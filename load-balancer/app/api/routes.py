"""API routes for the load balancer.

Exposes redirect routing endpoints that select a backend from Service Discovery
and issue 307 redirects preserving path and query string.
"""
from __future__ import annotations

from typing import Optional
from logging import getLogger
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from prometheus_client import Counter
from app.services.discovery_client import DiscoveryClient
from app.services.picker import Picker

log =  getLogger("Load-Balancer.API")
router = APIRouter()

REQUESTS = Counter("lb_requests_total", "Total incoming LB requests")
SELECTION_ERRORS = Counter("lb_selection_errors_total", "Backend selection failures")
# New labeled counter to track requests per image_id
IMAGE_REQUESTS = Counter("lb_image_requests_total", "Total incoming LB requests per image", ["image_id"])


def _get_dc_and_picker(request: Request) -> tuple[DiscoveryClient, Picker]:
    """Return DiscoveryClient and Picker instances.

    Prefers application-scoped singletons placed on ``app.state`` during
    application lifespan. Falls back to constructing ephemeral instances when
    running outside the fully-initialized app context (e.g., tests, scripts).
    """
    # Prefer app-scoped singletons (defined in app.main lifespan)
    dc: Optional[DiscoveryClient] = getattr(request.app.state, "dc", None)
    picker: Optional[Picker] = getattr(request.app.state, "picker", None)
    if dc is None or picker is None:
        # Fallback (not optimal): construct ephemeral ones
        dc = DiscoveryClient.from_settings()
        picker = Picker()
    log.info(f"Using DC: {dc}, Picker: {picker}")
    return dc, picker


@router.get("/registry/{image_id}")
@router.get("/registry/{image_id}/{path:path}")
async def route_to_backend(image_id: str, request: Request, path: str = ""):
    """
    Minimal LB mock:
      - fetch healthy endpoints for {image_id} from Service Discovery
      - pick one (first/round-robin)
      - 307-redirect the caller to that backend, preserving path & querystring
    """
    REQUESTS.inc()
    # Increment per-image counter
    IMAGE_REQUESTS.labels(image_id=image_id).inc()
    dc, picker = _get_dc_and_picker(request)

    # 1) ask Service Discovery
    backends = await dc.healthy_backends(image_id)  # -> ["http://host:port", ...]
    if not backends:
        SELECTION_ERRORS.inc()
        raise HTTPException(status_code=503, detail="No healthy backends")

    # 2) pick a target
    target_base = picker.pick(backends)
    if not target_base:
        SELECTION_ERRORS.inc()
        raise HTTPException(status_code=502, detail="Backend selection failed")

    # 3) build redirect URL (preserve path + query)
    path = path.lstrip("/")
    target_url = f"{target_base.rstrip('/')}/{path}" if path else target_base.rstrip("/")
    qs = str(request.url.query)
    if qs:
        target_url = f"{target_url}?{qs}"

    log.info("redirect %s -> %s", request.url, target_url)
    return RedirectResponse(url=target_url, status_code=307)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    log.info("Health check passed")
    return {"status": "OK"}


@router.get("/traffic")
async def traffic_stats():
    """Traffic statistics endpoint."""
    log.info("Traffic stats requested")
    return {"requests_total": REQUESTS._value.get(), "selection_errors_total": SELECTION_ERRORS._value.get()}

@router.get("/traffic/{image_id}")
async def traffic_stats_for_image(image_id: str):
    """Traffic statistics for a specific image."""
    # Retrieve the labeled counter for this image_id
    c = IMAGE_REQUESTS.labels(image_id=image_id)
    try:
        total = c._value.get()
    except Exception:
        total = 0.0
    log.info("Traffic stats for image %s: %d requests", image_id, total)
    return {"image_id": image_id, "requests_total": total}




"""API routes for the load balancer.

Exposes redirect routing endpoints that select a backend from Service Discovery
and issue 307 redirects preserving path and query string.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from prometheus_client import Counter

from app.services.discovery_client import DiscoveryClient
from app.services.picker import Picker

log = logging.getLogger("api")
router = APIRouter()

REQUESTS = Counter("lb_requests_total", "Total incoming LB requests")
SELECTION_ERRORS = Counter("lb_selection_errors_total", "Backend selection failures")


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
    return dc, picker


@router.get("/r/{image_id}")
@router.get("/r/{image_id}/{path:path}")
async def route_to_backend(image_id: str, request: Request, path: str = ""):
    """
    Minimal LB mock:
      - fetch healthy endpoints for {image_id} from Service Discovery
      - pick one (first/round-robin)
      - 307-redirect the caller to that backend, preserving path & querystring
    """
    REQUESTS.inc()
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

"""API routes for the load balancer.

Exposes redirect routing endpoints that select a backend from Service Discovery
and issue 307 redirects preserving path and query string.
"""
from __future__ import annotations

from typing import Optional, List
from logging import getLogger
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from prometheus_client import Counter
from app.services.discovery_client import DiscoveryClient
from app.services.picker import Picker
from app.services.proxy import forward as proxy_forward
from app.core.config import settings

log =  getLogger("Load-Balancer.API")
router = APIRouter()


REQUESTS = Counter("lb_requests_total", "Total incoming LB requests")
SELECTION_ERRORS = Counter("lb_selection_errors_total", "Backend selection failures")
# New labeled counter to track requests per image_id
IMAGE_REQUESTS = Counter("lb_image_requests_total", "Total incoming LB requests per image", ["image_id"])
# add requests per second by per image_id
REQUESTS_PER_SECOND = Counter("lb_requests_per_second", "Requests per second by image_id", ["image_id"])


# New reverse-proxy route replacing prior redirects for /r/{image_id}/{path:path}
@router.get("/registry/{image_id}")
@router.api_route("/registry/{image_id}/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def route_proxy(image_id: str, path: str, request: Request):
    """Reverse-proxy: forward to chosen backend and stream response back to client."""
    IMAGE_REQUESTS.labels(image_id=image_id).inc()

    sd = DiscoveryClient.from_settings()
    backends: List[str] = await sd.get_healthy_backends(image_id)  # e.g., ["http://backend-9001:9000"]

    if not backends:
        log.warning("No healthy backends for image_id=%s", image_id)
        raise HTTPException(status_code=503, detail="No healthy backends")

    chosen = Picker().pick(backends)
    if not chosen:
        raise HTTPException(status_code=503, detail="No healthy backends")
    log.info("Chosen backend for %s: %s", image_id, chosen)
    return await proxy_forward(request, chosen, path, timeout_s=settings.request_timeout_s)


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
    # add total requests per second
    requests_per_second = REQUESTS_PER_SECOND.labels(image_id=image_id)._value.get()
    return {"image_id": image_id, "requests_total": total, "requests_per_second": requests_per_second}




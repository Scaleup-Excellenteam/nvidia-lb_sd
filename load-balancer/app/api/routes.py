from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request
from prometheus_client import Counter

log = logging.getLogger("api")
router = APIRouter()

REQUESTS = Counter("lb_requests_total", "Total incoming LB requests")
SELECTION_ERRORS = Counter(
    "lb_selection_errors_total", "Backend selection failures"
)


@router.get("/")
async def choose_backend(request: Request):
    REQUESTS.inc()
    # app state set in main.py lifespan
    discovery = request.app.state.discovery
    selector = request.app.state.selector

    try:
        backends = await discovery.get_healthy_backends()
        if not backends:
            SELECTION_ERRORS.inc()
            raise HTTPException(status_code=503, detail="No healthy backends")
        target = await selector.next(backends)
        return {"selected_backend": target, "count_backends": len(backends)}
    except HTTPException:
        raise
    except Exception as e:
        SELECTION_ERRORS.inc()
        log.exception("Selection failed: %s", e)
        raise HTTPException(status_code=502, detail="Backend selection failed")

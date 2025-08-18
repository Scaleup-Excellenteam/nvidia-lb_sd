from fastapi import FastAPI
from app.api.routes import router as registry_router
from app.metrics.prometheus import metrics_router
from app.services.registry import seed_sample_data

# NEW: import asyncio + the poller
import asyncio
from app.services.health import poll_parts_loop

app = FastAPI(title="Service Discovery (Mock)")

# REST API under /registry
app.include_router(registry_router, prefix="/registry", tags=["registry"])

# Prometheus /metrics
app.include_router(metrics_router)

@app.on_event("startup")
async def _startup():
    """Seed a few sample endpoints at startup for convenience."""
    seed_sample_data()
    # NEW: start active polling loop (checks each part's /health every N seconds)
    app.state.parts_poller = asyncio.create_task(poll_parts_loop())

# NEW: stop the background task cleanly
@app.on_event("shutdown")
async def _shutdown():
    t = getattr(app.state, "parts_poller", None)
    if t:
        t.cancel()

@app.get("/health")
async def health():
    """Simple health endpoint for the mock SD service."""
    return {"status": "ok", "mock": True, "active_polling": True}

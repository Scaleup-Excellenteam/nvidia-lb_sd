"""Service Discovery mock FastAPI application.

Provides a minimal registry for endpoints and a Prometheus metrics endpoint.
"""

from fastapi import FastAPI
from app.api.routes import router as registry_router
from app.metrics.prometheus import metrics_router
from app.services.registry import seed_sample_data

app = FastAPI(title="Service Discovery (Mock)")

# REST API under /registry
app.include_router(registry_router, prefix="/registry", tags=["registry"])

# Prometheus /metrics
app.include_router(metrics_router)

@app.on_event("startup")
async def _startup():
    """Seed a few sample endpoints at startup for convenience."""
    # Load some sample endpoints so it's useful immediately
    seed_sample_data()

@app.get("/health")
async def health():
    """Simple health endpoint for the mock SD service."""
    return {"status": "ok", "mock": True}
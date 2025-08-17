from fastapi import APIRouter, Response
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

metrics_router = APIRouter()

# Standalone registry for the mock
registry = CollectorRegistry()
SD_HEALTHCHECKS = Counter("sd_healthchecks_total", "Number of SD /health calls", registry=registry)
SD_ENDPOINTS = Gauge("sd_endpoints", "Current endpoints known to SD", registry=registry)

@metrics_router.get("/metrics")
async def metrics():
    # Minimal example metrics; we set a placeholder count
    SD_HEALTHCHECKS.inc(0)
    SD_ENDPOINTS.set(3)
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
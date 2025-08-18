"""Load Balancer FastAPI application.

Creates the LB service, wires routes, configures logging, and exposes health and
Prometheus metrics endpoints.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.core.config import settings
from app.services.discovery_client import DiscoveryClient
from app.services.picker import Picker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan.

    Initializes logging and app-scoped singletons such as the
    DiscoveryClient (HTTP pool) and Picker (backend selection), and
    ensures they live for the duration of the app.
    """
    async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
        app.state.dc = DiscoveryClient(client, str(settings.service_discovery_url), settings.request_timeout_s)
        app.state.picker = Picker()
        yield

app = FastAPI(title="LB", version="0.1.0", lifespan=lifespan)
app.include_router(router)

@app.get("/readyz")
async def readyz():
    """Readiness probe endpoint returning a minimal OK payload."""
    return {"status": "ok"}

@app.get("/metrics")
async def metrics(_: Request):
    """Prometheus exposition endpoint for LB process metrics."""
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

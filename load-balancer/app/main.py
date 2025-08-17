from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.discovery_client import DiscoveryClient
from app.services.algorithms.round_robin import InMemoryRoundRobin

setup_logging()
log = logging.getLogger("lb")


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(
        connect=settings.request_timeout_s, read=settings.request_timeout_s
    )
    client = httpx.AsyncClient(timeout=timeout)

    app.state.http_client = client
    app.state.discovery = DiscoveryClient(str(settings.service_discovery_url), client)
    app.state.selector = InMemoryRoundRobin()
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(title="LB", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/readyz")
async def readyz():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics(_: Request):
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

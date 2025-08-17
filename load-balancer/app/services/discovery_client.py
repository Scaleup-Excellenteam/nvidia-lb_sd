from __future__ import annotations

import asyncio
import logging
from typing import List, Any

import httpx
from prometheus_client import Counter, Histogram

log = logging.getLogger("discovery")

SD_REQUESTS = Counter(
    "lb_sd_requests_total", "Service discovery requests", ["status"]
)
SD_LATENCY = Histogram(
    "lb_sd_latency_seconds", "Service discovery request latency seconds"
)


def _normalize_endpoints(payload: Any) -> list[str]:
    items: list[Any] = []
    if isinstance(payload, dict):
        for key in ("backends", "endpoints", "instances", "items", "nodes"):
            if key in payload and isinstance(payload[key], list):
                items = payload[key]
                break
    elif isinstance(payload, list):
        items = payload

    urls: list[str] = []
    for it in items:
        if isinstance(it, str):
            urls.append(it)
        elif isinstance(it, dict):
            if isinstance(it.get("url"), str):
                urls.append(it["url"]) 
            else:
                host = it.get("host") or it.get("ip") or it.get("address")
                port = it.get("port")
                scheme = it.get("scheme") or "http"
                path = it.get("path") or ""
                if host and port:
                    urls.append(f"{scheme}://{host}:{port}{path}")
    return urls


class DiscoveryClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url
        self.client = client

    async def get_healthy_backends(self) -> List[str]:
        attempt_delays = [0.05, 0.1, 0.2]
        last_exc: Exception | None = None

        for i, delay in enumerate([0.0, *attempt_delays]):
            if delay:
                await asyncio.sleep(delay)
            try:
                with SD_LATENCY.time():
                    resp = await self.client.get(self.base_url)
                if resp.status_code == 200:
                    SD_REQUESTS.labels(status="200").inc()
                    payload = resp.json()
                    urls = _normalize_endpoints(payload)
                    return urls
                else:
                    SD_REQUESTS.labels(status=str(resp.status_code)).inc()
                    log.warning("Service discovery non-200: %s", resp.status_code)
            except Exception as e:
                last_exc = e
                SD_REQUESTS.labels(status="error").inc()
                log.warning("Service discovery error (attempt %d): %s", i + 1, e)

        raise RuntimeError(f"Failed to get healthy backends: {last_exc}")

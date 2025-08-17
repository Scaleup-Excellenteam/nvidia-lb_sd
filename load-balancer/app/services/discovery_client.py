"""HTTP client wrapper for the Service Discovery mock.

Provides utilities to fetch healthy backends and normalize payload shapes.
Includes basic Prometheus metrics for request counts and latency.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import httpx
from prometheus_client import Counter, Histogram

from app.core.config import settings

log = logging.getLogger("discovery")

SD_REQUESTS = Counter("lb_sd_requests_total", "Service discovery requests", ["status"])
SD_LATENCY = Histogram("lb_sd_latency_seconds", "Service discovery request latency seconds")


def _normalize_endpoints(payload: object) -> list[str]:
    """
    Normalize heterogenous discovery payloads to a list of HTTP URLs.

    Accepts either:
      - {"backends": [{"url": "http://h:p"}, ...]}
      - [{"host": "1.2.3.4", "port": 8080}, ...]  (service-discovery mock shape)
      - [{"url": "http://h:p"}, ...]
    Returns a list of http URLs.
    """
    urls: list[str] = []

    def to_url(item: dict) -> Optional[str]:
        if "url" in item:
            return str(item["url"])
        host = item.get("host"); port = item.get("port")
        if host and port:
            return f"http://{host}:{port}"
        return None

    if isinstance(payload, dict):
        if "backends" in payload and isinstance(payload["backends"], list):
            for it in payload["backends"]:
                if isinstance(it, dict):
                    u = to_url(it)
                    if u: urls.append(u)
        else:
            u = to_url(payload) if isinstance(payload, dict) else None
            if u: urls.append(u)
    elif isinstance(payload, list):
        for it in payload:
            if isinstance(it, dict):
                u = to_url(it)
                if u: urls.append(u)

    return urls


class DiscoveryClient:
    """
    Tiny HTTP client wrapper for the service-discovery API.

    Holds an httpx.AsyncClient for connection pooling and exposes high-level
    operations such as fetching healthy backends for an image id.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str, timeout_s: float = 2.0):
        """Create a client with a shared HTTPX AsyncClient and base URL."""
        self._client = client
        self._base = base_url.rstrip("/")
        self._timeout = timeout_s

    @classmethod
    def from_settings(cls) -> "DiscoveryClient":
        """Construct a DiscoveryClient using global settings."""
        # settings.service_discovery_url may be either a base ("http://sd:7000")
        # or a full path. We treat it as base and construct endpoint URLs from it.
        client = httpx.AsyncClient(timeout=settings.request_timeout_s)
        return cls(client, str(settings.service_discovery_url), settings.request_timeout_s)

    def _image_url(self, image_id: str) -> str:
        """Build the URL used to fetch healthy endpoints for a given image id."""
        # Build: {base}/registry/images/{image_id}/endpoints?healthy=true
        return f"{self._base}/registry/images/{image_id}/endpoints?healthy=true"

    async def healthy_backends(self, image_id: str, retries: int = 2, backoff: float = 0.05) -> List[str]:
        """
        Fetch healthy endpoints for an image_id and normalize to absolute URLs.

        Retries a couple times with exponential backoff when requests fail or
        return non-200 responses. Emits simple Prometheus metrics.
        """
        url = self._image_url(image_id)
        last_exc: Exception | None = None

        for i in range(retries + 1):
            try:
                with SD_LATENCY.time():
                    resp = await self._client.get(url)
                if resp.status_code == 200:
                    SD_REQUESTS.labels(status="200").inc()
                    return _normalize_endpoints(resp.json())
                else:
                    SD_REQUESTS.labels(status=str(resp.status_code)).inc()
                    log.warning("SD non-200 (%s) on %s", resp.status_code, url)
            except Exception as e:
                last_exc = e
                SD_REQUESTS.labels(status="error").inc()
                log.warning("SD error (attempt %d): %s", i + 1, e)

            await asyncio.sleep(backoff * (2**i))
        
        raise RuntimeError(f"Failed to get healthy backends: {last_exc}")

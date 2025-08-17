"""Pydantic models used by the Load Balancer service."""
from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class Backend(BaseModel):
    """Represents a backend server reachable via an absolute URL."""

    url: HttpUrl


class DiscoveryResponse(BaseModel):
    """Shape returned by service discovery for a list of backends."""

    service: str | None = None
    backends: list[Backend]

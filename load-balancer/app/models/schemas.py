from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class Backend(BaseModel):
    url: HttpUrl


class DiscoveryResponse(BaseModel):
    service: str | None = None
    backends: list[Backend]

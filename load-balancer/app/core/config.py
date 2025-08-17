"""Configuration for the Load Balancer service.

Provides strongly-typed settings using Pydantic and a loader from environment
variables with defaults suitable for local development.
"""

from __future__ import annotations

import os
from pydantic import BaseModel, AnyUrl, ValidationError
from typing import cast


class Settings(BaseModel):
    """Pydantic settings for the LB service."""
    # Full URL to query healthy endpoints for demo-app
    service_discovery_url: AnyUrl # = "http://localhost:7000/registry/images/demo-app/endpoints?healthy=True"
    request_timeout_s: float = 2.0
    redis_url: str | None = None


def load_settings() -> Settings:
    """Load settings from environment variables and return a Settings object."""
    try:
        return Settings(
            service_discovery_url=cast(
            AnyUrl,
            os.getenv(
                "SERVICE_DISCOVERY_URL",
                "http://localhost:7000/registry/images/demo-app/endpoints?healthy=True",
            ),
            ),
            request_timeout_s=float(os.getenv("REQUEST_TIMEOUT_S", "2.0")),
            redis_url=os.getenv("REDIS_URL"),
        )
    except ValidationError as e:
        raise RuntimeError(f"Invalid configuration: {e}") from e


settings = load_settings()

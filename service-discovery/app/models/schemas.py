"""Pydantic models for the Service Discovery mock."""
from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict

class Status(str, Enum):
    """Health status of an endpoint."""
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"

class EndpointIn(BaseModel):
    """Input model used to register or update an endpoint in the registry."""
    id: str
    image_id: str
    host: str
    port: int
    zone: Optional[str] = None
    caps: Optional[Dict[str, int]] = None  # e.g., {"cpu": 300, "mem": 512}
    status: Status = Status.UP
    meta: Optional[Dict[str, str]] = None

class EndpointOut(EndpointIn):
    """Output model extending EndpointIn with server-managed properties."""
    last_heartbeat: Optional[float] = None
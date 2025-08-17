from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict

class Status(str, Enum):
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"

class EndpointIn(BaseModel):
    id: str
    image_id: str
    host: str
    port: int
    zone: Optional[str] = None
    caps: Optional[Dict[str, int]] = None  # e.g., {"cpu": 300, "mem": 512}
    status: Status = Status.UP
    meta: Optional[Dict[str, str]] = None

class EndpointOut(EndpointIn):
    last_heartbeat: Optional[float] = None
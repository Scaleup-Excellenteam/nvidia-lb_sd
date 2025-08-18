"""Configuration for the Service Discovery mock service."""
from pydantic import BaseModel
import os
HEALTH_POLL_INTERVAL_SEC   = float(os.getenv("HEALTH_POLL_INTERVAL_SEC", "30"))
HEALTH_REQUEST_TIMEOUT_SEC = float(os.getenv("HEALTH_REQUEST_TIMEOUT_SEC", "2.0"))
HEALTH_OK_KEY   = os.getenv("HEALTH_OK_KEY", "status")
HEALTH_OK_VALUE = os.getenv("HEALTH_OK_VALUE", "OK")

class Settings(BaseModel):
    """Static settings for the mock SD service."""
    # For a mock we keep it tiny. Add env parsing later if needed.
    SD_PORT: int = 7000
    HEARTBEAT_TTL_SEC: int = 0  # 0 = TTL disabled in this mock
    MOCK_MODE: bool = True

settings = Settings()
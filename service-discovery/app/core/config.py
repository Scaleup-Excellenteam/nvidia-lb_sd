"""Configuration for the Service Discovery mock service."""
from pydantic import BaseModel

class Settings(BaseModel):
    """Static settings for the mock SD service."""
    # For a mock we keep it tiny. Add env parsing later if needed.
    SD_PORT: int = 7000
    HEARTBEAT_TTL_SEC: int = 0  # 0 = TTL disabled in this mock
    MOCK_MODE: bool = True

settings = Settings()
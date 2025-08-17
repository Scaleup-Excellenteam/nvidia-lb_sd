from app.models.schemas import EndpointOut, Status

def is_healthy(ep: EndpointOut) -> bool:
    """Mock rule: only status==UP is considered healthy."""
    return ep.status == Status.UP
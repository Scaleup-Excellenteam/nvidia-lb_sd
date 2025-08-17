"""Helpers for evaluating endpoint health in the SD mock."""

from app.models.schemas import EndpointOut, Status

def is_healthy(ep: EndpointOut) -> bool:
    """Return True if the endpoint is considered healthy.

    Mock rule: only status==UP is considered healthy.
    """
    return ep.status == Status.UP
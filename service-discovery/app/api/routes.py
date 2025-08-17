"""API routes for the Service Discovery mock registry."""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.schemas import EndpointIn, EndpointOut, Status
from app.services.registry import registry

router = APIRouter()

@router.post("/endpoints", response_model=EndpointOut)
async def register_endpoint(ep: EndpointIn):
    """Create or update an endpoint (stored in memory)."""
    return registry.upsert(ep)

@router.delete("/endpoints/{endpoint_id}")
async def deregister_endpoint(endpoint_id: str):
    """Remove an endpoint by id. Returns 404 if not found."""
    if not registry.deregister(endpoint_id):
        raise HTTPException(404, detail="endpoint not found")
    return {"ok": True}

@router.put("/endpoints/{endpoint_id}/status", response_model=EndpointOut)
async def set_status(endpoint_id: str, status: Status = Query(...)):
    """Update the status of an endpoint (e.g., UP/DOWN)."""
    ep = registry.set_status(endpoint_id, status)
    if not ep:
        raise HTTPException(404, detail="endpoint not found")
    return ep

@router.post("/endpoints/{endpoint_id}/heartbeat", response_model=EndpointOut)
async def heartbeat(endpoint_id: str):
    """Touch the endpoint's heartbeat timestamp."""
    ep = registry.heartbeat(endpoint_id)
    if not ep:
        raise HTTPException(404, detail="endpoint not found")
    return ep

@router.get("/images/{image_id}/endpoints", response_model=List[EndpointOut])
async def list_endpoints(image_id: str, healthy: bool = True):
    """List endpoints for an image id, optionally filtering only healthy ones."""
    print(healthy)
    return registry.list_by_image(image_id, healthy_only=healthy)

@router.get("/services")
async def services_map():
    """Return the entire services map (image_id -> endpoints)."""
    return registry.services_map()
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
    if not registry.deregister(endpoint_id):
        raise HTTPException(404, detail="endpoint not found")
    return {"ok": True}

@router.put("/endpoints/{endpoint_id}/status", response_model=EndpointOut)
async def set_status(endpoint_id: str, status: Status = Query(...)):
    ep = registry.set_status(endpoint_id, status)
    if not ep:
        raise HTTPException(404, detail="endpoint not found")
    return ep

@router.post("/endpoints/{endpoint_id}/heartbeat", response_model=EndpointOut)
async def heartbeat(endpoint_id: str):
    ep = registry.heartbeat(endpoint_id)
    if not ep:
        raise HTTPException(404, detail="endpoint not found")
    return ep

@router.get("/images/{image_id}/endpoints", response_model=List[EndpointOut])
async def list_endpoints(image_id: str, healthy: bool = True):
    print(healthy)
    return registry.list_by_image(image_id, healthy_only=healthy)

@router.get("/services")
async def services_map():
    return registry.services_map()

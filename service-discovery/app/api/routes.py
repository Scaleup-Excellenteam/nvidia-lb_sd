from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.schemas import EndpointIn, EndpointOut, Status, SystemPartIn, SystemPartOut
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


# 1) parts add/update themselves here (similar to /endpoints)
@router.post("/parts", response_model=SystemPartOut)
async def register_part(part: SystemPartIn):
    return registry.upsert_part(part)

# 2) remove a part
@router.delete("/parts/{part_id}")
async def deregister_part(part_id: str):
    ok = registry.deregister_part(part_id)
    if not ok:
        raise HTTPException(404, detail="part not found")
    return {"ok": True}

# 3) manual status flip
@router.put("/parts/{part_id}/status", response_model=SystemPartOut)
async def update_part_status(part_id: str, status: Status = Query(...)):
    p = registry.set_part_status(part_id, status)
    if not p:
        raise HTTPException(404, detail="part not found")
    return p

# 4) heartbeat ("I'm alive")
@router.post("/parts/{part_id}/heartbeat", response_model=SystemPartOut)
async def heartbeat_part(part_id: str):
    p = registry.heartbeat_part(part_id)
    if not p:
        raise HTTPException(404, detail="part not found")
    return p

# 5) list parts by kind (like images), with healthy filter
@router.get("/parts/{kind}", response_model=List[SystemPartOut])
async def list_parts_by_kind(kind: str, healthy: bool = True):
    return registry.list_parts(kind=kind, healthy_only=healthy)

# 6) optional: list all parts, any kind
@router.get("/parts", response_model=List[SystemPartOut])
async def list_all_parts(healthy: bool = True):
    return registry.list_parts(kind=None, healthy_only=healthy)

# 7) optional: kind -> parts map (debug)
@router.get("/parts-map")
async def parts_map():
    return registry.parts_map()
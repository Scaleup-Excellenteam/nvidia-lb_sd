from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.schemas import EndpointIn, EndpointOut, Status, SystemPartIn, SystemPartOut, ServiceItem, ContainerItem
from app.services.registry import registry

router = APIRouter()


# ------- helpers to map internal -> UI strings -------
def _part_status_to_ui(s: Status) -> str:
    # UP -> healthy, DEGRADED -> warning, DOWN -> error
    return "healthy" if s == Status.UP else ("warning" if s == Status.DEGRADED else "error")

def _endpoint_status_to_ui(s: Status) -> str:
    # UP -> running, otherwise -> stopped
    return "running" if s == Status.UP else "stopped"

@router.post("/endpoints", response_model=EndpointOut)
async def register_endpoint(ep: EndpointIn):
    """Create or update an endpoint (stored in memory)."""
    print("[SD] POST /endpoints — creates/updates an endpoint; returns the saved endpoint JSON")

    return registry.upsert(ep)

@router.delete("/endpoints/{endpoint_id}")
async def deregister_endpoint(endpoint_id: str):
    print("[SD] DELETE /endpoints/{id} — removes an endpoint; returns {'ok': True} if it existed")

    if not registry.deregister(endpoint_id):
        raise HTTPException(404, detail="endpoint not found")
    return {"ok": True}

@router.put("/endpoints/{endpoint_id}/status", response_model=EndpointOut)
async def set_status(endpoint_id: str, status: Status = Query(...)):
    print("[SD] PUT /endpoints/{id}/status — sets status; returns the endpoint with new status")

    ep = registry.set_status(endpoint_id, status)
    if not ep:
        raise HTTPException(404, detail="endpoint not found")
    return ep

@router.post("/endpoints/{endpoint_id}/heartbeat", response_model=EndpointOut)
async def heartbeat(endpoint_id: str):
    print("[SD] POST /endpoints/{id}/heartbeat — marks alive; returns the endpoint with refreshed last_heartbeat")

    ep = registry.heartbeat(endpoint_id)
    if not ep:
        raise HTTPException(404, detail="endpoint not found")
    return ep

@router.get("/images/{image_id}/endpoints", response_model=List[EndpointOut])
async def list_endpoints(image_id: str, healthy: bool = True):
    print("[SD] GET /images/{image}/endpoints — lists endpoints; returns a list (maybe empty)")

    return registry.list_by_image(image_id, healthy_only=healthy)

@router.get("/services-map")
async def services_map():
    print("[SD] GET /services — shows catalog; returns image_id -> list of endpoints")

    return registry.services_map()


# 1) parts add/update themselves here (similar to /endpoints)
@router.post("/parts", response_model=SystemPartOut)
async def register_part(part: SystemPartIn):
    print("[SD] POST /parts — creates/updates a system part; returns the saved part JSON")

    return registry.upsert_part(part)

# 2) remove a part
@router.delete("/parts/{part_id}")
async def deregister_part(part_id: str):
    print("[SD] DELETE /parts/{id} — removes a part; returns {'ok': True} if it existed")

    ok = registry.deregister_part(part_id)
    if not ok:
        raise HTTPException(404, detail="part not found")
    return {"ok": True}

# 3) manual status flip
@router.put("/parts/{part_id}/status", response_model=SystemPartOut)
async def update_part_status(part_id: str, status: Status = Query(...)):
    print("[SD] DELETE /parts/{id} — removes a part; returns {'ok': True} if it existed")

    p = registry.set_part_status(part_id, status)
    if not p:
        raise HTTPException(404, detail="part not found")
    return p

# 4) heartbeat ("I'm alive")
@router.post("/parts/{part_id}/heartbeat", response_model=SystemPartOut)
async def heartbeat_part(part_id: str):
    print("[SD] POST /parts/{id}/heartbeat — marks alive; returns the part with refreshed last_heartbeat")

    p = registry.heartbeat_part(part_id)
    if not p:
        raise HTTPException(404, detail="part not found")
    return p

# 5) list parts by kind (like images), with healthy filter
@router.get("/parts/{kind}", response_model=List[SystemPartOut])
async def list_parts_by_kind(kind: str, healthy: bool = True):
    print("[SD] GET /parts/{kind} — lists parts of this kind; returns a list (maybe empty)")

    return registry.list_parts(kind=kind, healthy_only=healthy)

# 6) optional: list all parts, any kind
@router.get("/parts", response_model=List[SystemPartOut])
async def list_all_parts(healthy: bool = True):
    print("[SD] GET /parts — lists all parts; returns a list (maybe empty)")

    return registry.list_parts(kind=None, healthy_only=healthy)

# 7) optional: kind -> parts map (debug)
@router.get("/parts-map")
async def parts_map():
    print("[SD] GET /parts-map — shows catalog; returns kind -> list of parts")

    return registry.parts_map()


@router.get("/services", response_model=List[ServiceItem])
async def services_flat():
    """
    Returns:
      [
        { "id": "...", "name": "<kind>", "endpoint": "<url>", "status": "healthy|warning|error" },
        ...
      ]
    """
    parts = registry.list_parts(kind=None, healthy_only=False)
    return [
        ServiceItem(
            id=p.id,
            name=p.kind,
            endpoint=p.url,
            status=_part_status_to_ui(p.status),
        )
        for p in parts
    ]

@router.get("/containers", response_model=List[ContainerItem])
async def containers_flat(image_id: str = Query(..., description="image id to list")):
    """
    Query: ?image_id={imageId}
    Returns:
      [
        { "id": "...", "image_id": "...", "endpoint": "http://host:port", "status": "running|stopped" },
        ...
      ]
    """
    eps = registry.list_by_image(image_id, healthy_only=False)
    return [
        ContainerItem(
            id=e.id,
            image_id=e.image_id,
            endpoint=f"http://{e.host}:{e.port}",
            status=_endpoint_status_to_ui(e.status),
        )
        for e in eps
    ]
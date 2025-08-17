from threading import RLock
from time import monotonic
from typing import Dict, List, Optional
from app.models.schemas import EndpointIn, EndpointOut, Status

class Registry:
    """In-memory mock registry. Thread-safe and simple."""
    def __init__(self):
        self._endpoints: Dict[str, EndpointOut] = {}
        self._by_image: Dict[str, set[str]] = {}
        self._lock = RLock()

    def upsert(self, ep: EndpointIn) -> EndpointOut:
        with self._lock:
            out = EndpointOut(**ep.model_dump(), last_heartbeat=monotonic())
            self._endpoints[ep.id] = out
            self._by_image.setdefault(ep.image_id, set()).add(ep.id)
            return out

    def deregister(self, endpoint_id: str) -> bool:
        with self._lock:
            ep = self._endpoints.pop(endpoint_id, None)
            if not ep:
                return False
            s = self._by_image.get(ep.image_id)
            if s and endpoint_id in s:
                s.remove(endpoint_id)
                if not s:
                    self._by_image.pop(ep.image_id, None)
            return True

    def set_status(self, endpoint_id: str, status: Status) -> Optional[EndpointOut]:
        with self._lock:
            ep = self._endpoints.get(endpoint_id)
            if not ep:
                return None
            ep.status = status
            ep.last_heartbeat = monotonic()
            return ep

    def heartbeat(self, endpoint_id: str) -> Optional[EndpointOut]:
        with self._lock:
            ep = self._endpoints.get(endpoint_id)
            if not ep:
                return None
            ep.last_heartbeat = monotonic()
            return ep

    def list_by_image(self, image_id: str, healthy_only: bool = True) -> List[EndpointOut]:
        with self._lock:
            ids = self._by_image.get(image_id, set())
            eps = [self._endpoints[i] for i in ids]
            print(eps)
            if healthy_only:
                eps = [e for e in eps if e.status == Status.UP]
            return eps

    def services_map(self) -> Dict[str, list[EndpointOut]]:
        with self._lock:
            return {img: [self._endpoints[i] for i in ids] for img, ids in self._by_image.items()}

# Singleton used by routes
registry = Registry()

def seed_sample_data():
    """Load a few endpoints to play with at startup."""
    samples = [
        EndpointIn(id="web-1", image_id="demo-app", host="127.0.0.1", port=9001, status=Status.UP),
        EndpointIn(id="web-2", image_id="demo-app", host="127.0.0.1", port=9002, status=Status.UP),
        EndpointIn(id="api-1", image_id="shop-app", host="127.0.0.1", port=9101, status=Status.DEGRADED),
    ]
    for s in samples:
        registry.upsert(s)

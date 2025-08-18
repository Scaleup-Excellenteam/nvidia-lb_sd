import asyncio, httpx
from time import monotonic
from typing import Optional
from app.core.config import (
    HEALTH_POLL_INTERVAL_SEC, HEALTH_REQUEST_TIMEOUT_SEC,
    HEALTH_OK_KEY, HEALTH_OK_VALUE
)
from app.services.registry import registry
from app.models.schemas import Status

def _normalize(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return url + "health" if url.endswith("/") else url  # allow base or full URL

async def _check_part(client: httpx.AsyncClient, part) -> None:
    url = _normalize(getattr(part, "url", None))
    if not url:
        return
    ok = False
    try:
        r = await client.get(url, timeout=HEALTH_REQUEST_TIMEOUT_SEC)
        if r.status_code < 400:
            try:
                ok = str(r.json().get(HEALTH_OK_KEY, "")).upper() == HEALTH_OK_VALUE.upper()
            except ValueError:
                ok = "OK" in (r.text or "")
    except Exception:
        ok = False
    # Update SD: status becomes UP/DOWN; last_heartbeat updated inside set_part_status
    registry.set_part_status(part.id, Status.UP if ok else Status.DOWN)

async def poll_parts_loop() -> None:
    await asyncio.sleep(0.5)  # let app start
    while True:
        try:
            parts = registry.list_parts(kind=None, healthy_only=False)
            async with httpx.AsyncClient() as client:
                tasks = [_check_part(client, p) for p in parts if getattr(p, "url", None)]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"[SD] poller error: {e}")
        await asyncio.sleep(HEALTH_POLL_INTERVAL_SEC)

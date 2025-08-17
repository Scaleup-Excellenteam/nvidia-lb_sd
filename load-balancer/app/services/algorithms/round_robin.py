from __future__ import annotations

import asyncio
from typing import Sequence


class InMemoryRoundRobin:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._idx = 0

    async def next(self, items: Sequence[str]) -> str:
        if not items:
            raise ValueError("No backends available")
        async with self._lock:
            choice = items[self._idx % len(items)]
            self._idx += 1
            return choice

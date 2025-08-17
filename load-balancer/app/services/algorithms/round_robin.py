"""In-memory round-robin selection algorithm used by the LB mock."""
from __future__ import annotations

import asyncio
from typing import Sequence


class InMemoryRoundRobin:
    """A simple, coroutine-safe round-robin selector using an asyncio.Lock."""
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._idx = 0

    async def next(self, items: Sequence[str]) -> str:
        """Return the next item in a round-robin fashion.

        Raises ValueError when the sequence is empty.
        """
        if not items:
            raise ValueError("No backends available")
        async with self._lock:
            choice = items[self._idx % len(items)]
            self._idx += 1
            return choice

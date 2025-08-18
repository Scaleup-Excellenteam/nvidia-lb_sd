"""Round-robin selection algorithm."""
from __future__ import annotations

import threading
from typing import Optional

from .base import BaseAlgorithm


class RoundRobinAlgorithm(BaseAlgorithm):
    """Thread-safe round-robin algorithm."""

    def __init__(self):
        super().__init__("round_robin")
        self._lock = threading.Lock()
        self._index = 0
        self._last_backends_hash = None

    def pick(self, backends: list[str]) -> Optional[str]:
        """Pick next backend using round-robin."""
        if not backends:
            return None

        with self._lock:
            # Reset index if backends changed
            current_hash = hash(tuple(sorted(backends)))
            if current_hash != self._last_backends_hash:
                self._index = 0
                self._last_backends_hash = current_hash

            # Pick next backend
            backend = backends[self._index % len(backends)]
            self._index += 1

            return backend

    def reset(self) -> None:
        """Reset round-robin state."""
        super().reset()
        with self._lock:
            self._index = 0
            self._last_backends_hash = None
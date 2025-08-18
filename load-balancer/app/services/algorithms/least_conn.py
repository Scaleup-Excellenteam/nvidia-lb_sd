"""Least connections algorithm."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Optional

from .base import BaseAlgorithm


class LeastConnectionsAlgorithm(BaseAlgorithm):
    """Algorithm that selects backend with least active connections."""

    def __init__(self, connection_timeout: float = 30.0):
        super().__init__("least_connections")
        self._lock = threading.Lock()
        self._connections: dict[str, int] = defaultdict(int)
        self._last_request_time: dict[str, float] = defaultdict(float)
        self._connection_timeout = connection_timeout

    def pick(self, backends: list[str]) -> Optional[str]:
        """Pick backend with least connections."""
        if not backends:
            return None

        with self._lock:
            # Clean up expired connections
            self._cleanup_expired_connections()

            # Find backend with minimum connections
            min_connections = float('inf')
            best_backend = None

            for backend in backends:
                connections = self._connections[backend]
                if connections < min_connections:
                    min_connections = connections
                    best_backend = backend

            # Increment connection count
            if best_backend:
                self._connections[best_backend] += 1
                self._last_request_time[best_backend] = time.time()

            return best_backend

    def release_connection(self, backend: str) -> None:
        """Release a connection for a backend."""
        with self._lock:
            if backend in self._connections and self._connections[backend] > 0:
                self._connections[backend] -= 1

    def _cleanup_expired_connections(self) -> None:
        """Clean up connections that have timed out."""
        current_time = time.time()
        expired_backends = []

        for backend, last_time in self._last_request_time.items():
            if current_time - last_time > self._connection_timeout:
                expired_backends.append(backend)

        for backend in expired_backends:
            self._connections[backend] = 0
            del self._last_request_time[backend]

    def reset(self) -> None:
        """Reset connection tracking."""
        super().reset()
        with self._lock:
            self._connections.clear()
            self._last_request_time.clear()
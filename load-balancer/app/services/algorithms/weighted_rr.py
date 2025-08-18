"""Weighted round-robin algorithm."""
from __future__ import annotations

import threading
from typing import Optional

from .base import BaseAlgorithm


class WeightedRoundRobinAlgorithm(BaseAlgorithm):
    """Weighted round-robin algorithm that considers backend weights."""

    def __init__(self, default_weight: int = 1):
        super().__init__("weighted_round_robin")
        self._lock = threading.Lock()
        self._current_weights: dict[str, int] = {}
        self._default_weight = default_weight
        self._last_backends_hash = None

    def pick(self, backends: list[str]) -> Optional[str]:
        """Pick backend using weighted round-robin."""
        if not backends:
            return None

        with self._lock:
            # Reset if backends changed
            current_hash = hash(tuple(sorted(backends)))
            if current_hash != self._last_backends_hash:
                self._reset_weights(backends)
                self._last_backends_hash = current_hash

            # Find backend with highest current weight
            best_backend = None
            max_weight = -1

            for backend in backends:
                current_weight = self._current_weights.get(backend, 0)
                if current_weight > max_weight:
                    max_weight = current_weight
                    best_backend = backend

            if best_backend:
                # Reduce the weight of selected backend
                self._current_weights[best_backend] -= 1

                # If all weights are 0 or negative, reset them
                if all(w <= 0 for w in self._current_weights.values()):
                    self._reset_weights(backends)

            return best_backend

    def set_backend_weight(self, backend: str, weight: int) -> None:
        """Set weight for a specific backend."""
        with self._lock:
            if weight > 0:
                self._current_weights[backend] = weight

    def _reset_weights(self, backends: list[str]) -> None:
        """Reset weights for all backends."""
        self._current_weights.clear()
        for backend in backends:
            # Use default weight or derive from backend URL (simple heuristic)
            weight = self._get_backend_weight(backend)
            self._current_weights[backend] = weight

    def _get_backend_weight(self, backend: str) -> int:
        """Get weight for a backend (can be extended with actual weight logic)."""
        # Simple heuristic: backends with lower port numbers get higher weight
        # In real implementation, this could come from service discovery metadata
        try:
            if ':' in backend:
                port_str = backend.split(':')[-1]
                port = int(port_str.split('/')[0])  # Handle URLs with paths
                # Lower port = higher weight (just for demo)
                return max(1, 10 - (port % 10))
        except (ValueError, IndexError):
            pass
        return self._default_weight

    def reset(self) -> None:
        """Reset weighted round-robin state."""
        super().reset()
        with self._lock:
            self._current_weights.clear()
            self._last_backends_hash = None
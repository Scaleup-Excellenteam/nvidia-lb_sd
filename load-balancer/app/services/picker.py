"""Backend selection helpers for the Load Balancer."""
from __future__ import annotations

import itertools
import threading
from typing import Iterable, Optional


class Picker:
    """
    Simple, thread-safe round-robin picker.

    Maintains a per-pool iterator keyed by the sorted set of backend URLs so
    that each distinct pool has its own position in the cycle.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._iters: dict[tuple[str, ...], itertools.cycle[str]] = {}

    def pick(self, backends: Iterable[str]) -> Optional[str]:
        """Pick the next backend from the provided iterable using round-robin.

        Returns None if the input is empty.
        """
        pool = tuple(sorted(set(backends)))
        if not pool:
            return None

        with self._lock:
            it = self._iters.get(pool)
            if it is None:
                it = itertools.cycle(pool)
                self._iters[pool] = it
            return next(it)

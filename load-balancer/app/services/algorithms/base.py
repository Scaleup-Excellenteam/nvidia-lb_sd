"""Base interfaces and types for load-balancing algorithms."""
from __future__ import annotations

import abc
import time
from typing import Optional, Protocol


class LoadBalancingAlgorithm(Protocol):
    """Protocol for load balancing algorithms."""

    def pick(self, backends: list[str]) -> Optional[str]:
        """Pick a backend from the list. Returns None if no backends available."""
        ...

    def reset(self) -> None:
        """Reset algorithm state (optional)."""
        ...


class BaseAlgorithm(abc.ABC):
    """Base class for load balancing algorithms with common functionality."""

    def __init__(self, name: str):
        self.name = name
        self.last_used = time.time()
        self.request_count = 0
        self.error_count = 0

    @abc.abstractmethod
    def pick(self, backends: list[str]) -> Optional[str]:
        """Pick a backend from the list."""
        pass

    def reset(self) -> None:
        """Reset algorithm state."""
        self.last_used = time.time()
        self.request_count = 0
        self.error_count = 0

    def record_request(self, success: bool = True) -> None:
        """Record a request and its success/failure."""
        self.request_count += 1
        self.last_used = time.time()
        if not success:
            self.error_count += 1

    @property
    def error_rate(self) -> float:
        """Calculate error rate for this algorithm."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this algorithm."""
        return 1.0 - self.error_rate
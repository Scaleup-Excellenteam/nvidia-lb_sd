""""Smart backend selection with automatic algorithm switching."""
from __future__ import annotations

import time
import threading
from typing import Optional

from .algorithms.base import BaseAlgorithm
from .algorithms.round_robin import RoundRobinAlgorithm
from .algorithms.least_conn import LeastConnectionsAlgorithm
from .algorithms.weighted_rr import WeightedRoundRobinAlgorithm


class Picker:
    """
    Smart picker that automatically selects the best performing algorithm.

    Monitors performance of different algorithms and switches to the best one
    based on success rate and recent performance.
    """

    def __init__(self, evaluation_window: float = 60.0, min_requests_for_switch: int = 10):
        self._lock = threading.Lock()
        self._algorithms: list[BaseAlgorithm] = [
            RoundRobinAlgorithm(),
            LeastConnectionsAlgorithm(),
            WeightedRoundRobinAlgorithm(),
        ]
        self._current_algorithm_index = 0
        self._evaluation_window = evaluation_window
        self._min_requests_for_switch = min_requests_for_switch
        self._last_evaluation = time.time()
        self._last_backend_choice: dict[str, str] = {}  # backend -> algorithm_name
        self._exploration_counter = 0  # Counter to force trying all algorithms

    def pick(self, backends: list[str]) -> Optional[str]:
        """Pick the best backend using the currently selected algorithm."""
        if not backends:
            return None

        with self._lock:
            # Force exploration: give each algorithm a chance initially
            self._force_exploration()

            # Evaluate and potentially switch algorithms
            self._maybe_switch_algorithm()

            # Get current algorithm
            current_algo = self._algorithms[self._current_algorithm_index]

            # Pick backend
            backend = current_algo.pick(backends)

            if backend:
                # Record which algorithm was used for this backend
                self._last_backend_choice[backend] = current_algo.name
                current_algo.record_request(success=True)

            return backend

    def record_backend_result(self, backend: str, success: bool) -> None:
        """Record the result of a request to a specific backend."""
        with self._lock:
            # Find which algorithm was used for this backend
            algo_name = self._last_backend_choice.get(backend)
            if algo_name:
                for algo in self._algorithms:
                    if algo.name == algo_name:
                        algo.record_request(success)
                        break

    def _force_exploration(self) -> None:
        """Force trying all algorithms initially to gather data."""
        # For the first few requests, cycle through all algorithms
        # to give each one a chance to collect data
        total_requests = sum(algo.request_count for algo in self._algorithms)

        if total_requests < self._min_requests_for_switch * len(self._algorithms):
            # Still in exploration phase - rotate algorithms
            self._exploration_counter += 1
            desired_algo = (self._exploration_counter // self._min_requests_for_switch) % len(self._algorithms)

            if desired_algo != self._current_algorithm_index:
                old_name = self._algorithms[self._current_algorithm_index].name
                new_name = self._algorithms[desired_algo].name
                print(f"Exploration: switching from {old_name} to {new_name}")
                self._current_algorithm_index = desired_algo

    def _maybe_switch_algorithm(self) -> None:
        """Evaluate algorithms and switch to the best performing one."""
        current_time = time.time()

        # Only evaluate periodically
        if current_time - self._last_evaluation < self._evaluation_window:
            return

        self._last_evaluation = current_time
        current_algo = self._algorithms[self._current_algorithm_index]

        # If current algorithm has poor performance and enough data, try others
        if current_algo.request_count >= self._min_requests_for_switch:
            current_score = self._calculate_algorithm_score(current_algo)

            # If current algorithm is performing poorly (< 80% success), try alternatives
            if current_score < 0.8:
                print(f"Current algorithm {current_algo.name} performing poorly (score: {current_score:.3f})")

                # Try each other algorithm for a few requests
                for i, algo in enumerate(self._algorithms):
                    if i != self._current_algorithm_index:
                        print(f"Giving {algo.name} a chance to prove itself...")
                        self._current_algorithm_index = i
                        return

            # Regular evaluation: find best performing algorithm with enough data
            best_algo_index = self._current_algorithm_index
            best_score = current_score

            for i, algo in enumerate(self._algorithms):
                if algo.request_count >= self._min_requests_for_switch:
                    score = self._calculate_algorithm_score(algo)
                    if score > best_score + 0.05:  # Small threshold to avoid constant switching
                        best_score = score
                        best_algo_index = i

            # Switch if we found a significantly better algorithm
            if best_algo_index != self._current_algorithm_index:
                old_algo = self._algorithms[self._current_algorithm_index]
                new_algo = self._algorithms[best_algo_index]
                print(
                    f"Switching from {old_algo.name} (score: {self._calculate_algorithm_score(old_algo):.3f}) "
                    f"to {new_algo.name} (score: {best_score:.3f})"
                )
                self._current_algorithm_index = best_algo_index

    def _calculate_algorithm_score(self, algorithm: BaseAlgorithm) -> float:
        """Calculate a performance score for the algorithm."""
        success_rate = algorithm.success_rate
        error_rate = algorithm.error_rate

        # Simple scoring: prioritize success rate, penalize error rate
        return success_rate - error_rate
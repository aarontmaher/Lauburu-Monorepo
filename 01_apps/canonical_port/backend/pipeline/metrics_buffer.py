"""
High-Performance Bounded Time-Series Ring Buffer
Version: 3.0.0-CANONICAL

Stores multi-node telemetry samples with fast time-window slicing,
FIFO bounded retention, and sub-millisecond statistical aggregations.
"""

import collections
import statistics
import threading
from typing import Any, Dict, List, Optional, Tuple


class TimeSeriesRingBuffer:
    """
    Bounded, thread-safe time-series ring buffer with statistical aggregation.
    Maintains time-ordered telemetry samples with fast time-window queries.
    """

    def __init__(self, maxlen: int = 1000) -> None:
        if maxlen < 1:
            raise ValueError(f"Ring buffer maxlen must be >= 1, got {maxlen}")
        self.maxlen: int = maxlen
        self._buffer: collections.deque = collections.deque(maxlen=maxlen)
        self._lock: threading.RLock = threading.RLock()

    def append(
        self,
        timestamp: float,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Append a time-series sample to the ring buffer.
        Evicts oldest sample automatically if capacity is reached (FIFO).
        """
        with self._lock:
            self._buffer.append((float(timestamp), float(value), dict(metadata or {})))

    def size(self) -> int:
        """Return the current number of samples in the buffer."""
        with self._lock:
            return len(self._buffer)

    def __len__(self) -> int:
        """Return the current number of samples in the buffer."""
        return self.size()

    def get_recent(self, count: int = 10) -> List[Tuple[float, float, Dict[str, Any]]]:
        """Return the most recent `count` samples in chronological order."""
        with self._lock:
            if count <= 0:
                return []
            items = list(self._buffer)
            return items[-count:]

    def get_window(
        self, start_time: float, end_time: float
    ) -> List[Tuple[float, float, Dict[str, Any]]]:
        """Return all samples with timestamps in the closed interval [start_time, end_time]."""
        with self._lock:
            return [
                (t, v, m)
                for t, v, m in self._buffer
                if start_time <= t <= end_time
            ]

    def get_stats(self) -> Dict[str, float]:
        """
        Calculate statistical aggregations over all current samples in the buffer.
        Returns count, mean, min, max, stddev, median, p95, and p99.
        """
        with self._lock:
            if not self._buffer:
                return {
                    "count": 0.0,
                    "mean": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "stddev": 0.0,
                    "median": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }

            values = [v for _, v, _ in self._buffer]
            n = len(values)
            sorted_vals = sorted(values)

            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values) if n > 1 else 0.0
            median_val = statistics.median(values)

            # Percentile calculation
            p95_idx = min(int(n * 0.95), n - 1)
            p99_idx = min(int(n * 0.99), n - 1)
            p95_val = sorted_vals[p95_idx]
            p99_val = sorted_vals[p99_idx]

            return {
                "count": float(n),
                "mean": round(mean_val, 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "stddev": round(stdev_val, 4),
                "median": round(median_val, 4),
                "p95": round(p95_val, 4),
                "p99": round(p99_val, 4),
            }

    def get_latest(self) -> Optional[Tuple[float, float, Dict[str, Any]]]:
        """Return the newest sample in the buffer or None if empty."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]

    def get_oldest(self) -> Optional[Tuple[float, float, Dict[str, Any]]]:
        """Return the oldest sample in the buffer or None if empty."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[0]

    def clear(self) -> None:
        """Clear all samples from the buffer."""
        with self._lock:
            self._buffer.clear()

    def to_list(self) -> List[Tuple[float, float, Dict[str, Any]]]:
        """Return a full snapshot list of all samples in chronological order."""
        with self._lock:
            return list(self._buffer)

    def prune_older_than(self, cutoff_time: float) -> int:
        """
        Prune all samples with timestamp strictly before `cutoff_time`.
        Returns the number of pruned samples.
        """
        with self._lock:
            initial_count = len(self._buffer)
            while self._buffer and self._buffer[0][0] < cutoff_time:
                self._buffer.popleft()
            return initial_count - len(self._buffer)

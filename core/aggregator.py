"""Aggregator for I/O events with time window."""

import time
from typing import List, Dict, Optional

from core.models import IOEvent, AggregatedResult, OperationType


class Aggregator:
    def __init__(self, window_ms: int = 1000):
        self._window_ms = window_ms
        self._window_sec = window_ms / 1000.0
        self._data: Dict[tuple, AggregatedResult] = {}
        self._window_start: Optional[float] = None

    def add_event(self, event: IOEvent, process_name: str) -> None:
        now = time.time()
        if self._window_start is None:
            self._window_start = now

        if now - self._window_start >= self._window_sec:
            self._reset_window(now)

        key = (event.disk, event.pid, event.operation)
        if key not in self._data:
            self._data[key] = AggregatedResult(
                disk=event.disk,
                pid=event.pid,
                process_name=process_name
            )

        result = self._data[key]
        if event.operation == OperationType.READ:
            result.read_bytes += event.bytes
        else:
            result.write_bytes += event.bytes

    def _reset_window(self, now: float) -> None:
        self._data.clear()
        self._window_start = now

    def get_results(self) -> List[AggregatedResult]:
        results = []
        for result in self._data.values():
            total_bytes = result.read_bytes + result.write_bytes
            if total_bytes > 0:
                result.rate_kb_s = round(total_bytes / self._window_sec / 1024, 1)
                results.append(result)
        return sorted(results, key=lambda x: x.rate_kb_s, reverse=True)

    def has_activity(self) -> bool:
        return len(self._data) > 0

    def clear(self) -> None:
        self._data.clear()
        self._window_start = None

    @property
    def window_ms(self) -> int:
        return self._window_ms

    def set_window_ms(self, window_ms: int) -> None:
        self._window_ms = window_ms
        self._window_sec = window_ms / 1000.0


def calc_rate(current: int, last: int, interval_sec: float) -> float:
    if interval_sec <= 0:
        return 0.0
    return (current - last) / interval_sec

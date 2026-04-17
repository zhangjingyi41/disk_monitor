"""Data models for disk monitoring."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import time


class OperationType(Enum):
    READ = "READ"
    WRITE = "WRITE"


@dataclass
class IOEvent:
    timestamp: float
    pid: int
    operation: OperationType
    bytes: int
    disk: str
    file_path: Optional[str] = None


@dataclass
class DiskActivity:
    disk: str
    status: str
    pid: int
    process_name: str
    rate: float


@dataclass
class AggregatedResult:
    disk: str
    pid: int
    process_name: str
    read_bytes: int = 0
    write_bytes: int = 0
    rate_kb_s: float = 0.0

    def to_activity(self) -> DiskActivity:
        if self.read_bytes > 0 and self.write_bytes > 0:
            status = "READ/WRITE"
        elif self.read_bytes > 0:
            status = "READ"
        else:
            status = "WRITE"
        return DiskActivity(
            disk=self.disk,
            status=status,
            pid=self.pid,
            process_name=self.process_name,
            rate=self.rate_kb_s
        )


@dataclass
class DiskInfo:
    name: str
    mountpoint: str
    total: int
    used: int
    free: int
    fstype: str = ""


class WindowAggregator:
    def __init__(self, window_ms: int = 1000):
        self.window_ms = window_ms
        self.window_sec = window_ms / 1000.0
        self._data: Dict[tuple, AggregatedResult] = {}
        self._window_start: Optional[float] = None

    def add_event(self, event: IOEvent, process_name: str) -> None:
        now = time.time()
        if self._window_start is None:
            self._window_start = now

        if now - self._window_start >= self.window_sec:
            self._data.clear()
            self._window_start = now

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

    def get_results(self) -> List[AggregatedResult]:
        results = []
        for result in self._data.values():
            total_bytes = result.read_bytes + result.write_bytes
            result.rate_kb_s = round(total_bytes / self.window_sec / 1024, 1)
            results.append(result)
        return sorted(results, key=lambda x: x.rate_kb_s, reverse=True)

    def clear(self) -> None:
        self._data.clear()
        self._window_start = None

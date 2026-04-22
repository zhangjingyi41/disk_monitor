"""Process name cache with TTL support."""

import time
from typing import Optional, Dict
import psutil


class ProcessCache:
    def __init__(self, ttl_seconds: float = 30.0):
        self._cache: Dict[int, tuple] = {}
        self._ttl = ttl_seconds

    def get_process_name(self, pid: int) -> str:
        # Special handling for pid 0 (system/kernel)
        if pid == 0:
            return 'SYSTEM'
        
        now = time.time()
        if pid in self._cache:
            name, timestamp = self._cache[pid]
            if now - timestamp < self._ttl:
                return name
            del self._cache[pid]

        name = self._fetch_process_name(pid)
        if name:
            self._cache[pid] = (name, now)
        return name or f"PID:{pid}"

    def _fetch_process_name(self, pid: int) -> Optional[str]:
        try:
            proc = psutil.Process(pid)
            return proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    def invalidate(self, pid: int) -> None:
        if pid in self._cache:
            del self._cache[pid]

    def clear(self) -> None:
        self._cache.clear()

    def cleanup_expired(self) -> int:
        now = time.time()
        expired = [
            pid for pid, (_, timestamp) in self._cache.items()
            if now - timestamp >= self._ttl
        ]
        for pid in expired:
            del self._cache[pid]
        return len(expired)

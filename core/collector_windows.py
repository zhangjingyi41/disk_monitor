"""Windows I/O collector using psutil."""

import time
import psutil
import re
from typing import List, Dict

from core.models import IOEvent, OperationType
from core.collector_base import CollectorBase


class WindowsCollector(CollectorBase):
    def __init__(self, use_approx: bool = False):
        super().__init__()
        self._last_io_counters: Dict[int, dict] = {}
        self._last_disk_counters: Dict[str, dict] = {}
        self._last_check_time = time.time()
        self._process_name_cache: Dict[int, str] = {}
        self._use_process_io = not use_approx  # Use process IO unless in approx mode
        self._use_approx = use_approx

    def _start_native(self) -> bool:
        # Current implementation relies on base polling loop.
        return False

    def _stop_native(self) -> None:
        pass
    
    def _format_disk_name(self, disk_name: str) -> str:
        """Format physical disk name to be more user-friendly.
        
        Converts 'PhysicalDrive0' to 'Disk 0', 'PhysicalDrive1' to 'Disk 1', etc.
        Also handles other disk naming conventions.
        """
        # Handle PhysicalDriveX pattern
        match = re.match(r'PhysicalDrive(\d+)', disk_name, re.IGNORECASE)
        if match:
            return f"Disk {match.group(1)}"
        
        # Handle other patterns like C:, D:, etc.
        if re.match(r'^[A-Za-z]:$', disk_name):
            return disk_name
        
        return disk_name

    def _collect_events(self) -> List[IOEvent]:
        events = []
        current_time = time.time()

        if self._use_process_io:
            events.extend(self._collect_process_io(current_time))
        else:
            events.extend(self._collect_disk_io(current_time))

        self._last_check_time = current_time
        return events

    def _collect_process_io(self, current_time: float) -> List[IOEvent]:
        events = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    io = proc.io_counters()

                    if io is None:
                        continue

                    self._process_name_cache[pid] = name
                    last_io = self._last_io_counters.get(pid)

                    if last_io:
                        read_bytes = io.read_bytes - last_io['read_bytes']
                        write_bytes = io.write_bytes - last_io['write_bytes']

                        if read_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=pid,
                                operation=OperationType.READ,
                                bytes=read_bytes,
                                disk='SYSTEM'
                            ))

                        if write_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=pid,
                                operation=OperationType.WRITE,
                                bytes=write_bytes,
                                disk='SYSTEM'
                            ))

                    self._last_io_counters[pid] = {
                        'read_bytes': io.read_bytes,
                        'write_bytes': io.write_bytes
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                    continue
        except Exception:
            pass
        return events

    def _collect_disk_io(self, current_time: float) -> List[IOEvent]:
        events = []
        try:
            counters = psutil.disk_io_counters(perdisk=True)
            if counters:
                for disk_name, counter in counters.items():
                    last_counter = self._last_disk_counters.get(disk_name)

                    if last_counter:
                        read_bytes = counter.read_bytes - last_counter['read_bytes']
                        write_bytes = counter.write_bytes - last_counter['write_bytes']

                        if read_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=0,
                                operation=OperationType.READ,
                                bytes=read_bytes,
                                disk=self._format_disk_name(disk_name)
                            ))

                        if write_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=0,
                                operation=OperationType.WRITE,
                                bytes=write_bytes,
                                disk=self._format_disk_name(disk_name)
                            ))

                    self._last_disk_counters[disk_name] = {
                        'read_bytes': counter.read_bytes,
                        'write_bytes': counter.write_bytes
                    }
        except Exception:
            pass
        return events

    def get_process_name(self, pid: int) -> str:
        if pid == 0:
            return 'SYSTEM'
        return self._process_name_cache.get(pid, f'PID:{pid}')


def create_windows_collector(use_approx: bool = False) -> WindowsCollector:
    return WindowsCollector(use_approx=use_approx)

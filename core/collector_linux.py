"""Linux I/O collector using psutil."""

import time
import psutil
from typing import List, Dict, Optional

from core.models import IOEvent, OperationType
from core.collector_base import CollectorBase


class LinuxCollector(CollectorBase):
    def __init__(self):
        super().__init__()
        self._last_io_counters: Dict[int, dict] = {}
        self._last_check_time = time.time()
        self._process_name_cache: Dict[int, str] = {}
        self._use_disk_io = True

    def _start_native(self) -> bool:
        self._check_io_availability()
        # Current implementation relies on base polling loop.
        return False

    def _stop_native(self) -> None:
        pass

    def _check_io_availability(self) -> None:
        try:
            io = psutil.disk_io_counters()
            if io is None:
                self._use_disk_io = False
        except Exception:
            self._use_disk_io = False

        if not self._use_disk_io:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    proc.io_counters()
                    break
                self._use_disk_io = True
            except Exception:
                self._use_disk_io = False

    def _collect_events(self) -> List[IOEvent]:
        events = []
        current_time = time.time()

        if self._use_disk_io:
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
                    last_counter = self._last_io_counters.get(disk_name)

                    if last_counter:
                        read_bytes = counter.read_bytes - last_counter['read_bytes']
                        write_bytes = counter.write_bytes - last_counter['write_bytes']

                        if read_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=0,
                                operation=OperationType.READ,
                                bytes=read_bytes,
                                disk=disk_name
                            ))

                        if write_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=0,
                                operation=OperationType.WRITE,
                                bytes=write_bytes,
                                disk=disk_name
                            ))

                    self._last_io_counters[disk_name] = {
                        'read_bytes': counter.read_bytes,
                        'write_bytes': counter.write_bytes
                    }
        except Exception:
            pass
        return events

    def get_process_name(self, pid: int) -> str:
        return self._process_name_cache.get(pid, f'PID:{pid}')


def create_linux_collector(use_approx: bool = False) -> LinuxCollector:
    return LinuxCollector()

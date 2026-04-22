"""Linux I/O collector using psutil."""

import time
import psutil
from typing import List, Dict, Optional

from core.models import IOEvent, OperationType
from core.collector_base import CollectorBase


class LinuxCollector(CollectorBase):
    def __init__(self, use_approx: bool = False):
        super().__init__()
        self._last_io_counters: Dict[int, dict] = {}
        self._last_check_time = time.time()
        self._process_name_cache: Dict[int, str] = {}
        self._use_disk_io = True
        self._use_approx = use_approx
        self._use_proc_stat = False
        self._file_mapper = None
        self._cleanup_counter = 0
        if not self._use_approx:
            # Only use file mapper in non-approx mode
            from core.file_mapper import FileMapper
            self._file_mapper = FileMapper(cache_ttl_seconds=10.0)

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
        
        # If we can't use disk IO and we're in approx mode, try proc stat
        if not self._use_disk_io and self._use_approx:
            try:
                with open('/proc/self/stat', 'r') as f:
                    content = f.read()
                    fields = content.split()
                    if len(fields) >= 43:
                        rchar = int(fields[41])
                        wchar = int(fields[42])
                        self._use_proc_stat = True
            except Exception:
                self._use_proc_stat = False
    
    def _get_disk_for_process(self, pid: int, operation: str) -> str:
        """Get the most likely disk for a process's I/O activity.
        
        Uses file mapping heuristics to determine which mount point
        the process is most likely accessing.
        """
        if self._use_approx or self._file_mapper is None:
            # In approx mode or if file mapper not available
            return 'SYSTEM'
        
        # Try to get disk from file mapper
        disk = self._file_mapper.get_most_likely_disk_for_process(pid, operation)
        if disk:
            return disk
        
        # Fall back to SYSTEM if unknown
        return 'SYSTEM'

    def _collect_events(self) -> List[IOEvent]:
        events = []
        current_time = time.time()

        if self._use_proc_stat:
            events.extend(self._collect_proc_stat_io(current_time))
        elif self._use_disk_io:
            events.extend(self._collect_process_io(current_time))
        else:
            events.extend(self._collect_disk_io(current_time))

        # Clean up expired cache entries periodically
        self._cleanup_counter += 1
        if self._cleanup_counter >= 20 and self._file_mapper is not None:
            self._file_mapper.cleanup_expired()
            self._cleanup_counter = 0

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
                                disk=self._get_disk_for_process(pid, "READ")
                            ))

                        if write_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=pid,
                                operation=OperationType.WRITE,
                                bytes=write_bytes,
                                disk=self._get_disk_for_process(pid, "WRITE")
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

    def _collect_proc_stat_io(self, current_time: float) -> List[IOEvent]:
        events = []
        try:
            import os
            import glob
            
            # Iterate through all /proc/[pid]/stat files
            for stat_path in glob.glob('/proc/[0-9]*/stat'):
                try:
                    pid = int(os.path.basename(os.path.dirname(stat_path)))
                    with open(stat_path, 'r') as f:
                        content = f.read()
                    fields = content.split()
                    if len(fields) < 43:
                        continue
                    
                    rchar = int(fields[41])
                    wchar = int(fields[42])
                    
                    # Get process name from stat file (field 2, enclosed in parentheses)
                    # Process name might contain spaces, so we need to parse carefully
                    # The stat format: pid (comm) state ... fields
                    # Find the last closing parenthesis
                    end_comm = content.rfind(')')
                    if end_comm == -1:
                        continue
                    
                    # Get process name (without parentheses)
                    comm = content[content.find('(')+1:end_comm]
                    self._process_name_cache[pid] = comm
                    
                    # Get last counters
                    last_counter = self._last_io_counters.get(pid)
                    if last_counter:
                        read_bytes = rchar - last_counter['read_bytes']
                        write_bytes = wchar - last_counter['write_bytes']
                        
                        if read_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=pid,
                                operation=OperationType.READ,
                                bytes=read_bytes,
                                disk='SYSTEM'  # Can't determine disk in proc stat
                            ))
                        
                        if write_bytes > 0:
                            events.append(IOEvent(
                                timestamp=current_time,
                                pid=pid,
                                operation=OperationType.WRITE,
                                bytes=write_bytes,
                                disk='SYSTEM'  # Can't determine disk in proc stat
                            ))
                    
                    # Update last counters
                    self._last_io_counters[pid] = {
                        'read_bytes': rchar,
                        'write_bytes': wchar
                    }
                    
                except (FileNotFoundError, PermissionError, ValueError, IndexError):
                    continue
        except Exception:
            pass
        return events

    def get_process_name(self, pid: int) -> str:
        if pid == 0:
            return 'SYSTEM'
        return self._process_name_cache.get(pid, f'PID:{pid}')


def create_linux_collector(use_approx: bool = False) -> LinuxCollector:
    return LinuxCollector(use_approx=use_approx)

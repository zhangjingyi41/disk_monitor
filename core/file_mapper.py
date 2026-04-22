"""File path to disk partition mapping utilities."""

import os
import sys
import time
from typing import Dict, Optional, Set, Tuple
import psutil

from utils.platform import is_windows, is_linux


class FileMapper:
    """Maps file paths to disk partitions."""
    
    def __init__(self, cache_ttl_seconds: float = 5.0):
        self._cache_ttl = cache_ttl_seconds
        self._drive_cache: Dict[str, str] = {}  # file_path -> drive/disk
        self._cache_timestamp: Dict[str, float] = {}  # file_path -> last_update
        self._process_drive_cache: Dict[int, Set[str]] = {}  # pid -> set of drives
        self._process_cache_timestamp: Dict[int, float] = {}  # pid -> last_update
        
        # Platform-specific mappings
        self._drive_letters = []
        self._mount_points = []
        self._nt_to_drive: Dict[str, str] = {}
        
        # Pre-build drive mappings
        self._build_drive_mappings()
    
    def _build_drive_mappings(self) -> None:
        """Build initial drive mappings."""
        if is_windows():
            self._build_windows_drive_mappings()
        elif is_linux():
            self._build_linux_drive_mappings()
    
    def _build_windows_drive_mappings(self) -> None:
        """Build Windows drive letter mappings and NT device path mappings."""
        import string
        
        # Build list of valid drive letters
        self._drive_letters = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                self._drive_letters.append(letter)
        
        # Build NT device path to drive letter mapping
        self._nt_to_drive: Dict[str, str] = {}
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            for drive_letter in self._drive_letters:
                drive = f"{drive_letter}:"
                # QueryDosDeviceW returns the NT device path for a drive
                buffer = ctypes.create_unicode_buffer(1024)
                if kernel32.QueryDosDeviceW(drive, buffer, len(buffer)):
                    nt_path = buffer.value
                    if nt_path:
                        # Store mapping in lowercase for case-insensitive comparison
                        self._nt_to_drive[nt_path.lower()] = drive
        except (ImportError, AttributeError, OSError):
            # If we can't load ctypes or API fails, just continue without NT mapping
            pass
    
    def _build_linux_drive_mappings(self) -> None:
        """Build Linux mount point mappings."""
        self._mount_points = []
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint:
                self._mount_points.append(part.mountpoint)
        # Sort by length (longest first) for proper prefix matching
        self._mount_points.sort(key=len, reverse=True)
    
    def _get_drive_from_path_windows(self, file_path: str) -> Optional[str]:
        """Extract drive letter from Windows path."""
        if not file_path:
            return None
        
        # Handle different path formats
        file_path_lower = file_path.lower()
        
        # Check for drive letter pattern (C:\...)
        if len(file_path) >= 2 and file_path[1] == ':':
            drive = file_path[0:2].upper()
            if drive[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                return drive
        
        # Check for UNC path (\\server\share...)
        if file_path.startswith('\\\\'):
            # For UNC paths, we can't determine physical drive easily
            # Return as NETWORK
            return 'NETWORK'
        
        # Check for device path (\Device\HarddiskVolume...)
        if file_path_lower.startswith('\\device\\'):
            # Try to map NT device path to drive letter
            for nt_path, drive in self._nt_to_drive.items():
                if file_path_lower.startswith(nt_path.lower()):
                    return drive
            # If no mapping found but it's a harddiskvolume path, try to extract volume number
            if 'harddiskvolume' in file_path_lower:
                # Extract volume number: \Device\HarddiskVolume1\... -> HarddiskVolume1
                parts = file_path.split('\\')
                if len(parts) >= 3 and 'harddiskvolume' in parts[2].lower():
                    # Return generic PHYSICAL with volume number
                    volume = parts[2][len('HarddiskVolume'):]
                    return f'PHYSICAL{volume}'
        
        return None
    
    def _get_mount_from_path_linux(self, file_path: str) -> Optional[str]:
        """Get mount point from Linux path."""
        if not file_path:
            return None
        
        for mount_point in self._mount_points:
            if file_path.startswith(mount_point):
                return mount_point
        
        return None
    
    def map_file_to_disk(self, file_path: str) -> Optional[str]:
        """Map a file path to a disk identifier."""
        if not file_path:
            return None
        
        # Check cache
        now = time.time()
        if file_path in self._drive_cache:
            if now - self._cache_timestamp.get(file_path, 0) < self._cache_ttl:
                return self._drive_cache[file_path]
        
        # Map based on platform
        disk = None
        if is_windows():
            disk = self._get_drive_from_path_windows(file_path)
        elif is_linux():
            disk = self._get_mount_from_path_linux(file_path)
        
        # Update cache
        if disk:
            self._drive_cache[file_path] = disk
            self._cache_timestamp[file_path] = now
        
        return disk
    
    def get_process_drives(self, pid: int) -> Set[str]:
        """Get set of drives/mount points used by a process."""
        now = time.time()
        
        # Check cache
        if pid in self._process_drive_cache:
            if now - self._process_cache_timestamp.get(pid, 0) < self._cache_ttl:
                return self._process_drive_cache[pid].copy()
        
        drives = set()
        try:
            proc = psutil.Process(pid)
            
            # Get open files
            try:
                open_files = proc.open_files()
                for open_file in open_files:
                    file_path = open_file.path
                    disk = self.map_file_to_disk(file_path)
                    if disk:
                        drives.add(disk)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
            # On Windows, also check current working directory
            try:
                cwd = proc.cwd()
                disk = self.map_file_to_disk(cwd)
                if disk:
                    drives.add(disk)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
            # Cache results
            self._process_drive_cache[pid] = drives.copy()
            self._process_cache_timestamp[pid] = now
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        
        return drives
    
    def get_most_likely_disk_for_process(self, pid: int, operation: str = "READ") -> Optional[str]:
        """Get the most likely disk for a process's I/O activity.
        
        This is a heuristic method - it returns the first drive from the
        process's open files, or None if unknown.
        """
        drives = self.get_process_drives(pid)
        if drives:
            # Return the first drive (could implement more sophisticated logic)
            return next(iter(drives))
        return None
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._drive_cache.clear()
        self._cache_timestamp.clear()
        self._process_drive_cache.clear()
        self._process_cache_timestamp.clear()
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries."""
        now = time.time()
        expired = []
        
        # Clean file path cache
        for file_path, timestamp in self._cache_timestamp.items():
            if now - timestamp >= self._cache_ttl:
                expired.append(file_path)
        
        for file_path in expired:
            self._drive_cache.pop(file_path, None)
            self._cache_timestamp.pop(file_path, None)
        
        # Clean process cache
        expired_pids = []
        for pid, timestamp in self._process_cache_timestamp.items():
            if now - timestamp >= self._cache_ttl:
                expired_pids.append(pid)
        
        for pid in expired_pids:
            self._process_drive_cache.pop(pid, None)
            self._process_cache_timestamp.pop(pid, None)
        
        return len(expired) + len(expired_pids)
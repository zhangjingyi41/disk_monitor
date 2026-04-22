"""Disk and mount point scanner."""

import os
from typing import List, Optional

import psutil

from core.models import DiskInfo
from utils.platform import is_windows, is_linux, is_wsl


def get_disk_partitions() -> List[DiskInfo]:
    partitions = []
    for part in psutil.disk_partitions(all=True):
        if is_windows():
            if _is_valid_windows_partition(part):
                usage = _get_disk_usage(part.mountpoint)
                partitions.append(DiskInfo(
                    name=part.device,
                    mountpoint=part.mountpoint,
                    total=usage.total if usage else 0,
                    used=usage.used if usage else 0,
                    free=usage.free if usage else 0,
                    fstype=part.fstype
                ))
        elif is_linux():
            if _is_valid_linux_partition(part):
                usage = _get_disk_usage(part.mountpoint)
                partitions.append(DiskInfo(
                    name=part.device,
                    mountpoint=part.mountpoint,
                    total=usage.total if usage else 0,
                    used=usage.used if usage else 0,
                    free=usage.free if usage else 0,
                    fstype=part.fstype
                ))
    return partitions


def _is_valid_windows_partition(part) -> bool:
    if part.fstype == '':
        return False
    if 'cdrom' in part.opts.lower():
        return False
    if not part.mountpoint:
        return False
    return True


def _is_valid_linux_partition(part) -> bool:
    if not part.mountpoint or not part.fstype:
        return False
    if part.mountpoint == '/' or part.mountpoint.startswith('/boot'):
        return True
    if part.fstype in ('ext4', 'ext3', 'xfs', 'btrfs', 'ntfs', 'vfat'):
        return True
    return False


def _get_disk_usage(mountpoint: str) -> Optional[object]:
    try:
        return psutil.disk_usage(mountpoint)
    except (PermissionError, OSError):
        return None


def get_device_to_mountpoint_map() -> dict:
    mapping = {}
    if is_windows():
        for part in psutil.disk_partitions(all=False):
            if part.device and part.mountpoint:
                mapping[part.device] = part.mountpoint
    elif is_linux():
        try:
            with open('/proc/self/mountinfo', 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    device = parts[2] if len(parts) > 2 else ''
                    mountpoint = parts[1] if len(parts) > 1 else ''
                    if device and mountpoint:
                        mapping[device] = mountpoint
        except (FileNotFoundError, PermissionError):
            pass
    return mapping


def get_all_mountpoints() -> List[str]:
    mountpoints = []
    if is_windows():
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint:
                mountpoints.append(part.mountpoint)
    elif is_linux():
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint:
                mountpoints.append(part.mountpoint)
    return mountpoints

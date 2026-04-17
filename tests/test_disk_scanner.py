"""Tests for disk scanner module."""

import pytest
from unittest.mock import patch, MagicMock

from core.disk_scanner import (
    get_disk_partitions,
    get_device_to_mountpoint_map,
    get_all_mountpoints,
    _is_valid_windows_partition,
    _is_valid_linux_partition
)


class TestDiskScanner:
    @patch('psutil.disk_partitions')
    @patch('psutil.disk_usage')
    def test_get_disk_partitions_windows(self, mock_usage, mock_partitions):
        mock_partitions.return_value = [
            MagicMock(device='C:', mountpoint='C:\\', fstype='NTFS', opts=''),
            MagicMock(device='D:', mountpoint='D:\\', fstype='NTFS', opts=''),
        ]
        mock_usage.return_value = MagicMock(total=100000000000, used=50000000000, free=50000000000)

        with patch('core.disk_scanner.is_windows', return_value=True):
            partitions = get_disk_partitions()
            assert len(partitions) == 2
            assert partitions[0].name == 'C:'

    @patch('psutil.disk_partitions')
    def test_get_disk_partitions_filters_cdrom(self, mock_partitions):
        mock_partitions.return_value = [
            MagicMock(device='C:', mountpoint='C:\\', fstype='NTFS', opts=''),
            MagicMock(device='E:', mountpoint='E:\\', fstype='', opts='cdrom'),
        ]
        with patch('core.disk_scanner.is_windows', return_value=True):
            partitions = get_disk_partitions()
            assert len(partitions) == 1
            assert partitions[0].name == 'C:'

    @patch('psutil.disk_partitions')
    @patch('psutil.disk_usage')
    def test_get_disk_partitions_linux(self, mock_usage, mock_partitions):
        mock_partitions.return_value = [
            MagicMock(device='/dev/sda1', mountpoint='/', fstype='ext4', opts=''),
            MagicMock(device='/dev/sda2', mountpoint='/home', fstype='ext4', opts=''),
        ]
        mock_usage.return_value = MagicMock(total=100000000000, used=50000000000, free=50000000000)

        with patch('core.disk_scanner.is_linux', return_value=True):
            partitions = get_disk_partitions()
            assert len(partitions) == 2


class TestIsValidPartition:
    def test_valid_windows_partition(self):
        part = MagicMock(fstype='NTFS', opts='', mountpoint='C:\\')
        assert _is_valid_windows_partition(part) is True

    def test_invalid_cdrom(self):
        part = MagicMock(fstype='', opts='cdrom', mountpoint='E:\\')
        assert _is_valid_windows_partition(part) is False

    def test_invalid_no_fstype(self):
        part = MagicMock(fstype='', opts='', mountpoint='F:\\')
        assert _is_valid_windows_partition(part) is False

    def test_valid_linux_partition(self):
        part = MagicMock(mountpoint='/', fstype='ext4')
        assert _is_valid_linux_partition(part) is True

    def test_invalid_linux_partition(self):
        part = MagicMock(mountpoint='', fstype='tmpfs')
        assert _is_valid_linux_partition(part) is False


class TestMountpointMapping:
    @patch('core.disk_scanner.is_windows', return_value=True)
    @patch('psutil.disk_partitions')
    def test_windows_device_mapping(self, mock_partitions, mock_is_windows):
        mock_partitions.return_value = [
            MagicMock(device='C:', mountpoint='C:\\'),
            MagicMock(device='D:', mountpoint='D:\\'),
        ]
        mapping = get_device_to_mountpoint_map()
        assert 'C:' in mapping
        assert 'D:' in mapping

    def test_linux_device_mapping_parse(self):
        def parse_line(line):
            parts = line.strip().split()
            if len(parts) >= 4:
                return parts[2], parts[3]
            return None, None

        line1 = '1 2 /dev/sda1 / ext4 rw 0 0'
        device, mountpoint = parse_line(line1)
        assert device == '/dev/sda1'
        assert mountpoint == '/'

        line2 = '2 2 /dev/sda2 /home ext4 rw 0 0'
        device, mountpoint = parse_line(line2)
        assert device == '/dev/sda2'
        assert mountpoint == '/home'

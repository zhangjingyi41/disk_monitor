"""Tests for platform detection module."""

import pytest
from unittest.mock import patch
import sys

from utils.platform import (
    get_platform_name,
    is_windows,
    is_linux,
    is_wsl,
    is_macos,
    supports_etw,
    supports_ebpf
)


class TestPlatformDetection:
    @patch('sys.platform', 'win32')
    def test_is_windows(self):
        assert is_windows() is True
        assert is_linux() is False
        assert is_macos() is False

    @patch('sys.platform', 'linux')
    @patch('builtins.open', create=True)
    def test_is_wsl(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = 'microsoftUBR'
        assert is_wsl() is True

    @patch('sys.platform', 'linux')
    def test_is_linux_not_wsl(self):
        with patch('builtins.open', create=True, side_effect=FileNotFoundError):
            assert is_linux() is True
            assert is_wsl() is False

    @patch('sys.platform', 'darwin')
    def test_is_macos(self):
        assert is_macos() is True

    @patch('sys.platform', 'win32')
    def test_get_platform_name_windows(self):
        assert get_platform_name() == 'windows'

    @patch('sys.platform', 'linux')
    @patch('builtins.open', create=True)
    def test_get_platform_name_wsl(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = 'microsoft'
        assert get_platform_name() == 'wsl'


class TestFeatureSupport:
    @patch('sys.platform', 'win32')
    def test_supports_etw_windows(self):
        assert supports_etw() is True

    @patch('sys.platform', 'linux')
    def test_supports_etw_linux(self):
        assert supports_etw() is False

    @patch('sys.platform', 'linux')
    def test_supports_ebpf_linux(self):
        with patch('builtins.open', create=True, side_effect=FileNotFoundError):
            assert supports_ebpf() is True

    @patch('sys.platform', 'linux')
    @patch('builtins.open', create=True)
    def test_supports_ebpf_wsl(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = 'microsoft'
        assert supports_ebpf() is False

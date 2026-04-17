"""Tests for CLI display module."""

import pytest
from unittest.mock import patch, MagicMock
import io
import sys

from core.models import DiskActivity
from ui.display import CLIDisplayCallback


class TestCLIDisplayCallback:
    def setup_method(self):
        self.callback = CLIDisplayCallback()

    def test_output_empty_activities(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.callback.output([], 1000)
            output = mock_stdout.getvalue()
            assert '暂无磁盘活动' in output

    def test_output_with_activities(self):
        activities = [
            DiskActivity(disk='C:', status='READ', pid=1234, process_name='python.exe', rate=1024.5),
            DiskActivity(disk='D:', status='WRITE', pid=5678, process_name='code.exe', rate=512.3),
        ]
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.callback.output(activities, 300)
            output = mock_stdout.getvalue()
            assert 'C:' in output
            assert 'python.exe' in output
            assert '1234' in output
            assert 'D:' in output
            assert 'code.exe' in output

    def test_output_read_write_both(self):
        activities = [
            DiskActivity(disk='C:', status='READ/WRITE', pid=1234, process_name='test.exe', rate=100.0),
        ]
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.callback.output(activities, 1000)
            output = mock_stdout.getvalue()
            assert 'READ/WRITE' in output

    def test_set_refresh_interval(self):
        self.callback.set_refresh_interval(500)
        assert self.callback._interval_ms == 500

    def test_on_start(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.callback.on_start()
            output = mock_stdout.getvalue()
            assert '已启动' in output

    def test_on_stop(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.callback.on_stop()
            output = mock_stdout.getvalue()
            assert '已停止' in output

    def test_format_rate_kb(self):
        rate_str = self.callback._format_rate(500.0)
        assert 'KB/s' in rate_str
        assert '500.0' in rate_str

    def test_format_rate_mb(self):
        rate_str = self.callback._format_rate(2048.0)
        assert 'MB/s' in rate_str

    def test_clear_screen(self):
        with patch('os.system') as mock_system:
            self.callback._clear_screen()
            mock_system.assert_called_once()

    @patch('sys.platform', 'win32')
    def test_clear_screen_windows(self):
        callback = CLIDisplayCallback()
        with patch('os.system') as mock_system:
            callback._clear_screen()
            mock_system.assert_called_with('cls')

    @patch('sys.platform', 'linux')
    def test_clear_screen_linux(self):
        callback = CLIDisplayCallback()
        with patch('os.system') as mock_system:
            callback._clear_screen()
            mock_system.assert_called_with('clear')

"""Tests for process cache module."""

import pytest
import time
from unittest.mock import patch, MagicMock

from core.process_cache import ProcessCache


class TestProcessCache:
    def test_cache_init(self):
        cache = ProcessCache(ttl_seconds=10.0)
        assert cache._ttl == 10.0
        cache.clear()

    def test_get_process_name(self):
        cache = ProcessCache(ttl_seconds=30.0)
        with patch('psutil.Process') as mock_process:
            mock_proc = MagicMock()
            mock_proc.name.return_value = 'python.exe'
            mock_process.return_value = mock_proc

            name = cache.get_process_name(1234)
            assert name == 'python.exe'
            assert 1234 in cache._cache

    def test_cache_hit(self):
        cache = ProcessCache(ttl_seconds=30.0)
        cache._cache[1234] = ('python.exe', time.time())

        with patch('psutil.Process') as mock_process:
            name = cache.get_process_name(1234)
            assert name == 'python.exe'
            mock_process.assert_not_called()

    def test_cache_expired(self):
        cache = ProcessCache(ttl_seconds=1.0)
        cache._cache[1234] = ('python.exe', time.time() - 2.0)

        with patch('psutil.Process') as mock_process:
            mock_proc = MagicMock()
            mock_proc.name.return_value = 'newname.exe'
            mock_process.return_value = mock_proc

            name = cache.get_process_name(1234)
            assert name == 'newname.exe'

    def test_process_not_found(self):
        cache = ProcessCache()
        import psutil
        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(1234)):
            name = cache.get_process_name(9999)
            assert name == 'PID:9999'

    def test_invalidate(self):
        cache = ProcessCache()
        cache._cache[1234] = ('python.exe', time.time())
        cache.invalidate(1234)
        assert 1234 not in cache._cache

    def test_clear(self):
        cache = ProcessCache()
        cache._cache[1234] = ('python.exe', time.time())
        cache._cache[5678] = ('code.exe', time.time())
        cache.clear()
        assert len(cache._cache) == 0

    def test_cleanup_expired(self):
        cache = ProcessCache(ttl_seconds=1.0)
        cache._cache[1234] = ('python.exe', time.time())
        cache._cache[5678] = ('code.exe', time.time() - 2.0)
        cache._cache[9999] = ('test.exe', time.time() - 3.0)

        removed = cache.cleanup_expired()
        assert removed == 2
        assert 1234 in cache._cache
        assert 5678 not in cache._cache
        assert 9999 not in cache._cache

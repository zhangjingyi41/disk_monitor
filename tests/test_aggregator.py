"""Tests for aggregator module."""

import pytest
import time

from core.models import IOEvent, OperationType, AggregatedResult
from core.aggregator import Aggregator, calc_rate


class TestAggregator:
    def test_aggregator_init(self):
        agg = Aggregator(window_ms=500)
        assert agg.window_ms == 500
        assert agg.has_activity() is False

    def test_add_read_event(self):
        agg = Aggregator()
        event = IOEvent(
            timestamp=time.time(),
            pid=1234,
            operation=OperationType.READ,
            bytes=1024,
            disk='C:'
        )
        agg.add_event(event, 'test.exe')
        assert agg.has_activity() is True
        results = agg.get_results()
        assert len(results) == 1
        assert results[0].read_bytes == 1024
        assert results[0].write_bytes == 0

    def test_add_write_event(self):
        agg = Aggregator()
        event = IOEvent(
            timestamp=time.time(),
            pid=1234,
            operation=OperationType.WRITE,
            bytes=2048,
            disk='C:'
        )
        agg.add_event(event, 'test.exe')
        results = agg.get_results()
        assert len(results) == 1
        assert results[0].write_bytes == 2048
        assert results[0].read_bytes == 0

    def test_aggregates_same_disk_pid(self):
        agg = Aggregator()
        t = time.time()
        event1 = IOEvent(t, 1234, OperationType.READ, 1024, 'C:')
        event2 = IOEvent(t, 1234, OperationType.READ, 2048, 'C:')
        agg.add_event(event1, 'test.exe')
        agg.add_event(event2, 'test.exe')
        results = agg.get_results()
        assert len(results) == 1
        assert results[0].read_bytes == 3072

    def test_separate_disk_pid(self):
        agg = Aggregator()
        t = time.time()
        event1 = IOEvent(t, 1234, OperationType.READ, 1024, 'C:')
        event2 = IOEvent(t, 5678, OperationType.READ, 2048, 'D:')
        agg.add_event(event1, 'test1.exe')
        agg.add_event(event2, 'test2.exe')
        results = agg.get_results()
        assert len(results) == 2

    def test_rate_calculation(self):
        agg = Aggregator(window_ms=1000)
        t = time.time()
        for _ in range(10):
            event = IOEvent(t, 1234, OperationType.READ, 10240, 'C:')
            agg.add_event(event, 'test.exe')
        results = agg.get_results()
        assert len(results) == 1
        expected_rate = (10240 * 10) / 1.0 / 1024
        assert results[0].rate_kb_s == pytest.approx(expected_rate, rel=0.1)

    def test_clear(self):
        agg = Aggregator()
        event = IOEvent(time.time(), 1234, OperationType.READ, 1024, 'C:')
        agg.add_event(event, 'test.exe')
        agg.clear()
        assert agg.has_activity() is False
        assert len(agg.get_results()) == 0


class TestCalcRate:
    def test_calc_rate_positive(self):
        rate = calc_rate(2000, 1000, 1.0)
        assert rate == 1000.0

    def test_calc_rate_zero_interval(self):
        rate = calc_rate(2000, 1000, 0.0)
        assert rate == 0.0

    def test_calc_rate_negative_interval(self):
        rate = calc_rate(2000, 1000, -1.0)
        assert rate == 0.0

    def test_calc_rate_negative_bytes(self):
        rate = calc_rate(1000, 2000, 1.0)
        assert rate < 0


class TestAggregatedResult:
    def test_to_activity_read(self):
        result = AggregatedResult('C:', 1234, 'test.exe', read_bytes=1024)
        activity = result.to_activity()
        assert activity.status == 'READ'
        assert activity.disk == 'C:'
        assert activity.pid == 1234

    def test_to_activity_write(self):
        result = AggregatedResult('D:', 5678, 'test.exe', write_bytes=2048)
        activity = result.to_activity()
        assert activity.status == 'WRITE'

    def test_to_activity_both(self):
        result = AggregatedResult('E:', 9999, 'test.exe', read_bytes=1024, write_bytes=2048)
        activity = result.to_activity()
        assert activity.status == 'READ/WRITE'

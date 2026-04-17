"""Tests for collector base lifecycle behavior."""

import time
from typing import List

from core.collector_base import CollectorBase
from core.models import IOEvent, OperationType


class PollingCollector(CollectorBase):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def _start_native(self) -> bool:
        return False

    def _stop_native(self) -> None:
        pass

    def _collect_events(self) -> List[IOEvent]:
        self.calls += 1
        return [
            IOEvent(
                timestamp=time.time(),
                pid=1,
                operation=OperationType.READ,
                bytes=1,
                disk="SYSTEM",
            )
        ]


def test_start_with_polling_mode_runs_collect_loop():
    collector = PollingCollector()
    collector.set_interval(10)
    received = []

    collector.start(received.append)
    time.sleep(0.05)
    collector.stop()

    assert collector.calls > 0
    assert len(received) > 0

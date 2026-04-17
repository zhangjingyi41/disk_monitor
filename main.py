"""Main entry point for disk monitor."""

import signal
import sys
import time
from typing import Optional

from core.collector import create_collector, is_approx_mode_required
from core.aggregator import Aggregator
from core.process_cache import ProcessCache
from core.models import IOEvent, DiskActivity
from core.disk_scanner import get_disk_partitions
from ui.callback import OutputCallback
from utils.config import parse_args, Config


class DiskMonitor:
    def __init__(self, config: Config, callback: OutputCallback):
        self._config = config
        self._callback = callback
        self._collector = None
        self._aggregator = Aggregator(window_ms=config.window_ms)
        self._process_cache = ProcessCache(ttl_seconds=30.0)
        self._running = False
        self._approx_mode = False
        self._last_render_time = 0.0

    def _on_io_event(self, event: IOEvent) -> None:
        process_name = self._process_cache.get_process_name(event.pid)
        self._aggregator.add_event(event, process_name)

    def _get_refresh_interval(self) -> int:
        if self._aggregator.has_activity():
            return self._config.active_refresh_ms
        return self._config.idle_refresh_ms

    def _render(self) -> None:
        results = self._aggregator.get_results()
        activities = [r.to_activity() for r in results[:self._config.top_n]]
        self._callback.output(activities, self._get_refresh_interval())

    def start(self) -> None:
        self._approx_mode = is_approx_mode_required() or self._config.approx_mode

        if self._approx_mode:
            print("[Approx Mode] 进程与磁盘归因可能不精确")

        self._collector = create_collector(use_approx=self._approx_mode)
        self._collector.start(self._on_io_event)

        self._callback.on_start()
        self._running = True

        try:
            while self._running:
                interval = self._get_refresh_interval()
                time.sleep(interval / 1000.0)
                self._render()
                self._process_cache.cleanup_expired()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        if self._collector:
            self._collector.stop()
        self._callback.on_stop()
        print("程序已退出")


def main():
    config = parse_args()

    print_disk_info()

    from ui.display import CLIDisplayCallback
    callback = CLIDisplayCallback()

    monitor = DiskMonitor(config, callback)
    monitor.start()


def print_disk_info():
    print("=" * 50)
    print("检测到的磁盘分区:")
    partitions = get_disk_partitions()
    for p in partitions:
        total_gb = p.total / (1024 ** 3) if p.total else 0
        print(f"  {p.name} ({p.mountpoint}) - {p.fstype} - {total_gb:.1f}GB")
    if not partitions:
        print("  未检测到磁盘分区")
    print("=" * 50)
    print()


if __name__ == '__main__':
    main()

"""CLI display implementation using clear and redraw."""

import os
import sys
import time
from typing import List

from core.models import DiskActivity
from ui.callback import OutputCallback


class CLIDisplayCallback(OutputCallback):
    def __init__(self):
        self._interval_ms = 1000
        self._last_render_time = 0.0
        self._is_windows = sys.platform == 'win32'

    def output(self, activities: List[DiskActivity], interval_ms: int) -> None:
        self._clear_screen()
        self._print_header(interval_ms)
        self._print_activities(activities)
        sys.stdout.flush()

    def set_refresh_interval(self, interval_ms: int) -> None:
        self._interval_ms = interval_ms

    def on_start(self) -> None:
        self._clear_screen()
        print("=" * 50)
        print("硬盘状态监听器已启动")
        print("按 Ctrl+C 退出")
        print("=" * 50)
        print()

    def on_stop(self) -> None:
        self._clear_screen()
        print("=" * 50)
        print("硬盘状态监听器已停止")
        print("=" * 50)

    def _clear_screen(self) -> None:
        os.system('cls' if self._is_windows else 'clear')

    def _print_header(self, interval_ms: int) -> None:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{'=' * 50}")
        print(f"刷新间隔: {interval_ms}ms | 时间: {current_time}")
        print(f"{'=' * 50}")
        print()

    def _print_activities(self, activities: List[DiskActivity]) -> None:
        if not activities:
            print("暂无磁盘活动...")
            return

        grouped: dict = {}
        for activity in activities:
            if activity.disk not in grouped:
                grouped[activity.disk] = []
            grouped[activity.disk].append(activity)

        for disk, disk_activities in grouped.items():
            print(f"Disk: {disk}")
            for activity in disk_activities:
                status_color = self._get_status_color(activity.status)
                rate_str = self._format_rate(activity.rate)
                print(f"  Status: {status_color}{activity.status}\033[0m")
                print(f"  Pid: {activity.pid}")
                print(f"  ProcessName: {activity.process_name}")
                print(f"  Rate: {rate_str}")
            print()

    def _get_status_color(self, status: str) -> str:
        if "READ" in status:
            return "\033[94m"
        elif "WRITE" in status:
            return "\033[92m"
        return "\033[93m"

    def _format_rate(self, rate: float) -> str:
        if rate >= 1024:
            return f"{rate / 1024:.1f}MB/s"
        return f"{rate:.1f}KB/s"

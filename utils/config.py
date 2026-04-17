"""Configuration and argument parsing."""

import argparse
from dataclasses import dataclass


@dataclass
class Config:
    window_ms: int = 1000
    active_refresh_ms: int = 300
    idle_refresh_ms: int = 1500
    top_n: int = 10
    approx_mode: bool = False


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description='硬盘状态监听器 - 实时监控磁盘读写活动'
    )
    parser.add_argument(
        '--window-ms',
        type=int,
        default=1000,
        help='聚合窗口大小(ms)，默认1000'
    )
    parser.add_argument(
        '--active-refresh-ms',
        type=int,
        default=300,
        help='活跃期刷新间隔(ms)，默认300'
    )
    parser.add_argument(
        '--idle-refresh-ms',
        type=int,
        default=1500,
        help='空闲期刷新间隔(ms)，默认1500'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=10,
        help='每磁盘展示的最多进程数，默认10'
    )
    parser.add_argument(
        '--approx-mode',
        action='store_true',
        help='强制使用近似模式(psutil)'
    )

    args = parser.parse_args()
    return Config(
        window_ms=args.window_ms,
        active_refresh_ms=args.active_refresh_ms,
        idle_refresh_ms=args.idle_refresh_ms,
        top_n=args.top_n,
        approx_mode=args.approx_mode
    )

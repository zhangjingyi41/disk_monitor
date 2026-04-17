"""Platform detection utilities."""

import platform
import sys


def get_platform_name() -> str:
    if sys.platform == 'win32':
        return 'windows'
    elif is_wsl():
        return 'wsl'
    elif sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform == 'darwin':
        return 'macos'
    return 'unknown'


def is_windows() -> bool:
    return sys.platform == 'win32'


def is_linux() -> bool:
    return sys.platform.startswith('linux')


def is_wsl() -> bool:
    if sys.platform == 'win32':
        return False
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except (FileNotFoundError, PermissionError):
        return False


def is_macos() -> bool:
    return sys.platform == 'darwin'


def supports_etw() -> bool:
    return is_windows()


def supports_ebpf() -> bool:
    return is_linux() and not is_wsl()

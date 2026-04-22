"""Factory for creating platform-specific collectors."""

from utils.platform import is_windows, is_linux
from core.collector_base import CollectorBase
from core.collector_windows import create_windows_collector
from core.collector_linux import create_linux_collector


def create_collector(use_approx: bool = False) -> CollectorBase:
    if is_windows():
        return create_windows_collector(use_approx)
    elif is_linux():
        return create_linux_collector(use_approx)
    else:
        raise NotImplementedError(f"Unsupported platform")


def is_approx_mode_required() -> bool:
    from utils.platform import is_wsl
    # In WSL, psutil cannot get disk IO counters, so approximate mode is required
    if is_wsl():
        return True
    
    # Check if psutil can get disk IO counters
    try:
        import psutil
        io = psutil.disk_io_counters()
        if io is None:
            return True
    except Exception:
        return True
    
    return False

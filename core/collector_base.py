"""Base interface for I/O collectors."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable
import threading
import time

from core.models import IOEvent


class CollectorBase(ABC):
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[IOEvent], None]] = None
        self._interval_ms = 100

    @abstractmethod
    def _collect_events(self) -> List[IOEvent]:
        pass

    @abstractmethod
    def _start_native(self) -> bool:
        pass

    @abstractmethod
    def _stop_native(self) -> None:
        pass

    def start(self, callback: Callable[[IOEvent], None]) -> bool:
        if self._running:
            return True

        self._callback = callback
        self._running = True

        # Native mode means the subclass has started its own event loop/callback
        # and polling thread is not required.
        native_started = self._start_native()
        if native_started:
            return True

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        self._stop_native()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _poll_loop(self) -> None:
        while self._running:
            try:
                events = self._collect_events()
                for event in events:
                    if self._callback:
                        self._callback(event)
            except Exception:
                pass
            time.sleep(self._interval_ms / 1000.0)

    def set_interval(self, interval_ms: int) -> None:
        self._interval_ms = interval_ms

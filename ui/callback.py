"""GUI callback interface definition."""

from abc import ABC, abstractmethod
from typing import List

from core.models import DiskActivity


class OutputCallback(ABC):
    @abstractmethod
    def output(self, activities: List[DiskActivity], interval_ms: int) -> None:
        pass

    @abstractmethod
    def set_refresh_interval(self, interval_ms: int) -> None:
        pass

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

from __future__ import annotations

from abc import ABC, abstractmethod

from ..execution_event import ExecutionEvent


class ExecutionObserver(ABC):

    @abstractmethod
    def on_event(self, event: ExecutionEvent) -> None:
        """
        Receives an ExecutionEvent emitted during an execution.
        """
        raise NotImplementedError

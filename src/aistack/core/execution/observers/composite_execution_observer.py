from __future__ import annotations

from collections.abc import Iterable

from ..execution_event import ExecutionEvent
from .execution_observer import ExecutionObserver


class CompositeExecutionObserver(ExecutionObserver):

    def __init__(self, observers: Iterable[ExecutionObserver]):
        self._observers = tuple(observers)

    def on_event(self, event: ExecutionEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)

from ..execution_event import ExecutionEvent
from .execution_observer import ExecutionObserver


class NullExecutionObserver(ExecutionObserver):

    def on_event(self, event: ExecutionEvent) -> None:
        pass

from __future__ import annotations

from abc import ABC, abstractmethod

from aistack.kernel.tracing import ExecutionTrace


class TraceRepository(ABC):
    """
    Contract for storing execution traces.

    A TraceRepository preserves Runtime execution history.
    """

    @abstractmethod
    def save(
        self,
        trace: ExecutionTrace,
    ) -> None:
        """
        Store an execution trace.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> tuple[ExecutionTrace, ...]:
        """
        Return all stored execution traces.
        """
        raise NotImplementedError

"""
Knowledge Transaction - In-memory Operation Registry.
"""

from __future__ import annotations

from aistack.transaction.interfaces.operation_engine import OperationEngine
from aistack.transaction.interfaces.operation_registry import OperationRegistry


class InMemoryOperationRegistry(OperationRegistry):
    """
    Simple in-memory registry of operation engines.
    """

    def __init__(self) -> None:
        self._engines: dict[str, OperationEngine] = {}

    def register(
        self,
        operation_type: str,
        engine: OperationEngine,
    ) -> None:
        self._engines[operation_type] = engine

    def get(
        self,
        operation_type: str,
    ) -> OperationEngine:
        return self._engines[operation_type]

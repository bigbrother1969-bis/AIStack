"""
Knowledge Transaction - Default Transaction Executor.
"""

from __future__ import annotations

from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.interfaces.operation_registry import (
    OperationRegistry,
)


class DefaultTransactionExecutor:
    """
    Default implementation of a transaction executor.
    """

    def __init__(
        self,
        registry: OperationRegistry,
    ) -> None:
        self._registry = registry

    def execute(
        self,
        transaction: Transaction,
    ) -> None:
        """
        Execute all operations in the transaction.
        """

        for operation in transaction.operations:
            engine = self._registry.get(operation.kind)
            engine.execute(operation.payload)

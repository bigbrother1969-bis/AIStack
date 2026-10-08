"""
Knowledge Transaction - Default Transaction Executor.

Runs a transaction's operations in order, each through the engine
registered for its kind, and keeps their statuses: the first operation
that raises is `failed` (its message kept in `error`), the ones after
it `skipped`, the transaction `failed`; otherwise every operation and
the transaction `succeeded` (1.10, `ADR-0019` § 6 — the dock's first
real transactions). A listener, when given, is told as each operation
starts and ends, so a caller can record progress as it happens.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transaction.contracts.operation import Operation
from aistack.transaction.contracts.operation_status import OperationStatus
from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.contracts.transaction_status import TransactionStatus
from aistack.transaction.interfaces.operation_registry import (
    OperationRegistry,
)


class TransactionListener(Protocol):
    def started(self, operation: Operation) -> None: ...

    def finished(self, operation: Operation) -> None: ...


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
        listener: TransactionListener | None = None,
    ) -> Transaction:
        """
        Execute the operations in order; stop at the first failure.
        Returns the transaction, its statuses set.
        """

        transaction.status = TransactionStatus.RUNNING
        failed = False
        for operation in transaction.operations:
            if failed:
                operation.status = OperationStatus.SKIPPED
                continue
            operation.status = OperationStatus.RUNNING
            if listener is not None:
                listener.started(operation)
            try:
                engine = self._registry.get(operation.kind)
                operation.result = engine.execute(operation.payload)
            except Exception as error:  # noqa: BLE001 - kept on the operation; the transaction stops
                operation.status = OperationStatus.FAILED
                operation.error = str(error) or type(error).__name__
                failed = True
            else:
                operation.status = OperationStatus.SUCCEEDED
            if listener is not None:
                listener.finished(operation)
        transaction.status = TransactionStatus.FAILED if failed else TransactionStatus.SUCCEEDED
        return transaction

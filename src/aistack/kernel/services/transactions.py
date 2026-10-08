from __future__ import annotations

from dataclasses import dataclass

from aistack.transaction.executor.default_transaction_executor import (
    DefaultTransactionExecutor,
)
from aistack.transaction.registry.in_memory_operation_registry import (
    InMemoryOperationRegistry,
)


@dataclass(frozen=True, slots=True)
class TransactionServices:
    """
    The transaction service (`ADR-0019` § 6, 1.10): the registry of
    operation engines, by kind, and the executor that runs a
    transaction's operations through them. Bootstrap registers the
    `transport` engine; a caller that brings its own operations — the
    dock — registers its engines here before executing.
    """

    registry: InMemoryOperationRegistry
    executor: DefaultTransactionExecutor


def create_transaction_services() -> TransactionServices:
    registry = InMemoryOperationRegistry()
    return TransactionServices(registry=registry, executor=DefaultTransactionExecutor(registry))

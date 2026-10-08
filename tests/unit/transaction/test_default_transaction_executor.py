from __future__ import annotations

import pytest

from aistack.kernel.bootstrap.default import create_kernel
from aistack.transaction.adapters.transport_operation_engine import TransportOperationEngine
from aistack.transaction.contracts.operation import Operation
from aistack.transaction.contracts.operation_status import OperationStatus
from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.contracts.transaction_status import TransactionStatus
from aistack.transaction.executor.default_transaction_executor import DefaultTransactionExecutor
from aistack.transaction.interfaces.operation_engine import OperationEngine
from aistack.transaction.registry.in_memory_operation_registry import InMemoryOperationRegistry


class Echo(OperationEngine):
    def __init__(self, fail_on: object = None) -> None:
        self.seen: list[object] = []
        self.fail_on = fail_on

    def execute(self, payload: object) -> object:
        self.seen.append(payload)
        if payload == self.fail_on:
            raise RuntimeError(f"no {payload}")
        return f"did {payload}"


class Listener:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, str]] = []

    def started(self, operation: Operation) -> None:
        self.events.append(("started", operation.name, operation.status.value))

    def finished(self, operation: Operation) -> None:
        self.events.append(("finished", operation.name, operation.status.value))


def _executor(engine: OperationEngine) -> DefaultTransactionExecutor:
    registry = InMemoryOperationRegistry()
    registry.register("echo", engine)
    return DefaultTransactionExecutor(registry)


def _transaction(*payloads: str) -> Transaction:
    return Transaction(operations=[Operation(name=p, kind="echo", payload=p) for p in payloads])


def test_every_operation_succeeds_and_keeps_its_result():
    done = _executor(Echo()).execute(_transaction("a", "b"))

    assert done.status == TransactionStatus.SUCCEEDED
    assert [(op.status, op.result) for op in done.operations] == [
        (OperationStatus.SUCCEEDED, "did a"), (OperationStatus.SUCCEEDED, "did b"),
    ]


def test_the_first_failure_stops_the_transaction():
    engine = Echo(fail_on="b")
    listener = Listener()

    done = _executor(engine).execute(_transaction("a", "b", "c"), listener)

    assert done.status == TransactionStatus.FAILED
    assert [op.status for op in done.operations] == [
        OperationStatus.SUCCEEDED, OperationStatus.FAILED, OperationStatus.SKIPPED,
    ]
    assert done.operations[1].error == "no b"
    assert engine.seen == ["a", "b"]
    assert listener.events == [
        ("started", "a", "running"), ("finished", "a", "succeeded"),
        ("started", "b", "running"), ("finished", "b", "failed"),
    ]


def test_an_operation_of_an_unregistered_kind_fails_its_transaction():
    done = DefaultTransactionExecutor(InMemoryOperationRegistry()).execute(_transaction("a"))

    assert done.status == TransactionStatus.FAILED and done.operations[0].status == OperationStatus.FAILED


def test_the_kernel_carries_the_transaction_service_with_transport_registered():
    transactions = create_kernel().services.transactions

    assert isinstance(transactions.registry.get("transport"), TransportOperationEngine)
    assert isinstance(transactions.executor, DefaultTransactionExecutor)
    with pytest.raises(KeyError):
        transactions.registry.get("dock.apply")

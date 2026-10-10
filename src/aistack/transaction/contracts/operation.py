"""Knowledge Transaction - Operation contract."""

from __future__ import annotations

from dataclasses import dataclass

from .operation_status import OperationStatus


@dataclass(slots=True)
class Operation:
    """A unit of work executed within a transaction.

    The payload is opaque to the executor; only the engine registered for
    `kind` interprets it. The executor sets `result` (what the engine
    returned) and `error` (why it failed); see `ADR-0019` § 6.
    """

    name: str

    kind: str

    payload: object

    status: OperationStatus = OperationStatus.CREATED

    result: object = None

    error: str = ""

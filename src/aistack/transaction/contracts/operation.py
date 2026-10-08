"""
Knowledge Transaction - Operation contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from .operation_status import OperationStatus


@dataclass(slots=True)
class Operation:
    """
    A governed unit of work executed within a transaction.

    The payload is opaque to the orchestrator and is interpreted only by
    the specialized engine responsible for the operation kind.

    `result` holds what the engine returned, `error` why it failed —
    set by the executor (1.10, `ADR-0019` § 6).
    """

    name: str

    kind: str

    payload: object

    status: OperationStatus = OperationStatus.CREATED

    result: object = None

    error: str = ""

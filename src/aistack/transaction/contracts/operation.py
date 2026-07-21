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
    """

    name: str

    kind: str

    payload: object

    status: OperationStatus = OperationStatus.CREATED

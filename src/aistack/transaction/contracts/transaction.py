"""
Knowledge Transaction - Transaction contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .operation import Operation
from .transaction_status import TransactionStatus


@dataclass(slots=True)
class Transaction:
    """
    A governed transaction composed of one or more operations.
    """

    operations: list[Operation] = field(default_factory=list)

    status: TransactionStatus = TransactionStatus.CREATED

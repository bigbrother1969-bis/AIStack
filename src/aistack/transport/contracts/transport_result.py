"""
Knowledge Transport Layer - Transport Result contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.transport.contracts.transport_status import TransportStatus


@dataclass(frozen=True, slots=True)
class TransportResult:
    """
    Result returned by a Knowledge Transport Layer operation.
    """

    transaction_id: str

    status: TransportStatus

    delivered: bool

    verified: bool

    rollback_available: bool

    message: str = ""

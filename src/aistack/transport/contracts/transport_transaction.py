"""
Knowledge Transport Layer - Transport Transaction contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aistack.transport.contracts.delivery_mode import DeliveryMode
from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.contracts.transport_endpoint import TransportEndpoint
from aistack.transport.contracts.transport_status import TransportStatus


@dataclass(frozen=True, slots=True)
class TransportTransaction:
    """
    Current state of a governed transport transaction.

    This object represents the current state only.
    Historical changes belong to the History Repository.
    """

    transaction_id: str

    resource: ResourceReference

    source: TransportEndpoint

    destination: TransportEndpoint

    delivery_mode: DeliveryMode

    status: TransportStatus = TransportStatus.PENDING

    started_at: datetime | None = None

    completed_at: datetime | None = None

    attempt_count: int = 0

    rollback_available: bool = False

    previous_state_uri: str | None = None

    last_error: str | None = None

    correlation_id: str | None = None

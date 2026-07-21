"""
Knowledge Transport Layer - Transport Request contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.transport.contracts.delivery_mode import DeliveryMode
from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.contracts.transport_endpoint import TransportEndpoint


@dataclass(frozen=True, slots=True)
class TransportRequest:
    """
    Request submitted to the Knowledge Transport Layer.
    """

    source_resource: ResourceReference

    destination_resource: ResourceReference

    source: TransportEndpoint

    destination: TransportEndpoint

    delivery_mode: DeliveryMode

    correlation_id: str | None = None

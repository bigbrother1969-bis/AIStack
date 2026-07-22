from __future__ import annotations

from dataclasses import dataclass

from aistack.transport.default_transport_engine import (
    DefaultTransportEngine,
)
from aistack.transport.delivery_verifier import DeliveryVerifier
from aistack.transport.registry.in_memory_transport_registry import (
    InMemoryTransportRegistry,
)


@dataclass(frozen=True, slots=True)
class KernelServices:
    """
    Immutable aggregate of composed Kernel runtime services.

    KernelServices does not instantiate services, resolve dependencies,
    register capabilities, or orchestrate runtime operations.
    """

    transport_registry: InMemoryTransportRegistry
    delivery_verifier: DeliveryVerifier
    transport: DefaultTransportEngine

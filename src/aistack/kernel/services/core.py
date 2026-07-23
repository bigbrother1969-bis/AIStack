from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.services.execution import (
    ExecutionServices,
)

from aistack.kernel.services.knowledge.core import (
    KnowledgeServices,
)

from aistack.transport.default_transport_engine import (
    DefaultTransportEngine,
)
from aistack.transport.delivery_verifier import (
    DeliveryVerifier,
)
from aistack.transport.registry.in_memory_transport_registry import (
    InMemoryTransportRegistry,
)


@dataclass(frozen=True, slots=True)
class KernelServices:
    """
    Immutable aggregate of composed Kernel services.
    """

    transport_registry: InMemoryTransportRegistry
    delivery_verifier: DeliveryVerifier
    transport: DefaultTransportEngine

    execution: ExecutionServices
    knowledge: KnowledgeServices

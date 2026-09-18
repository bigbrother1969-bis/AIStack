from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.services.execution import (
    ExecutionServices,
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

    Carried a `knowledge: KnowledgeServices` field until
    2026-09-18 (`GOV-0002/OS-058`) — a repository wrapping the
    second, unwired `KnowledgeArtifact` definition, never called
    from any CLI or generator, its only persistence an in-memory
    dict that never survived a process. Removed along with that
    definition rather than retyped against the production one:
    nothing here ever consumed it.
    """

    transport_registry: InMemoryTransportRegistry
    delivery_verifier: DeliveryVerifier
    transport: DefaultTransportEngine

    execution: ExecutionServices

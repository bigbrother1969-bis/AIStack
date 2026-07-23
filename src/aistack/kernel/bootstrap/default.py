from __future__ import annotations

from aistack.kernel import Kernel

from aistack.kernel.bootstrap.catalog_views import (
    register_default_catalog_views,
)

from aistack.kernel.bootstrap.providers import (
    register_default_providers,
)

from aistack.kernel.bootstrap.selection import (
    register_default_selection_strategies,
)

from aistack.kernel.registries import KernelRegistries

from aistack.kernel.registries.catalog_view_registry import (
    CatalogViewRegistry,
)

from aistack.kernel.registries.provider_registry import (
    ProviderRegistry,
)

from aistack.kernel.registries.selection_strategy_registry import (
    SelectionStrategyRegistry,
)

from aistack.kernel.registries.task_registry import (
    TaskRegistry,
)

from aistack.kernel.services import (
    KernelServices,
)

from aistack.kernel.services.execution import (
    ExecutionServices,
)

from aistack.kernel.services.knowledge import (
    InMemoryKnowledgeRepository,
)

from aistack.kernel.services.knowledge.core import (
    KnowledgeServices,
)

from aistack.kernel.tracing.repository import (
    InMemoryTraceRepository,
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


def create_kernel() -> Kernel:
    """
    Compose and initialize the default AIStack Kernel.

    This function is the Runtime Composition Root.

    It is the only place responsible for creating
    the default Kernel dependency graph.
    """

    registries = KernelRegistries(
        providers=ProviderRegistry(),
        catalog_views=CatalogViewRegistry(),
        selection_strategies=SelectionStrategyRegistry(),
        tasks=TaskRegistry(),
    )

    transport_registry = InMemoryTransportRegistry()

    delivery_verifier = DeliveryVerifier()

    transport = DefaultTransportEngine(
        registry=transport_registry,
        delivery_verifier=delivery_verifier,
    )

    trace_repository = InMemoryTraceRepository()

    execution_services = ExecutionServices(
        trace_repository=trace_repository,
    )

    knowledge_repository = InMemoryKnowledgeRepository()

    knowledge_services = KnowledgeServices(
        repository=knowledge_repository,
    )

    services = KernelServices(
        transport_registry=transport_registry,
        delivery_verifier=delivery_verifier,
        transport=transport,
        execution=execution_services,
        knowledge=knowledge_services,
    )

    kernel = Kernel(
        registries=registries,
        services=services,
    )

    register_default_providers(kernel)

    register_default_catalog_views(kernel)

    register_default_selection_strategies(kernel)

    return kernel

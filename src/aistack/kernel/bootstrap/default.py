from __future__ import annotations

from aistack.kernel import Kernel

from aistack.kernel.bootstrap.catalog_views import (
    register_default_catalog_views,
)

from aistack.kernel.bootstrap.providers import (
    register_default_providers,
)

from aistack.kernel.bootstrap.tasks import (
    register_default_tasks,
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

from aistack.kernel.services.transactions import (
    create_transaction_services,
)

from aistack.transaction.adapters.transport_operation_engine import (
    TransportOperationEngine,
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

    # A transport is one kind of operation a transaction can hold
    # (ADR-0019 § 6); the dock registers its own kinds itself.
    transactions = create_transaction_services()
    transactions.registry.register(
        "transport",
        TransportOperationEngine(transport),
    )

    services = KernelServices(
        transport_registry=transport_registry,
        delivery_verifier=delivery_verifier,
        transport=transport,
        execution=execution_services,
        transactions=transactions,
    )

    kernel = Kernel(
        registries=registries,
        services=services,
    )

    register_default_providers(kernel)

    register_default_catalog_views(kernel)

    # Must run after `register_default_providers`: it looks up the
    # provider its one task wraps.
    register_default_tasks(kernel)

    return kernel


# No Selection Strategy is registered on purpose: `ByIdsSelectionStrategy`
# takes its identifiers in its constructor, so
# `aistack.selection.workflow` builds one per selection. The registry
# itself stays (ADR-0003) and is empty after bootstrap.

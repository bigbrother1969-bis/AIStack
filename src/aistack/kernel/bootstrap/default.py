from __future__ import annotations

from aistack.kernel import Kernel

from aistack.kernel.bootstrap.registrations import (
    load_registrations,
    register_declared,
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

from aistack.transaction.contracts.declaration_write import KIND as DECLARATION_WRITE
from aistack.transaction.engines.declaration_write import DeclarationWriteEngine
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
    # A declaration a person changes is written through the same service
    # (ADR-0027 § 11).
    transactions.registry.register(DECLARATION_WRITE, DeclarationWriteEngine())

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

    # The Kernel names no provider, catalog view or task: it registers
    # what `registrations.yml` declares (ADR-0027 § 8).
    register_declared(kernel, load_registrations())

    return kernel


# No Selection Strategy is registered on purpose: `ByIdsSelectionStrategy`
# takes its identifiers in its constructor, so
# `aistack.selection.workflow` builds one per selection. The registry
# itself stays (ADR-0003) and is empty after bootstrap.


def registered_providers(providers: ProviderRegistry | None = None) -> ProviderRegistry:
    """
    The providers a chain reads through: the ones given, or those of a
    Kernel booted for the occasion (ADR-0027 § 9).

    A chain that reads several times boots one Kernel and hands its
    providers on; a function called alone boots its own.
    """

    return providers if providers is not None else create_kernel().registries.providers

from __future__ import annotations

from aistack.kernel.bootstrap.catalog_views import (
    register_default_catalog_views,
)
from aistack.kernel.bootstrap.providers import (
    register_default_providers,
)
from aistack.kernel.bootstrap.selection import (
    register_default_selection_strategies,
)
from aistack.kernel.context import Kernel
from aistack.kernel.registries import KernelRegistries
from aistack.kernel.registries.catalog_view_registry import CatalogViewRegistry
from aistack.kernel.registries.provider_registry import ProviderRegistry
from aistack.kernel.registries.selection_strategy_registry import (
    SelectionStrategyRegistry,
)
from aistack.kernel.services import KernelServices
from aistack.transport.default_transport_engine import (
    DefaultTransportEngine,
)
from aistack.transport.delivery_verifier import DeliveryVerifier
from aistack.transport.registry.in_memory_transport_registry import (
    InMemoryTransportRegistry,
)


def create_kernel() -> Kernel:
    """
    Compose and initialize the default AIStack Kernel.

    This function is the runtime Composition Root. It is the only place
    responsible for constructing the default Kernel dependency graph.
    """

    registries = KernelRegistries(
        providers=ProviderRegistry(),
        catalog_views=CatalogViewRegistry(),
        selection_strategies=SelectionStrategyRegistry(),
    )

    transport_registry = InMemoryTransportRegistry()
    delivery_verifier = DeliveryVerifier()

    transport = DefaultTransportEngine(
        registry=transport_registry,
        delivery_verifier=delivery_verifier,
    )

    services = KernelServices(
        transport_registry=transport_registry,
        delivery_verifier=delivery_verifier,
        transport=transport,
    )

    kernel = Kernel(
        registries=registries,
        services=services,
    )

    register_default_providers(kernel)
    register_default_catalog_views(kernel)
    register_default_selection_strategies(kernel)

    return kernel

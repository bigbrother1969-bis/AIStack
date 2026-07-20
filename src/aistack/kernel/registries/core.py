from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.registries.catalog_view_registry import CatalogViewRegistry
from aistack.kernel.registries.provider_registry import ProviderRegistry
from aistack.kernel.registries.selection_strategy_registry import (
    SelectionStrategyRegistry,
)


@dataclass
class KernelRegistries:
    """Root container for Kernel registries."""

    providers: ProviderRegistry = field(default_factory=ProviderRegistry)
    catalog_views: CatalogViewRegistry = field(default_factory=CatalogViewRegistry)
    selection_strategies: SelectionStrategyRegistry = field(
        default_factory=SelectionStrategyRegistry
    )

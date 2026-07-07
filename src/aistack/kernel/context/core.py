from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.registries import CatalogViewRegistry, SelectionStrategyRegistry


@dataclass
class KernelContext:
    """Root context aggregating Kernel registries."""

    catalog_views: CatalogViewRegistry = field(default_factory=CatalogViewRegistry)
    selection_strategies: SelectionStrategyRegistry = field(default_factory=SelectionStrategyRegistry)

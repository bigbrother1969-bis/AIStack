from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.registries.catalog_view_registry import CatalogViewRegistry
from aistack.kernel.registries.provider_registry import ProviderRegistry
from aistack.kernel.registries.selection_strategy_registry import (
    SelectionStrategyRegistry,
)
from aistack.kernel.registries.task_registry import TaskRegistry


@dataclass(frozen=True, slots=True)
class KernelRegistries:
    """
    Immutable aggregate of Kernel registries.

    The aggregate structure is immutable. The registries it exposes retain
    responsibility for registering and resolving their domain components.
    """

    providers: ProviderRegistry
    catalog_views: CatalogViewRegistry
    selection_strategies: SelectionStrategyRegistry
    tasks: TaskRegistry

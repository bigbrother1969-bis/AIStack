from __future__ import annotations

from aistack.kernel.registry import Registry
from aistack.selection.strategies import SelectionStrategy


class SelectionStrategyRegistry(Registry[SelectionStrategy]):
    """Registry of Selection Strategies."""

    pass

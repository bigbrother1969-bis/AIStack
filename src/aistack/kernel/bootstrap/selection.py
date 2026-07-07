from __future__ import annotations

from aistack.kernel.context import KernelContext
from aistack.kernel.selection.strategies import ByIdsSelectionStrategy


def register_default_selection_strategies(ctx: KernelContext) -> None:
    """Register default Selection Strategies into the Kernel Context."""

    ctx.selection_strategies.register("by-ids", ByIdsSelectionStrategy([]))

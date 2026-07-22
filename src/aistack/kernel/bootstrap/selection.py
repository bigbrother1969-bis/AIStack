from __future__ import annotations

from aistack.kernel import Kernel
from aistack.kernel.selection.strategies import ByIdsSelectionStrategy


def register_default_selection_strategies(kernel: Kernel) -> None:
    """Register default Selection Strategies into the Kernel."""

    kernel.registries.selection_strategies.register(
        "by-ids",
        ByIdsSelectionStrategy([]),
    )

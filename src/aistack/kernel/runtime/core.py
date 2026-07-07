from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.bootstrap import create_kernel_context
from aistack.kernel.context import KernelContext


@dataclass
class KernelRuntime:
    """Runtime entry point for the AIStack Knowledge Operating System Kernel."""

    context: KernelContext

    @classmethod
    def boot(cls) -> "KernelRuntime":
        """Boot the Kernel Runtime using the default Kernel Bootstrap."""

        return cls(context=create_kernel_context())

    def provider_ids(self) -> list[str]:
        """Return registered Knowledge Provider identifiers."""

        return sorted(self.context.providers.all().keys())

    def catalog_view_ids(self) -> list[str]:
        """Return registered Catalog View identifiers."""

        return sorted(self.context.catalog_views.all().keys())

    def selection_strategy_ids(self) -> list[str]:
        """Return registered Selection Strategy identifiers."""

        return sorted(self.context.selection_strategies.all().keys())

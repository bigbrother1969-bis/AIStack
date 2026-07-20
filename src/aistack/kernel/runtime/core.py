from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.bootstrap import create_kernel
from aistack.kernel.context import Kernel
from aistack.kernel.runtime.state import RuntimeState
from aistack.transport import DefaultTransportEngine


@dataclass
class KernelRuntime:
    """Runtime entry point for the AIStack Knowledge Operating System Kernel."""

    kernel: Kernel
    state: RuntimeState = RuntimeState.READY

    @classmethod
    def boot(cls) -> "KernelRuntime":
        """Boot the Kernel Runtime using the default Kernel Bootstrap."""

        return cls(
            kernel=create_kernel(),
            state=RuntimeState.READY,
        )

    @property
    def transport(self) -> DefaultTransportEngine:
        """Return the Kernel Transport Engine."""

        return self.kernel.services.transport

    def provider_ids(self) -> list[str]:
        """Return registered Knowledge Provider identifiers."""

        return sorted(self.kernel.registries.providers.all().keys())

    def catalog_view_ids(self) -> list[str]:
        """Return registered Catalog View identifiers."""

        return sorted(self.kernel.registries.catalog_views.all().keys())

    def selection_strategy_ids(self) -> list[str]:
        """Return registered Selection Strategy identifiers."""

        return sorted(
            self.kernel.registries.selection_strategies.all().keys()
        )

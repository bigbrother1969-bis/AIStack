from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.bootstrap import create_kernel
from aistack.kernel.context import Kernel
from aistack.kernel.runtime.state import RuntimeState
from aistack.transport import DefaultTransportEngine


@dataclass
class KernelRuntime:
    """
    Runtime entry point for the AIStack Knowledge Operating System.

    The Runtime supervises the execution of the Kernel.

    Registries, Providers and other Kernel components remain accessible
    through the Kernel itself and are not exposed by dedicated Runtime APIs.
    """

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

from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel import Kernel
from aistack.kernel.bootstrap import create_kernel
from aistack.kernel.execution import (
    Request,
    RuntimeExecutionContext,
)
from aistack.kernel.resolution import TaskResolver
from aistack.kernel.runtime.execution import RuntimeExecutor
from aistack.kernel.runtime.state import RuntimeState
from aistack.kernel.tracing import ExecutionTrace
from aistack.transport import DefaultTransportEngine


@dataclass
class KernelRuntime:
    """
    Runtime entry point for the AIStack Knowledge Operating System.

    The Runtime accepts Requests, resolves their Tasks, executes those Tasks,
    and returns the resulting Execution Trace.

    It never resolves or invokes Providers, Capabilities, or Actions directly.
    """

    kernel: Kernel
    resolver: TaskResolver
    executor: RuntimeExecutor
    state: RuntimeState = RuntimeState.READY

    @classmethod
    def boot(cls) -> "KernelRuntime":
        """Boot the Runtime through the default Kernel Composition Root."""

        kernel = create_kernel()
        resolver = TaskResolver(tasks=kernel.registries.tasks)
        executor = RuntimeExecutor(resolver=resolver)

        return cls(
            kernel=kernel,
            resolver=resolver,
            executor=executor,
            state=RuntimeState.READY,
        )

    def execute(self, request: Request) -> ExecutionTrace:
        """Execute one Request and return its execution trace."""

        if self.state is not RuntimeState.READY:
            raise RuntimeError(
                f"Runtime is not ready: {self.state.value}"
            )


        context = RuntimeExecutionContext(
            request=request,
        )

        return self.executor.execute(context)

        

    @property
    def transport(self) -> DefaultTransportEngine:
        """Return the Kernel Transport Engine."""

        return self.kernel.services.transport

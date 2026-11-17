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
from aistack.kernel.tracing import (
    ExecutionTrace,
    InMemoryTraceRepository,
    TraceRepository,
)
from aistack.transport import DefaultTransportEngine


@dataclass
class KernelRuntime:
    """
    Runtime entry point for AIStack.

    The Runtime orchestrates:
    - request execution;
    - trace production;
    - trace persistence.
    """

    kernel: Kernel
    resolver: TaskResolver
    executor: RuntimeExecutor
    trace_repository: TraceRepository
    state: RuntimeState = RuntimeState.READY

    @classmethod
    def boot(
        cls,
        trace_repository: TraceRepository | None = None,
    ) -> "KernelRuntime":
        """
        Boot the Runtime through the default Kernel Composition Root.

        **`trace_repository` defaults to in-memory, never to durable
        storage.** A caller that wants Runtime Operation History
        passes a `FileTraceRepository` explicitly, as
        `aistack.cli.health_render` does: defaulting `.boot()` itself
        to writing files would make every test that boots the Runtime
        write into this repository's own `reports/generated/`.
        `tests/unit/kernel/test_architecture_boundaries.py` checks that
        every command that boots the Runtime says which one it wants.
        """

        kernel = create_kernel()

        resolver = TaskResolver(
            tasks=kernel.registries.tasks,
        )

        executor = RuntimeExecutor(
            resolver=resolver,
        )

        trace_repository = trace_repository or InMemoryTraceRepository()

        return cls(
            kernel=kernel,
            resolver=resolver,
            executor=executor,
            trace_repository=trace_repository,
            state=RuntimeState.READY,
        )

    def execute(
        self,
        request: Request,
    ) -> ExecutionTrace:
        """
        Execute one Request and persist its execution trace.
        """

        if self.state is not RuntimeState.READY:
            raise RuntimeError(
                f"Runtime is not ready: {self.state.value}"
            )

        context = RuntimeExecutionContext(
            request=request,
        )
        trace = self.executor.execute(
            context,
        )

        self.trace_repository.save(
            trace,
        )

        return trace

    @property
    def transport(self) -> DefaultTransportEngine:
        """
        Return the Kernel Transport Engine.
        """

        return self.kernel.services.transport

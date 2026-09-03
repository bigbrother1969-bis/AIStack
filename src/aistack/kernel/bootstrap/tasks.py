from __future__ import annotations

from aistack.kernel import Kernel
from aistack.kernel.tasks import DockerDiscoverTask


def register_default_tasks(kernel: Kernel) -> None:
    """
    Register default Tasks into the Kernel.

    **The first call this function ever makes.** Until 2026-09-03
    `create_kernel()` built an empty `TaskRegistry` and nothing
    populated it — GOV-0002/OS-041 measured that as *"tasks
    registered → 0"* and resolved the Execution Dimension unearned
    on exactly that absence. `docker.discover` is the first
    registration, built from the provider `register_default_providers`
    already registered — so this must run after it, the same
    ordering `create_kernel()` already gives catalog views relative
    to providers.
    """

    kernel.registries.tasks.register(
        DockerDiscoverTask.task_id,
        DockerDiscoverTask(kernel.registries.providers.get("docker")),
    )

from __future__ import annotations

from aistack.kernel import Kernel
from aistack.kernel.tasks import DockerDiscoverTask


def register_default_tasks(kernel: Kernel) -> None:
    """
    Register default Tasks into the Kernel.

    Must run after `register_default_providers`: `docker.discover` is
    built from the registered `docker` provider.
    """

    kernel.registries.tasks.register(
        DockerDiscoverTask.task_id,
        DockerDiscoverTask(kernel.registries.providers.get("docker")),
    )

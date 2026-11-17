"""
The tasks `create_kernel()` registers — GOV-0002/OS-041 measured it
registering none. They are declared in `registrations.yml` since
ADR-0027 § 8; these tests read the Kernel, not the file.
"""

from __future__ import annotations

from aistack.kernel.bootstrap import create_kernel
from aistack.tasks import (
    ArchitectureRenderTask,
    ConsoleRenderTask,
    HealthRenderTask,
    NetworkDockerDiscoverTask,
    TimeMachineRebuildTask,
)


def test_create_kernel_registers_the_health_render_task():
    kernel = create_kernel()

    task = kernel.registries.tasks.get("health.render")

    assert isinstance(task, HealthRenderTask)


def test_create_kernel_registers_the_architecture_render_task():
    kernel = create_kernel()

    task = kernel.registries.tasks.get("architecture.render")

    assert isinstance(task, ArchitectureRenderTask)
    assert task._providers is kernel.registries.providers


def test_create_kernel_registers_the_console_render_task():
    kernel = create_kernel()

    task = kernel.registries.tasks.get("console.render")

    assert isinstance(task, ConsoleRenderTask)
    assert task._providers is kernel.registries.providers


def test_create_kernel_registers_the_time_machine_rebuild_task():
    kernel = create_kernel()

    task = kernel.registries.tasks.get("timemachine.rebuild")

    assert isinstance(task, TimeMachineRebuildTask)


def test_create_kernel_registers_the_network_docker_discover_task():
    kernel = create_kernel()

    task = kernel.registries.tasks.get("network_docker.discover")

    assert isinstance(task, NetworkDockerDiscoverTask)


def test_the_health_task_reads_through_the_providers_of_its_own_kernel():
    """
    Not a second `ProviderRegistry`, nor a Kernel booted for the
    occasion: the registry this Kernel registered, so a provider
    stubbed for a test is the one the chain actually reads.
    """

    kernel = create_kernel()

    task = kernel.registries.tasks.get("health.render")

    assert task._providers is kernel.registries.providers


def test_only_the_tasks_declared_here_are_registered():
    """
    Kernel Runtime tracing invariant (audited 2026-09-23): a Task
    registered here is executed by a command that boots the Runtime
    with a durable trace repository
    (`tests/unit/kernel/test_architecture_boundaries.py`). A second
    Task registered without this assertion also being touched fails
    here, at the moment a new chain could first go untraced, not at
    the next audit. `docker.discover` was removed on 2026-11-17
    (ADR-0027 § 10): nothing executed it.
    """

    kernel = create_kernel()

    assert set(kernel.registries.tasks.all()) == {
        "health.render",
        "architecture.render",
        "console.render",
        "timemachine.rebuild",
        "network_docker.discover",
    }

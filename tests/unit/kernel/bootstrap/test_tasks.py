"""
`register_default_tasks` — GOV-0002/OS-041 measured
`create_kernel()` registering zero tasks; this is the function that
changes that, and its own test.
"""

from __future__ import annotations

from aistack.kernel.bootstrap import create_kernel
from aistack.kernel.tasks import DockerDiscoverTask


def test_create_kernel_registers_the_docker_discover_task():
    kernel = create_kernel()

    task = kernel.registries.tasks.get("docker.discover")

    assert isinstance(task, DockerDiscoverTask)


def test_the_registered_task_wraps_the_registered_docker_provider():
    """
    Not a second, independent `DockerProvider()` — the same
    instance `register_default_providers` already registered, so a
    provider stubbed for a test (as
    `tests/unit/cli/test_the_provider_commands_run.py` does) is the
    one this task actually calls.
    """

    kernel = create_kernel()

    provider = kernel.registries.providers.get("docker")
    task = kernel.registries.tasks.get("docker.discover")

    assert task._provider is provider


def test_only_the_tasks_declared_here_are_registered():
    """
    Kernel Runtime tracing invariant, audited 2026-09-23
    (`claude/AUDIT-KERNEL-RUNTIME-CALLERS-2026-09-23.md`) —
    `KernelRuntime.boot()` defaults `trace_repository` to
    `InMemoryTraceRepository()` for every caller that does not ask
    for `FileTraceRepository` explicitly
    (`tests/unit/kernel/runtime/test_runtime.py::
    test_boot_defaults_to_an_in_memory_trace_repository`). That
    default has zero real exposure today only because
    `docker.discover` is the sole registered Task — this test names
    that fact so a second Task registered here, without this
    assertion also being touched, fails immediately, at the moment a
    new caller could first go untraced, not at the next audit.
    """

    kernel = create_kernel()

    assert set(kernel.registries.tasks.all()) == {"docker.discover"}

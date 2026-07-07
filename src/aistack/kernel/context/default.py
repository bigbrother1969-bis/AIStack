from __future__ import annotations

from aistack.kernel.context import KernelContext
from aistack.providers.docker import DockerProvider


def create_kernel_context() -> KernelContext:
    """Create the default AIStack Kernel context."""

    ctx = KernelContext()
    ctx.providers.register("docker", DockerProvider())
    return ctx

from __future__ import annotations

from aistack.kernel.context import KernelContext
from aistack.providers.docker import DockerProvider


def register_default_providers(ctx: KernelContext) -> None:
    """Register default Knowledge Providers into the Kernel Context."""

    ctx.providers.register("docker", DockerProvider())

from __future__ import annotations

from aistack.kernel import Kernel
from aistack.providers.compose import ComposeProvider
from aistack.providers.docker import DockerProvider


def register_default_providers(kernel: Kernel) -> None:
    """Register default Knowledge Providers into the Kernel."""

    kernel.registries.providers.register("docker", DockerProvider())
    kernel.registries.providers.register("compose", ComposeProvider())

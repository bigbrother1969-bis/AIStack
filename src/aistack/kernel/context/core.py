from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.registries import KernelRegistries
from aistack.kernel.services import KernelServices


@dataclass
class KernelContext:
    """Root context aggregating Kernel registries and services."""

    registries: KernelRegistries = field(default_factory=KernelRegistries)
    services: KernelServices = field(default_factory=KernelServices)

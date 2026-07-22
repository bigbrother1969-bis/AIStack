from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.registries import KernelRegistries
from aistack.kernel.services import KernelServices


@dataclass(frozen=True, slots=True)
class Kernel:
    """
    Immutable representation of a fully composed AIStack runtime.

    The Kernel does not construct dependencies.
    Runtime composition is exclusively performed by the bootstrap.
    """

    registries: KernelRegistries
    services: KernelServices

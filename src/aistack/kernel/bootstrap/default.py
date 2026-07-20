from __future__ import annotations

from aistack.kernel.bootstrap.catalog_views import register_default_catalog_views
from aistack.kernel.bootstrap.providers import register_default_providers
from aistack.kernel.bootstrap.selection import (
    register_default_selection_strategies,
)
from aistack.kernel.context import Kernel


def create_kernel() -> Kernel:
    kernel = Kernel()

    register_default_providers(kernel)
    register_default_catalog_views(kernel)
    register_default_selection_strategies(kernel)

    return kernel

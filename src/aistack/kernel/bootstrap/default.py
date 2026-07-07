from __future__ import annotations

from aistack.kernel.bootstrap.catalog_views import register_default_catalog_views
from aistack.kernel.bootstrap.providers import register_default_providers
from aistack.kernel.bootstrap.selection import register_default_selection_strategies
from aistack.kernel.context.core import KernelContext


def create_kernel_context() -> KernelContext:
    """Create the default AIStack Kernel context."""

    ctx = KernelContext()
    register_default_providers(ctx)
    register_default_catalog_views(ctx)
    register_default_selection_strategies(ctx)
    return ctx

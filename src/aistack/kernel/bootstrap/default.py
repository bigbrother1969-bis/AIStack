from __future__ import annotations

from aistack.kernel.bootstrap.providers import register_default_providers
from aistack.kernel.context.core import KernelContext


def create_kernel_context() -> KernelContext:
    """Create the default AIStack Kernel context."""

    ctx = KernelContext()
    register_default_providers(ctx)
    return ctx

from __future__ import annotations

from dataclasses import dataclass, field

from aistack.transport import DefaultTransportEngine


@dataclass
class KernelServices:
    """Root container for Kernel services."""

    transport: DefaultTransportEngine = field(default_factory=DefaultTransportEngine)

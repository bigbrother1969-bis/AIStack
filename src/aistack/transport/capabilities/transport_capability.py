"""
Knowledge Transport Layer - Transport Capability contract.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.interfaces.receiver import Receiver
from aistack.transport.interfaces.writer import Writer


class TransportCapability(Protocol):
    """
    Groups all technology-specific transport primitives.
    """

    @property
    def receiver(self) -> Receiver:
        ...

    @property
    def writer(self) -> Writer:
        ...

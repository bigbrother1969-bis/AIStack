from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from aistack.kernel.contracts.base_provider import Provider


class DiscoveryProvider(Provider, Protocol):
    """
    Discover information made available by an external source.

    Discovery Providers support AIStack Self Discovery.
    They do not prescribe the nature, value, relationships, or future uses
    of discovered information.
    """

    def discover(self) -> Iterable[Any]:
        ...

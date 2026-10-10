from __future__ import annotations

from typing import Any, Protocol

from aistack.kernel.contracts.base_provider import Provider


class KnowledgeProvider(Provider, Protocol):
    """
    Make observations from an external source available to AIStack.

    A provider only collects evidence and never interprets it; `collect`
    is its single method.
    """

    def collect(self) -> dict[str, Any]:
        ...

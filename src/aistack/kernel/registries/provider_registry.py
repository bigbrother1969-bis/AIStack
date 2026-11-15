from __future__ import annotations

from typing import TypeVar, cast

from aistack.kernel.contracts.base_provider import Provider
from aistack.kernel.contracts.provider import KnowledgeProvider
from aistack.kernel.registry import Registry

P = TypeVar("P")


class ProviderRegistry(Registry[Provider]):
    """
    Registry of Providers (ADR-0027 § 9).

    It holds what every provider is: an identity, and no prescribed way
    of obtaining information. A provider that `collect()`s is a
    `KnowledgeProvider`; one that exposes specialised readings is asked
    for by the class that declares them.
    """

    def collecting(self, identifier: str) -> KnowledgeProvider:
        """
        The registered provider, as one that `collect()`s.

        Raises a TypeError naming the provider when it does not: the
        contract is checked here, where it is relied on.
        """

        entry = self.get(identifier)

        if not callable(getattr(entry, "collect", None)):
            raise TypeError(
                f"Provider {identifier!r} is registered and does not collect(): "
                f"it is not a KnowledgeProvider"
            )

        return cast(KnowledgeProvider, entry)

    def get_as(self, identifier: str, expected: type[P]) -> P:
        """
        The registered provider, as the class whose readings the caller
        uses.

        `expected` is the caller's statement of what it asks for: the
        type checker holds the caller to it. It is not verified here —
        what is registered under an identifier is declared in
        `registrations.yml`, and a provider standing in for another one
        need not inherit from it.
        """

        return cast(P, self.get(identifier))

from __future__ import annotations

from typing import Any, Protocol

from aistack.kernel.contracts.base_provider import Provider


class KnowledgeProvider(Provider, Protocol):
    """
    Make observations from an external source available to AIStack.

    FDN-0002 defines a Knowledge Provider as *responsible for
    discovering observations from a Digital Ecosystem*, which
    *never interpret observations* and *only collect evidence*.
    One activity, and `collect` is it.

    **This protocol declared a second method until 2026-08-27.**
    It extended a `DiscoveryProvider` requiring `discover()`, and
    described itself as *backward-compatible*: `collect` was the
    legacy, `discover` the destination of a Runtime migration.

    That migration was measured on 2026-08-27 and abandoned by the
    owner. Six call sites used `collect`, none used `discover`,
    and `aistack.cli.docker_discover` — the command named after
    the model — called `collect` too. Five weeks after the
    contract was shaped for the destination, nothing had moved
    toward it. ARC-P-006 says an abstraction is earned; this one
    was named and never was. GOV-0002/OS-034.

    The word survives where it describes the activity — the
    glossary's definition, the command name. What is retired is
    the second *method*.
    """

    def collect(self) -> dict[str, Any]:
        ...

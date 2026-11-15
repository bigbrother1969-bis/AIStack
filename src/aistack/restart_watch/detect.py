from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from aistack.restart_watch.facts import ContainerFacts

UNHEALTHY = "unhealthy"
STALE_NETWORK = "stale_network"
PROBE_FAILED = "probe_failed"

# A provider that started within this many seconds of its dependent is the
# same boot, not a restart after it.
STALE_MARGIN_SECONDS = 2.0

# The watch never restarts itself: it would end the very process acting.
ALWAYS_LEFT_ALONE = frozenset({"aistack-restart-watch"})


@dataclass(frozen=True)
class Stuck:
    """A running container judged stuck, and why (one or more reasons)."""

    name: str
    reasons: tuple[str, ...]


def find_stuck(
    facts: Sequence[ContainerFacts],
    failed_probes: Collection[str] = (),
    never: Collection[str] = (),
) -> tuple[Stuck, ...]:
    """
    The running containers that are stuck, by three signs (ADR-0025 § 2).

    - `unhealthy`: its own healthcheck says so. Docker only says it after
      the start period, so a container still starting is never named.
    - `stale_network`: it shares another container's network and that
      provider was started *after* it — it holds a namespace that no
      longer exists, and nothing in its own state shows it.
    - `probe_failed`: the owner declared a probe for it (it has no
      healthcheck) and the probe got no answer.

    A stopped container is never named: stopping it may be the owner's
    wish, and the restart policy already covers a crash.
    """

    by_name = {item.name: item for item in facts}
    skipped = set(never) | ALWAYS_LEFT_ALONE
    stuck: list[Stuck] = []

    for item in facts:
        if item.name in skipped or not item.running:
            continue

        reasons: list[str] = []

        if item.health == "unhealthy":
            reasons.append(UNHEALTHY)

        provider = by_name.get(item.network_provider or "")

        if (
            provider is not None
            and provider.running
            and provider.started_at is not None
            and item.started_at is not None
            and (provider.started_at - item.started_at).total_seconds() > STALE_MARGIN_SECONDS
        ):
            reasons.append(STALE_NETWORK)

        if item.name in failed_probes and not item.has_healthcheck:
            reasons.append(PROBE_FAILED)

        if reasons:
            stuck.append(Stuck(item.name, tuple(reasons)))

    return tuple(sorted(stuck, key=lambda item: item.name))

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from aistack.restart_watch.detect import ALWAYS_LEFT_ALONE
from aistack.restart_watch.facts import ContainerFacts


@dataclass(frozen=True)
class Plan:
    """
    The containers to restart, in order, and what was added to the list.

    `dragged` are containers that were not stuck themselves but share the
    network of one that is restarted: its namespace is replaced, so theirs
    would be stale next. `cycle` is True when the declared order loops and
    the remainder was ordered by name.
    """

    order: tuple[str, ...]
    dragged: tuple[str, ...] = ()
    cycle: bool = False


def plan_restart(
    stuck: Collection[str],
    facts: Sequence[ContainerFacts],
    after: Mapping[str, Sequence[str]] | None = None,
    never: Collection[str] = (),
) -> Plan:
    """
    Order the restart of `stuck`: a provider before whoever depends on it.

    An edge `A -> B` (A first) comes from `B` sharing `A`'s network, from
    `B`'s Compose `depends_on` on `A`, or from the owner's `after`
    exceptions. Restarting a network provider drags in every running
    container sharing its network. Ties break by name, so the same
    situation always gives the same order.
    """

    by_name = {item.name: item for item in facts}
    skipped = set(never) | ALWAYS_LEFT_ALONE
    chosen = {name for name in stuck if name in by_name and name not in skipped}
    dragged: set[str] = set()
    grew = True

    while grew:
        grew = False

        for item in facts:
            if (
                item.running
                and item.name not in chosen
                and item.name not in skipped
                and item.network_provider in chosen
            ):
                chosen.add(item.name)
                dragged.add(item.name)
                grew = True

    first_of: dict[str, set[str]] = {name: set() for name in chosen}

    for name in chosen:
        item = by_name[name]
        wanted = set(item.depends_on)

        if item.network_provider:
            wanted.add(item.network_provider)

        wanted.update((after or {}).get(name, ()))
        first_of[name] = {other for other in wanted if other in chosen and other != name}

    order: list[str] = []
    waiting = dict(first_of)

    while waiting:
        ready = sorted(name for name, needs in waiting.items() if not needs)

        if not ready:
            order.extend(sorted(waiting))

            return Plan(tuple(order), tuple(sorted(dragged)), cycle=True)

        order.extend(ready)

        for name in ready:
            del waiting[name]

        for needs in waiting.values():
            needs.difference_update(ready)

    return Plan(tuple(order), tuple(sorted(dragged)))

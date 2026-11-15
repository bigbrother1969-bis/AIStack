"""What is new, from what was seen before and what is seen now. No disk, no clock, no Docker."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from aistack.arrivals.definition import ArrivalsDefinition

CONTAINER = "container"
HOST = "host"
# What is kept about a container to recognize it (`aistack.arrivals.facts`).
FACTS = ("image", "ports", "gpu")

# The health cockpit's inventory domain and the messages it gives a
# container no service declares (`aistack.runtime.evaluate_inventory_gap`).
INVENTORY_DOMAIN = "Écarts d'inventaire"
UNDECLARED_KEYS = (
    "findings.inventory_gap.undeclared_here.interpretation",
    "findings.inventory_gap.undeclared_on_host.interpretation",
)


@dataclass(frozen=True)
class Arrival:
    """`name` is the container's name, or the machine's address."""

    kind: str
    name: str
    where: str | None = None


def observed_containers(snapshot: Any) -> dict[str, str | None] | None:
    """
    The containers running that no service declares, with the machine each
    is on (`None`: this one), from the last health snapshot; `None` when
    there is no snapshot, so the pass changes nothing.
    """

    if snapshot is None:
        return None

    found: dict[str, str | None] = {}

    for finding in snapshot.findings:
        if finding.domain != INVENTORY_DOMAIN or not finding.message:
            continue

        key, params = finding.message[0]

        if key in UNDECLARED_KEYS:
            found[finding.subject] = dict(params).get("host")

    return found


def update_containers(
    state: Mapping[str, Any],
    observed: Mapping[str, str | None],
    facts: Mapping[str, Mapping[str, Any]],
    definition: ArrivalsDefinition,
    ignored: Collection[str],
    now: str,
) -> tuple[dict[str, Any], list[Arrival]]:
    """
    The `containers` of the next state, and the arrivals to say.

    The first pass of a fresh state only notes what is there. After it, a
    container is said once, on its `confirm_passes`-th pass in a row; one
    that disappears is forgotten, so it is said again if it comes back.
    """

    before: Mapping[str, Any] = state.get("containers") or {}
    first = not state.get("baseline")
    kept: dict[str, Any] = {}
    arrivals: list[Arrival] = []

    for name in sorted(observed):
        if name in definition.ignore or name in ignored:
            continue

        previous = before.get(name) or {}
        entry: dict[str, Any] = {
            "host": observed[name],
            "seen": int(previous.get("seen", 0)) + 1,
            "since": previous.get("since", now),
            "announced": bool(previous.get("announced", False)),
            **{key: previous[key] for key in FACTS if key in previous},
            **{key: value for key, value in (facts.get(name) or {}).items() if value not in (None, "")},
        }

        if not entry["announced"] and (first or entry["seen"] >= definition.confirm_passes):
            entry["announced"] = True

            if not first:
                arrivals.append(Arrival(CONTAINER, name, observed[name]))

        kept[name] = entry

    return kept, arrivals


def update_hosts(
    state: Mapping[str, Any],
    observation: Mapping[str, Any],
    traced: Collection[str],
    definition: ArrivalsDefinition,
    decided: Collection[str],
    now: str,
) -> tuple[dict[str, Any], list[str], list[Arrival]]:
    """
    The `hosts` waiting, the `known_hosts` to remember, and the arrivals to say.

    A machine is known when `hosts.yml` gives its address, `arrivals.yml`
    lists it, the owner marked it, or it was there when the first
    observation that held any machine was read (only that last kind is
    remembered: the others are read again at every pass). An observation with no
    machine proves nothing (the scan may have failed), so it sets no baseline.
    """

    found = [
        entry
        for entry in (observation.get("network_docker") or {}).get("hosts") or []
        if isinstance(entry, dict) and entry.get("host")
    ]
    remembered = set(state.get("known_hosts") or [])
    waiting: dict[str, Any] = {}
    arrivals: list[Arrival] = []
    before: Mapping[str, Any] = state.get("hosts") or {}

    if found and not state.get("hosts_baseline"):
        remembered |= {str(entry["host"]) for entry in found}

    known = remembered | set(traced) | set(definition.known_hosts) | set(decided)

    for entry in found:
        address = str(entry["host"])

        if address in known:
            continue

        previous = before.get(address) or {}
        announced = bool(previous.get("announced", False))
        waiting[address] = {
            "user": entry.get("ssh_username"),
            "containers": len(entry.get("containers") or []),
            "since": previous.get("since", now),
            "announced": True,
        }

        if not announced:
            arrivals.append(Arrival(HOST, address, entry.get("ssh_username")))

    return waiting, sorted(remembered), arrivals

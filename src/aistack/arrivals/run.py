"""One pass of the vigil over arrivals: read, compare with the last pass, remember, say what is new."""

from __future__ import annotations

from collections.abc import Callable, Collection
from datetime import datetime
from pathlib import Path
from typing import Any

from aistack.arrivals import state as store
from aistack.arrivals.definition import ArrivalsDefinition
from aistack.arrivals.detect import Arrival, observed_containers, update_containers, update_hosts
from aistack.arrivals.facts import local_facts, remote_facts

LocalFacts = Callable[[Collection[str]], dict[str, dict[str, Any]]]


def due(last_scan: object, now: datetime, hours: float) -> bool:
    """Whether a scan is due: switched on, and never done or done `hours` ago."""

    if hours <= 0:
        return False

    try:
        last = datetime.fromisoformat(str(last_scan))
    except ValueError:
        return True

    return (now - last).total_seconds() >= hours * 3600


def run(
    generated: Path,
    definition: ArrivalsDefinition,
    snapshot: Any,
    traced: Collection[str],
    *,
    now: datetime,
    scan: Callable[[], None] | None = None,
    facts: LocalFacts = local_facts,
) -> tuple[list[Arrival], dict[str, Any]]:
    """
    The arrivals to say at this pass, and the state to `remember` once they
    were said (a message Gotify refused is tried again at the next pass).

    `snapshot` is the last health snapshot (`aistack.vigil.snapshot.read`),
    `None` when there is none: containers are then left as they were.
    `scan` runs the network discovery; it is called only when
    `machine_scan_hours` says one is due.
    """

    state = store.read_state(generated)
    decisions = store.read_decisions(generated)
    stamp = now.isoformat(timespec="seconds")
    following = dict(state)
    arrivals: list[Arrival] = []

    if scan is not None and due(state.get("last_scan"), now, definition.machine_scan_hours):
        scan()
        following["last_scan"] = stamp

    observation = store.read_observation(generated)
    waiting, known, machines = update_hosts(state, observation, traced, definition, decisions["known_hosts"], stamp)
    following.update(hosts=waiting, known_hosts=known)

    if (observation.get("network_docker") or {}).get("hosts"):
        following["hosts_baseline"] = True

    arrivals += machines

    observed = observed_containers(snapshot)

    if observed is not None:
        before = state.get("containers") or {}
        unknown = {name: host for name, host in observed.items() if not (before.get(name) or {}).get("image")}
        found = {**remote_facts(observation, unknown), **facts([n for n, host in unknown.items() if host is None])}
        kept, containers = update_containers(state, observed, found, definition, decisions["ignored_containers"], stamp)
        following.update(containers=kept, baseline=True)
        arrivals += containers

    following["updated_at"] = stamp

    return arrivals, following


def remember(generated: Path, following: dict[str, Any]) -> None:
    store.write_state(generated, following)

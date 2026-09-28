from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Mapping

from aistack.providers.docker.identity import stable_subject_from_labels


# 1.5, Traçabilité passive des conteneurs (`claude/ROADMAP-1.2-TO-2.0-
# 2026-09-27.md` § 1.5). Cadrage 2026-09-28: the owner chose `docker
# events` as 1.5's first collector — it is the source the upgrade
# events § 1.5 itself asks for (exec, pull, create, recreate, destroy)
# come from — and chose a governed polling loop over a continuous
# subscription, the same shape `aistack.cli
# .resource_priority_monitor` already established as this heritage's
# one precedent for a long-running collector (`ADR-0011` § *Decision*
# 1's "point-in-time snapshot" contract every other provider's
# `collect()` already follows, extended here to a bounded time window
# instead of "right now" alone).
#
# `ARC-P-012`'s boundary (`DockerProvider.collect_logs`'s own
# docstring: "this returns lines, never a verdict") holds here too:
# this module returns what Docker itself reported, and derives only
# the three facts `ADR-0011` § 3-4 already named as needing derivation
# at collection time (`aistack:stableSubject`, `aistack:occurredAt`,
# the action taken) — never an interpretation such as "this was an
# upgrade". Correlating a `destroy`+`create` pair into a richer
# "upgrade" fact is a later, separate concern (`ADR-0011` § *Open
# Points*), not something this raw collector decides on its own.


def collect_docker_events(since: str, until: str) -> list[dict[str, Any]]:
    """
    Every Docker event in `[since, until)`, raw, as Docker itself
    reports it — one bounded call, the same "point-in-time snapshot"
    shape `DockerProvider.collect()` already holds, just parametrised
    by a window instead of "right now" alone: a governed polling loop
    calls this once per cycle with `since` set to its own last
    checkpoint, never leaving a process attached to a live subscription
    (`aistack.cli.docker_events_monitor`, the cadrage decision above).

    `--since`/`--until` accept anything Docker's own reference parses
    (`"2026-09-28T10:00:00Z"`, a Unix timestamp); this module states no
    format of its own, so the caller and Docker agree on the same one
    without a translation layer here that could drift from it.

    Returns `[]` on any failure — no daemon, no such command, malformed
    output — the same convention `NvidiaGpuProvider.collect_readings`
    and `DockerProvider.collect_cpu_readings` already hold: what could
    not be observed is reported as nothing observed, never raised, so
    one bad cycle does not crash a monitor meant to run for days.
    """

    try:
        result = subprocess.run(
            [
                "docker",
                "events",
                "--since",
                since,
                "--until",
                until,
                "--format",
                "{{json .}}",
            ],
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    events: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)

    return events


def stable_subject_of(event: Mapping[str, Any]) -> str:
    """
    `ADR-0011` § *Decision* 3's identity rule, applied to one raw
    Docker event: the Compose project and service name when the
    event's own actor carries both (`compose_project/service` —
    Compose writes these as the `com.docker.compose.project`/
    `com.docker.compose.service` labels on every container it
    manages, the same two labels `NetworkDockerDiscoveryProvider`
    already reads for the same reason), falling back to the actor's
    plain name, and, when Docker names neither, its own id — never
    empty, since a real Docker event always carries at least
    `Actor.ID`.

    Deliberately not the container's own Docker id as a first choice:
    § 3 fixes this exactly to avoid it — "recreation always changes
    it and identity by definition must not."

    **A thin adapter, since 2026-09-28.** The identity rule itself
    moved to `aistack.providers.docker.identity.stable_subject_from_
    labels` that day, cadrage for 1.5's second collector (`docker
    diff` périodique) — the owner's own decision to factor it out
    before a third and fourth caller (dérive du digest, inventaire
    des paquets) would each otherwise need their own copy. This
    function is now only the part specific to a Docker *event*'s own
    payload shape: pulling `attributes`/`actor_id` out of `Actor`
    before handing them to the shared rule. Behaviour unchanged —
    this is a refactor, not a redesign.
    """

    actor = event.get("Actor")
    attributes = actor.get("Attributes") if isinstance(actor, dict) else None
    attributes = attributes if isinstance(attributes, dict) else {}
    actor_id = actor.get("ID") if isinstance(actor, dict) else None

    return stable_subject_from_labels(
        attributes,
        name=str(attributes.get("name") or ""),
        container_id=str(actor_id or ""),
    )


def occurred_at_of(event: Mapping[str, Any]) -> datetime:
    """
    The instant Docker itself says this event happened —
    `ADR-0011` § 4's `aistack:occurredAt`, the field that section
    says stays unstated for every stream that cannot state it
    independently of recording time; a real `docker events` payload
    always can, via `timeNano` (nanoseconds since the epoch, the
    finer of the two fields Docker emits) or, failing that, `time`
    (whole seconds).

    Falls back to the current instant only when a payload carries
    neither — malformed input this function does not raise on, the
    same defensive posture `stable_subject_of` holds for a payload
    missing its actor.
    """

    time_nano = event.get("timeNano")
    if isinstance(time_nano, (int, float)):
        # Integer arithmetic, not `time_nano / 1_000_000_000`: a real
        # `timeNano` (nanoseconds since the epoch, ~19 significant
        # digits by 2026) loses precision past a `float`'s own ~15-17,
        # which was measured here to round the last microsecond digit
        # incorrectly on a real value — `divmod` keeps the nanosecond
        # count exact up to the microsecond `datetime` itself can hold.
        seconds, nanoseconds = divmod(int(time_nano), 1_000_000_000)
        return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
            microsecond=nanoseconds // 1000
        )

    time_seconds = event.get("time")
    if isinstance(time_seconds, (int, float)):
        return datetime.fromtimestamp(time_seconds, tz=timezone.utc)

    return datetime.now(timezone.utc)


def docker_action_of(event: Mapping[str, Any]) -> str:
    """The action Docker recorded (`"start"`, `"destroy"`, `"exec_create"`, ...), or `""` when absent."""

    action = event.get("Action")
    return str(action) if action else ""


def enrich(event: Mapping[str, Any]) -> dict[str, Any]:
    """
    One raw Docker event, alongside the three facts `ADR-0011` §
    3-4 asks a *collector* to state — `subject`/`occurred_at`/
    `action` sit beside `raw`, never replacing it, so the evidence a
    human or a future qualifier reads is never less than what Docker
    itself reported (the same "raw stays raw" discipline
    `DockerProvider.collect_logs` already holds for log lines).
    """

    return {
        "subject": stable_subject_of(event),
        "occurred_at": occurred_at_of(event).isoformat(),
        "action": docker_action_of(event),
        "raw": dict(event),
    }

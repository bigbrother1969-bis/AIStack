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


# --- Exec noise: AIStack's own probes and declared healthchecks ------------
#
# Cadrage 2026-10-02, measured on the reference host before any code:
# one hour of this stream held 18,074 events, 97 % of them `exec_*` —
# about 3,800 healthcheck runs (gluetun, MariaDB, frigate, curl/wget
# probes) and 2,338 of AIStack's own `docker exec` package probes
# (`aistack.providers.docker.packages`), three events each. Neither is
# a trace of anything a person did, and together they buried the one
# real fault the stream held that hour: a container restarting every
# 17 seconds. Owner's choice: keep a human or external `docker exec`,
# drop the two automatic kinds — never every exec, which would lose
# exactly the manual action this collector exists to trace.

_MAX_REMEMBERED_EXEC_IDS = 4096
_MAX_CACHED_CONTAINERS = 1024


def _aistack_probe_commands() -> frozenset[str]:
    # Imported here, not at module top: `packages` is this collector's
    # sibling, and naming its commands from it — rather than copying
    # them — is what keeps the two from drifting apart.
    from aistack.providers.docker.packages import APK_DB_COMMAND, DPKG_QUERY_COMMAND

    return frozenset(
        " ".join(command).strip() for command in (DPKG_QUERY_COMMAND, APK_DB_COMMAND)
    )


def healthcheck_commands_of(inspect_entry: Mapping[str, Any]) -> frozenset[str]:
    """
    The exec command line(s) Docker reports when it runs this
    container's own declared healthcheck — the same string Docker puts
    after `exec_create: ` / `exec_start: ` in the event's `Action`.

    `CMD-SHELL x` runs through the container's own shell (its
    `Config.Shell`, `/bin/sh -c` when none is set) and so appears as
    `/bin/sh -c x`; `CMD a b` appears as `a b`. `NONE`, or no
    healthcheck at all, yields nothing.
    """

    config = inspect_entry.get("Config")
    config = config if isinstance(config, dict) else {}
    healthcheck = config.get("Healthcheck")
    test = healthcheck.get("Test") if isinstance(healthcheck, dict) else None
    if not isinstance(test, list) or len(test) < 2:
        return frozenset()

    kind, rest = str(test[0]), [str(part) for part in test[1:]]
    if kind == "CMD-SHELL":
        shell = config.get("Shell")
        shell_parts = (
            [str(part) for part in shell]
            if isinstance(shell, list) and shell
            else ["/bin/sh", "-c"]
        )
        return frozenset({" ".join([*shell_parts, *rest]).strip()})
    if kind == "CMD":
        return frozenset({" ".join(rest).strip()})
    return frozenset()


def _inspect_healthcheck(container_id: str) -> frozenset[str] | None:
    """`None` when Docker could not say — never cached, never read as "no healthcheck"."""

    from aistack.providers.docker.identity import inspect_containers

    entries = inspect_containers([container_id])
    if not entries or not isinstance(entries[0], dict):
        return None
    return healthcheck_commands_of(entries[0])


class ExecNoiseFilter:
    """
    Decides, event by event, whether a raw Docker event is exec noise —
    AIStack's own package probe, or a container's own declared
    healthcheck — and should be left out of Observation History.

    Only `exec_create` and `exec_start` name the command they ran;
    `exec_die` carries only its `execID`. So the filter remembers the
    `execID`s it dropped (bounded) and drops their `exec_die` too — it
    must live as long as the monitor's loop, not one cycle, since a
    probe's `exec_die` can land in the next poll window.

    **Never drops what it cannot prove is noise.** A non-exec event is
    always kept; an exec whose container Docker could not inspect is
    kept; an `exec_die` whose `exec_create` this process never saw (it
    started in between) is kept. The cost of a wrong keep is one noisy
    line; the cost of a wrong drop is a lost trace of a human action.
    """

    def __init__(
        self,
        *,
        healthchecks_by_subject: Mapping[str, frozenset[str]] | None = None,
        remember_uninspectable: bool = False,
    ) -> None:
        """
        The two keyword arguments exist for refiltering history after
        the fact (`aistack.cli.docker_events_refilter`), never for the
        live monitor: an old event names a container id that may no
        longer exist — recreated since by an image update — so
        `healthchecks_by_subject` (the healthchecks of the containers
        running now, by stable subject) stands in for an id Docker can
        no longer inspect, and `remember_uninspectable` stops the
        filter asking Docker again about an id it already could not
        resolve, across tens of thousands of archived events.
        """

        self._probe_commands = _aistack_probe_commands()
        self._dropped_exec_ids: dict[str, None] = {}
        self._healthchecks: dict[str, frozenset[str]] = {}
        self._healthchecks_by_subject = healthchecks_by_subject or {}
        self._remember_uninspectable = remember_uninspectable

    def _healthcheck_commands(self, container_id: str) -> frozenset[str]:
        cached = self._healthchecks.get(container_id)
        if cached is not None:
            return cached
        commands = _inspect_healthcheck(container_id)
        if commands is None:
            if not self._remember_uninspectable:
                return frozenset()
            commands = frozenset()
        if len(self._healthchecks) >= _MAX_CACHED_CONTAINERS:
            self._healthchecks.clear()
        self._healthchecks[container_id] = commands
        return commands

    def _remember(self, exec_id: str) -> None:
        if not exec_id:
            return
        self._dropped_exec_ids[exec_id] = None
        while len(self._dropped_exec_ids) > _MAX_REMEMBERED_EXEC_IDS:
            self._dropped_exec_ids.pop(next(iter(self._dropped_exec_ids)))

    def keep(self, event: Mapping[str, Any]) -> bool:
        action = docker_action_of(event)
        if not action.startswith("exec_"):
            return True

        actor = event.get("Actor")
        actor = actor if isinstance(actor, dict) else {}
        attributes = actor.get("Attributes")
        attributes = attributes if isinstance(attributes, dict) else {}
        exec_id = str(attributes.get("execID") or "")

        verb, separator, command = action.partition(":")
        if not separator:
            # `exec_die` and the like: no command, only the execID.
            return not (exec_id and exec_id in self._dropped_exec_ids)

        command = command.strip()
        noisy = command in self._probe_commands
        if not noisy:
            container_id = str(actor.get("ID") or "")
            noisy = bool(container_id) and command in self._healthcheck_commands(
                container_id
            )
        if not noisy and self._healthchecks_by_subject:
            noisy = command in self._healthchecks_by_subject.get(
                stable_subject_of(event), frozenset()
            )
        if noisy:
            self._remember(exec_id)
        return not noisy


def current_healthchecks_by_subject() -> dict[str, frozenset[str]]:
    """
    The declared healthcheck command(s) of every container running now,
    by stable subject — `ExecNoiseFilter(healthchecks_by_subject=...)`'s
    stand-in for a container id an archived event names but Docker can
    no longer inspect. `{}` when Docker cannot be reached.
    """

    from aistack.providers.docker.identity import (
        inspect_containers,
        list_running_container_names,
    )

    by_subject: dict[str, frozenset[str]] = {}
    for entry in inspect_containers(list_running_container_names()):
        if not isinstance(entry, dict):
            continue
        config = entry.get("Config")
        labels = config.get("Labels") if isinstance(config, dict) else None
        labels = labels if isinstance(labels, dict) else {}
        raw_name = entry.get("Name")
        subject = stable_subject_from_labels(
            labels,
            name=str(raw_name).lstrip("/") if raw_name else "",
            container_id=str(entry.get("Id") or ""),
        )
        commands = healthcheck_commands_of(entry)
        if commands:
            by_subject[subject] = commands
    return by_subject

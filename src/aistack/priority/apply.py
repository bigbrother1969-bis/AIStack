from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass

from aistack.priority.cpu import cpus_equal, format_cpus


class ContainerNotFound(RuntimeError):
    """A target container does not exist, or Docker could not be asked."""


@dataclass(frozen=True)
class ApplyReport:
    """
    What applying a set of CPU targets did, or found already true.

    Mirrors `MaterialisationReport`'s shape and reasoning: returned
    rather than printed, because the caller — eventually the étape
    4 monitor, for now whoever runs this by hand — is the only one
    positioned to act on it.

    **`not_found` is not `failed`.** A container the owner has
    stopped or removed for reasons of his own is not this feature
    misbehaving, and should not read the same as a Docker command
    that actually failed.
    """

    applied: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    not_found: tuple[str, ...] = ()
    failed: tuple[tuple[str, str], ...] = ()
    dry_run: bool = False

    @property
    def changed(self) -> bool:
        """
        Whether this report is worth surfacing to a human or to
        history — the one condition `aistack.cli
        .resource_priority_monitor.log_cycle` already prints on and
        `aistack.priority.decision_history.record_decision` (CPU
        decision history, 2026-09-03) now persists on, kept here as
        the single place either could drift from the other.

        `unchanged` alone is the quiet case: every container was
        already at its target, nothing for a poll cycle to say.
        `not_found` counts as a change worth surfacing even though
        nothing was written — a container the owner removed is
        still something worth a line, the same reasoning `not_found
        is not failed` already draws for a different distinction.
        """

        return bool(self.applied or self.failed or self.not_found)


def apply_resource_priority(
    targets: Mapping[str, float | None],
    unlimited_cpus: float,
    dry_run: bool = False,
) -> ApplyReport:
    """
    Bring every named container's CPU ceiling to its target.

    **Idempotent by construction.** Each container's current
    ceiling is read with `docker inspect` before anything is
    written, and `docker update` is called only where it differs
    from the target — a monitor calling this every few seconds
    while nothing has changed issues zero Docker mutations, the
    same reasoning as `materialise_by_hardlink`'s incremental
    reconciliation.

    **`unlimited_cpus` exists because Docker cannot clear a limit
    it has already set.** Verified live, 2026-09-03, against a real
    Engine API (not just the CLI): once a container's
    `HostConfig.NanoCpus` is nonzero, `docker update --cpus 0` is a
    silent no-op — confirmed by sending the raw
    `POST /containers/{id}/update` request with an explicit
    `{"NanoCPUs": 0}` body and reading `HostConfig.NanoCpus`
    unchanged afterwards. Moving such a container to the
    `--cpu-period`/`--cpu-quota` mechanism instead (where `-1`
    genuinely does mean "no quota") is refused outright by the
    daemon: *"Conflicting options: CPU Period cannot be updated as
    NanoCPUs has already been set"*. So a target of `None`
    ("unlimited", `ContainerPriorityDefinition.normal_cpus`'s own
    convention) is resolved to a concrete cap at `unlimited_cpus`
    (the host's own core count) *before* it is compared or
    written, never sent to Docker as a literal `0` — operationally
    the same thing, since nothing can use more cores than the host
    has anyway, and the one direction confirmed to work reliably
    every time.

    **The first call after this ships writes once more than a
    literal read of "nothing changed" would suggest.** A container
    Docker has never limited (`NanoCpus: 0`) compares against the
    resolved `unlimited_cpus` cap, not against `0`, so its very
    first reconciliation is a real write — trading the daemon's
    own "never configured" state for this feature's "explicitly
    capped at every core the host has," which behave identically
    in practice. Every call after that compares the same concrete
    number against itself and changes nothing.

    **One container's failure does not stop the others.** Given
    fourteen background containers plus Jellyfin, a single `docker
    update` failing — permission denied on the socket, the daemon
    momentarily busy, a container the owner removed — should not
    leave the other thirteen at their previous ceiling; each is
    attempted independently and reported on its own.

    **`dry_run` still reads.** Every container's current ceiling is
    checked either way; only the `docker update` call itself is
    skipped, so a dry run reports exactly which containers a real
    run would touch.

    **Verified live against a real Docker daemon, not GIGABYTE's.**
    `docker inspect`'s `HostConfig.NanoCpus` field is the one
    already named in the governed YAML's comments from measurements
    taken on GIGABYTE 2026-09-03
    (`claude/PLAN-RESOURCE-PRIORITY-2026-09-03.md`); this function
    was run end-to-end — including the throttle-then-restore cycle,
    twice, to confirm idempotency both ways — against disposable
    containers on a different host before being handed to the
    owner, which is exactly what caught the `--cpus 0` no-op above
    before it could reach GIGABYTE. It was never run against
    GIGABYTE's own containers, since doing that from here would
    mean reaching into infrastructure this session cannot see or
    undo. This layer is thin and host-touching for the same reason
    `selection_ui/app.py` sits outside the governed suite (decision
    #9): not unit-tested, verified live instead. Run with
    `dry_run=True` first against the real containers.
    """

    applied: list[str] = []
    unchanged: list[str] = []
    not_found: list[str] = []
    failed: list[tuple[str, str]] = []

    for name, target in targets.items():
        resolved_target = unlimited_cpus if target is None else target

        try:
            current = _read_current_cpus(name)
        except ContainerNotFound:
            not_found.append(name)
            continue

        if cpus_equal(current, resolved_target):
            unchanged.append(name)
            continue

        if dry_run:
            applied.append(name)
            continue

        result = subprocess.run(
            ["docker", "update", "--cpus", format_cpus(resolved_target), name],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            failed.append((name, result.stderr.strip()))
        else:
            applied.append(name)

    return ApplyReport(
        applied=tuple(applied),
        unchanged=tuple(unchanged),
        not_found=tuple(not_found),
        failed=tuple(failed),
        dry_run=dry_run,
    )


def _read_current_cpus(container: str) -> float | None:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{json .HostConfig.NanoCpus}}",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise ContainerNotFound(
            result.stderr.strip() or f"no such container: {container}"
        )

    nano_cpus = json.loads(result.stdout.strip() or "null")

    return (nano_cpus / 1_000_000_000) if nano_cpus else None

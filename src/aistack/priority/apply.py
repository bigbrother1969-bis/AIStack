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

    `not_found` (a container stopped or removed) is kept apart from `failed`
    (a Docker command that actually failed).
    """

    applied: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    not_found: tuple[str, ...] = ()
    failed: tuple[tuple[str, str], ...] = ()
    dry_run: bool = False

    @property
    def changed(self) -> bool:
        """
        Whether this report is worth logging or recording: something was
        applied, failed or not found. Shared by `log_cycle` and
        `record_decision` so their triggers cannot drift apart.
        """

        return bool(self.applied or self.failed or self.not_found)


def apply_resource_priority(
    targets: Mapping[str, float | None],
    unlimited_cpus: float,
    dry_run: bool = False,
) -> ApplyReport:
    """
    Bring every named container's CPU ceiling to its target.

    Idempotent: the current ceiling is read with `docker inspect` and
    `docker update` runs only where it differs. One container's failure
    does not stop the others. `dry_run` still reads, and skips only the
    update.

    Docker cannot clear a CPU limit once set: `docker update --cpus 0` is a
    silent no-op, and switching to `--cpu-quota` is refused. A `None`
    (unlimited) target is therefore written as a cap at `unlimited_cpus`,
    the host's core count. A container never limited is written once, then
    compares equal on every later call.

    Not unit-tested: it calls Docker. Run with `dry_run=True` first.
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

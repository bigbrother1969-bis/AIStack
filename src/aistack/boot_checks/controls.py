"""
The base controls of a start, judged by code (ADR-0032, slice B2).

Each control reads facts (`aistack.boot_checks.facts`) and what the owner
declared (`boot_checks.yml`) and says one thing: it passes, it is waiting,
it is to watch, it is to fix, or it was not checked and why. No control
reads a machine and none calls an AI engine: the verdict is the same
whoever asks, and an engine that is silent changes nothing.

A control the owner did not declare (no reference list of containers, no
mount, no probe) is **skipped and says so**, never guessed and never
counted as passed. A source that did not answer is *unknown*, never a
healthy host. Before `settle_minutes` after the start, what fails is
*pending*: the containers are still coming up and the restart watch works
(ADR-0025); it is not an anomaly yet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from aistack.boot_checks.definition import CRITICAL, IGNORE, WARNING, BootChecksDefinition
from aistack.boot_checks.facts import BootFacts

OK = "ok"
PENDING = "pending"
SKIPPED = "skipped"
UNKNOWN = "unknown"
INFORMATION = "information"

# The statuses that count as an anomaly.
ANOMALIES = (WARNING, CRITICAL)
MAX_DETAILS = 12


@dataclass(frozen=True)
class Reading:
    """What the cockpit says of a domain AIStack already judges (disks: OPS-0005, backups: OPS-0006)."""

    instrumented: bool
    findings: int = 0
    note: str = ""


@dataclass(frozen=True)
class Result:
    """One control's answer. `details` are names and counts, never a line of a log."""

    control: str
    status: str
    summary: str
    details: tuple[str, ...] = ()
    finding: str = ""


def _fails(
    control: str,
    finding: str,
    summary: str,
    details: tuple[str, ...],
    definition: BootChecksDefinition,
    settled: bool,
) -> Result | None:
    """A failing control, weighed by the declaration; `None` when the owner ignores that finding."""

    weight = definition.severity.get(finding, WARNING)

    if weight == IGNORE:
        return None

    return Result(control, weight if settled else PENDING, summary, details[:MAX_DETAILS], finding)


def _passes(control: str, summary: str) -> Result:
    return Result(control, OK, summary)


def _skipped(control: str, why: str) -> Result:
    return Result(control, SKIPPED, why)


def _unknown(control: str, facts: BootFacts, source: str) -> Result:
    reason = facts.sources.get(source, "no answer")

    return Result(control, UNKNOWN, f"not read: {reason}")


def _failed_units(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if facts.failed_units is None:
        return _unknown("failed_units", facts, "failed_units")

    if facts.failed_units:
        return _fails(
            "failed_units", "failed_unit", f"{len(facts.failed_units)} unit(s) failed", facts.failed_units, definition, settled
        )

    return _passes("failed_units", "no failed unit")


def _mounts(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if not definition.mounts:
        return _skipped("mounts", "no mount declared")

    if facts.mounts is None:
        return _unknown("mounts", facts, "mounts")

    missing = tuple(path for path in definition.mounts if path not in facts.mounts)

    if missing:
        return _fails("mounts", "mount_missing", f"{len(missing)} mount(s) missing", missing, definition, settled)

    return _passes("mounts", f"{len(definition.mounts)} declared mount(s) present")


def _containers(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> list[Result]:
    if facts.containers is None:
        return [_unknown("containers", facts, "containers"), _unknown("container_health", facts, "containers")]

    found: list[Result | None] = []
    by_name = {container.name: container for container in facts.containers}

    if not definition.expected_containers:
        found.append(_skipped("containers", "no reference list of containers declared"))
    else:
        missing = tuple(name for name in definition.expected_containers if name not in by_name)
        stopped_by_mistake = tuple(
            name
            for name in definition.expected_containers
            if name in by_name and by_name[name].state != "running" and name not in definition.expected_stopped
        )

        if missing:
            found.append(
                _fails("containers", "container_missing", f"{len(missing)} container(s) missing", missing, definition, settled)
            )
        elif stopped_by_mistake:
            found.append(
                _fails(
                    "containers", "container_stopped", f"{len(stopped_by_mistake)} container(s) stopped",
                    stopped_by_mistake, definition, settled,
                )
            )
        else:
            running = sum(1 for item in facts.containers if item.state == "running")
            found.append(_passes("containers", f"{len(definition.expected_containers)} expected present, {running} running"))

    unhealthy = tuple(item.name for item in facts.containers if item.health == "unhealthy")
    starting = tuple(item.name for item in facts.containers if item.health == "starting")

    if unhealthy:
        found.append(
            _fails("container_health", "container_unhealthy", f"{len(unhealthy)} container(s) unhealthy", unhealthy, definition, settled)
        )
    elif starting:
        found.append(Result("container_health", PENDING, f"{len(starting)} container(s) still starting", starting[:MAX_DETAILS]))
    else:
        found.append(_passes("container_health", "no container unhealthy"))

    return [result for result in found if result is not None]


def _docker_user(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if definition.docker_user_rules is None:
        return _skipped("docker_user", "number of DOCKER-USER rules not declared")

    if facts.docker_user_rules is None:
        return _unknown("docker_user", facts, "docker_user_rules")

    if facts.docker_user_rules != definition.docker_user_rules:
        return _fails(
            "docker_user", "docker_user_changed", "the DOCKER-USER chain changed",
            (f"declared {definition.docker_user_rules}, found {facts.docker_user_rules}",), definition, settled,
        )

    return _passes("docker_user", f"{facts.docker_user_rules} rules, as declared")


def _probes(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if not definition.probes:
        return _skipped("probes", "no probe declared")

    if facts.probes is None:
        return _unknown("probes", facts, "probes")

    wrong = tuple(
        f"{label}: {facts.probes.get(label, 'not read')} instead of {status}"
        for label, status in sorted(definition.probes.items())
        if facts.probes.get(label) != status
    )

    if wrong:
        return _fails("probes", "probe_failed", f"{len(wrong)} probe(s) failed", wrong, definition, settled)

    return _passes("probes", f"{len(definition.probes)} probe(s) answer as declared")


def _kvm(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if facts.kvm_modules is None:
        return _unknown("kvm_modules", facts, "kvm_modules")

    if facts.kvm_modules:
        return _fails("kvm_modules", "kvm_modules", "KVM modules are loaded", (), definition, settled)

    return _passes("kvm_modules", "KVM modules not loaded")


def _ups(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if facts.sources.get("ups") == "absent":
        return _skipped("ups", "no UPS declared on the host")

    if facts.ups is None:
        return _unknown("ups", facts, "ups")

    word = facts.ups.split()[0] if facts.ups.split() else ""

    if word not in definition.ups_expected:
        return _fails("ups", "ups_on_battery", f"the UPS says {facts.ups}", (), definition, settled)

    return _passes("ups", f"the UPS says {facts.ups}")


def _previous_boot(facts: BootFacts) -> Result:
    """What the end of the previous run says. A past event: shown, never an anomaly."""

    if facts.previous_boot_clean is None:
        return Result("previous_boot", INFORMATION, "the end of the previous run is not known")

    if facts.previous_boot_clean:
        return Result("previous_boot", INFORMATION, "the previous run ended with a clean shutdown")

    return Result("previous_boot", INFORMATION, "the previous run did not end with a shutdown (power loss or hard stop)")


def _reading(control: str, finding: str, name: str, reading: Reading | None, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if reading is None:
        return _skipped(control, f"{name} was not read")

    if not reading.instrumented:
        return _skipped(control, reading.note or f"{name} is not instrumented on this host")

    if reading.findings:
        return _fails(control, finding, f"{reading.findings} finding(s) in the {name} domain", (), definition, settled)

    return _passes(control, f"nothing to report in the {name} domain")


def evaluate(
    facts: BootFacts,
    definition: BootChecksDefinition,
    now: datetime,
    storage: Reading | None = None,
    backup: Reading | None = None,
) -> list[Result]:
    """Every control of the base set, in a stable order."""

    settled = facts.booted_at is None or now - facts.booted_at >= timedelta(minutes=definition.settle_minutes)
    singles: list[Callable[[BootFacts, BootChecksDefinition, bool], Result | None]] = [_failed_units, _mounts]
    results: list[Result | None] = [check(facts, definition, settled) for check in singles]
    results.extend(_containers(facts, definition, settled))

    for check in (_docker_user, _probes, _kvm, _ups):
        results.append(check(facts, definition, settled))

    results.append(_reading("storage", "storage_low", "storage", storage, definition, settled))
    results.append(_reading("backup", "backup_late", "backup", backup, definition, settled))
    results.append(_previous_boot(facts))

    return [result for result in results if result is not None]

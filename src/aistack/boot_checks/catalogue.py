"""
The extra controls of a start and what justifies them (ADR-0032 § 3, slice B5a).

The base controls run at every pass. These run only when the circumstances
call for them: a start that followed a stop that was not clean looks at the
databases and the kernel's disk errors, a recent start tells its cause, a
start inside the backup window looks at the backup, memory under pressure
looks at memory.

The **circumstances** are computed by code from the facts, never guessed.
The **catalogue** is closed: five controls, each read-only, each linked by
the declaration to the circumstances that justify it. `choose` is the rule
that picks them; a later slice lets an AI engine pick among the same
catalogue and falls back on this rule when it is silent. Either way the
verdict of each control is computed here, by code.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aistack.boot_checks.controls import INFORMATION, UNKNOWN, Reading, Result, _fails, _passes, _skipped, _unknown
from aistack.boot_checks.definition import CIRCUMSTANCES, EXTRA_CONTROLS, BootChecksDefinition
from aistack.boot_checks.facts import BootFacts


def _clock(value: str) -> time:
    hour, minute = value.split(":")

    return time(int(hour), int(minute))


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def _in_window(start: datetime, definition: BootChecksDefinition) -> bool:
    """Whether the start fell in the backup window, in the owner's time zone (a window may cross midnight)."""

    moment = start.astimezone(_zone(definition.timezone)).time()
    opening, closing = (_clock(value) for value in definition.backup_window)

    return opening <= moment < closing if opening <= closing else moment >= opening or moment < closing


def _pressed(facts: BootFacts, definition: BootChecksDefinition) -> bool:
    return (facts.memory_pressure is not None and facts.memory_pressure >= definition.memory_pressure_percent) or (
        facts.swap_used_percent is not None and facts.swap_used_percent >= definition.swap_used_percent
    )


def circumstances(facts: BootFacts, definition: BootChecksDefinition) -> tuple[str, ...]:
    """The circumstances that hold now, in the closed order of `CIRCUMSTANCES`."""

    holding: set[str] = set()

    if facts.previous_boot_clean is False:
        holding.add("unclean_previous_stop")

    on_battery = facts.ups is not None and facts.ups.split(" ")[0] not in definition.ups_expected

    if facts.stop_reason == "ups" or on_battery:
        holding.add("ups_event")

    if facts.uptime_seconds is not None and facts.uptime_seconds < definition.recent_restart_hours * 3600:
        holding.add("recent_restart")

    if facts.booted_at is not None and _in_window(facts.booted_at, definition):
        holding.add("restart_in_backup_window")

    if _pressed(facts, definition):
        holding.add("memory_pressure")

    return tuple(item for item in CIRCUMSTANCES if item in holding)


def choose(found: tuple[str, ...], definition: BootChecksDefinition) -> tuple[str, ...]:
    """The extra controls the circumstances justify, in catalogue order, at most `ai_max_extra_controls`."""

    chosen = [
        control
        for control in EXTRA_CONTROLS
        if any(item in found for item in definition.catalogue.get(control, ()))
    ]

    return tuple(chosen[: definition.ai_max_extra_controls])


def _database_recovery(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result:
    if not definition.database_containers:
        return _skipped("database_recovery", "no database container declared")

    if facts.database_recovery is None:
        return _unknown("database_recovery", facts, "database_recovery")

    unread = tuple(name for name in definition.database_containers if name not in facts.database_recovery)
    recovered = tuple(name for name in definition.database_containers if facts.database_recovery.get(name, 0) > 0)

    if recovered:
        failed = _fails("database_recovery", "database_recovery", f"{len(recovered)} database(s) recovered after the start", recovered, definition, settled)

        return failed if failed is not None else _skipped("database_recovery", "database recovery findings are ignored")

    if unread:
        return Result("database_recovery", UNKNOWN, f"{len(unread)} database log(s) not read", unread)

    return _passes("database_recovery", f"{len(definition.database_containers)} database log(s) read, no recovery")


def _kernel_disk_errors(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result:
    if facts.kernel_disk_errors is None:
        return _unknown("kernel_disk_errors", facts, "kernel_disk_errors")

    if facts.kernel_disk_errors:
        failed = _fails(
            "kernel_disk_errors", "kernel_disk_errors", f"{facts.kernel_disk_errors} disk or file-system error line(s) in the kernel log since the start", (), definition, settled
        )

        return failed if failed is not None else _skipped("kernel_disk_errors", "kernel disk errors are ignored")

    return _passes("kernel_disk_errors", "no disk or file-system error in the kernel log since the start")


_CAUSES = {
    "ups": "the previous run was stopped by the UPS (power cut)",
    "requested": "the previous run was stopped by a shutdown or a reboot that was asked for",
    "unknown": "the cause of the previous stop is not in the journal",
}


def _restart_cause(facts: BootFacts) -> Result:
    """The cause of the last stop, told and never judged: a past event."""

    if facts.stop_reason is None:
        return Result("restart_cause", INFORMATION, "the cause of the previous stop is not known")

    return Result("restart_cause", INFORMATION, _CAUSES.get(facts.stop_reason, _CAUSES["unknown"]))


def _backup_after_restart(backup: Reading | None, definition: BootChecksDefinition, settled: bool) -> Result:
    """
    A start inside the backup window may have cut the backup short. The backup domain (OPS-0006)
    says whether it is late or failed; this control says it was asked because of the start.
    """

    if backup is None or not backup.instrumented:
        return _skipped("backup_after_restart", (backup.note if backup is not None else "") or "the backup domain was not read")

    if backup.findings:
        failed = _fails(
            "backup_after_restart", "backup_late", f"the start fell in the backup window and the backup domain has {backup.findings} finding(s)", (), definition, settled
        )

        return failed if failed is not None else _skipped("backup_after_restart", "backup findings are ignored")

    return _passes("backup_after_restart", "the start fell in the backup window; the backup domain has nothing to report")


def _memory(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result:
    if facts.memory_pressure is None and facts.swap_used_percent is None:
        return _unknown("memory", facts, "memory_pressure")

    said = f"memory pressure {facts.memory_pressure if facts.memory_pressure is not None else '?'} %, swap {facts.swap_used_percent if facts.swap_used_percent is not None else '?'} % in use"

    if _pressed(facts, definition):
        failed = _fails("memory", "memory_pressure", said, (), definition, settled)

        return failed if failed is not None else _skipped("memory", "memory findings are ignored")

    return _passes("memory", said)


def evaluate_extra(
    chosen: tuple[str, ...],
    facts: BootFacts,
    definition: BootChecksDefinition,
    backup: Reading | None,
    settled: bool,
) -> list[Result]:
    """The answer of each chosen extra control, in catalogue order."""

    answers = {
        "database_recovery": lambda: _database_recovery(facts, definition, settled),
        "kernel_disk_errors": lambda: _kernel_disk_errors(facts, definition, settled),
        "restart_cause": lambda: _restart_cause(facts),
        "backup_after_restart": lambda: _backup_after_restart(backup, definition, settled),
        "memory": lambda: _memory(facts, definition, settled),
    }

    return [answers[control]() for control in EXTRA_CONTROLS if control in chosen]


def settled_since(facts: BootFacts, definition: BootChecksDefinition, now: datetime) -> bool:
    """Whether `settle_minutes` have passed since the start (the same rule as the base controls)."""

    return facts.booted_at is None or now - facts.booted_at >= timedelta(minutes=definition.settle_minutes)

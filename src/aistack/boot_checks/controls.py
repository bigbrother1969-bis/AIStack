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

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from aistack.boot_checks.definition import CRITICAL, IGNORE, WARNING, BootChecksDefinition
from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.boot_checks.expiry import Expiry, ExpiryReading
from aistack.boot_checks.disks import COUNTERS, LINK_COUNTERS, Disk, DiskReading
from aistack.boot_checks.facts import BootFacts
from aistack.boot_checks.monitor import DOWN, MAINTENANCE, WAITING, MonitorReading
from aistack.boot_checks.trend import Trend, trend_of
from aistack.boot_checks.usage import UsageReading
from aistack.boot_checks.systems import DOWN as SYSTEM_DOWN
from aistack.boot_checks.systems import UP as SYSTEM_UP
from aistack.boot_checks.systems import SystemsReading

if TYPE_CHECKING:
    from aistack.boot_checks.recurrence import RecurrenceReading

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
class RestoreGap:
    """A restore test (OPS-0009) that is not good: `reason` is `failed`, `stale` (older than the limit) or `untested`."""

    service: str
    reason: str
    tested_at: datetime | None
    max_age_days: float


@dataclass(frozen=True)
class RestoreReading:
    """
    What the restore tests say. `declared` is false when no test is declared (the control is skipped); `reason` says
    why they could not be read (the control is then *unknown*, never fine).
    """

    tests: int = 0
    gaps: tuple[RestoreGap, ...] = ()
    declared: bool = True
    reason: str = ""


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


# What `vcgencmd get_throttled` says: the low four bits are true now, the same four,
# sixteen places up, are true since the start.
_THROTTLE_NOW = 0xF
_THROTTLE_NAMES = ("under-voltage", "frequency capped", "throttled", "soft temperature limit")


def _throttle_names(bits: int) -> tuple[str, ...]:
    return tuple(name for index, name in enumerate(_THROTTLE_NAMES) if bits >> index & 1)


def _throttled(facts: BootFacts, definition: BootChecksDefinition, settled: bool) -> Result | None:
    """A Raspberry's power and temperature. Not a control for a host that has no such command."""

    if facts.sources.get("throttled") == "absent":
        return None

    if facts.throttled is None:
        return _unknown("throttled", facts, "throttled")

    now = _throttle_names(facts.throttled & _THROTTLE_NOW)
    since = _throttle_names(facts.throttled >> 16 & _THROTTLE_NOW)

    power = ("to do: the power supply or its cable is too weak, use the board's own supply",) if "under-voltage" in (*now, *since) else ()

    if now:
        return _fails("throttled", "companion_throttled", "a power or temperature limit is active now", (*now, *power), definition, settled)

    if since:
        return Result("throttled", INFORMATION, "a limit was reached since the start, none now", (*since, *power))

    return _passes("throttled", "no power or temperature limit, now or since the start")


def _clock(facts: BootFacts) -> Result | None:
    """Whether the start time can be trusted: a host with no clock of its own is wrong until the network sets it."""

    if facts.clock_synced is None:
        return None

    if facts.clock_synced:
        return Result("clock", INFORMATION, "the clock was set by the network")

    return Result("clock", INFORMATION, "the clock is not set by the network yet: the start time may be off")


def evaluate_companion(
    name: str,
    facts: BootFacts | None,
    note: str,
    definition: BootChecksDefinition,
    now: datetime,
) -> list[Result]:
    """
    The controls of a companion machine, from the facts its own host unit pushed.

    No facts (the file is old, or damaged) is the machine *unreachable*, to
    fix by default: a Raspberry that stopped writing is not a healthy one. What
    only the MSI has (containers, the firewall chain, the UPS) is not asked of it.
    """

    if facts is None:
        missing = _fails("reachable", "companion_unreachable", note or "no facts", (), definition, True)

        return [missing if missing is not None else _skipped("reachable", note or "no facts")]

    settled = facts.booted_at is None or now - facts.booted_at >= timedelta(minutes=definition.settle_minutes)
    own = replace(definition, mounts=definition.companion_mounts.get(name, ()))
    results: list[Result | None] = [
        _passes("reachable", f"facts from {facts.collected_at.strftime('%H:%M')} UTC"),
        _failed_units(facts, own, settled),
        _mounts(facts, own, settled),
        _throttled(facts, own, settled),
        _clock(facts),
        _previous_boot(facts),
    ]

    return [result for result in results if result is not None]


NAMED = 4


def _named(names: tuple[str, ...]) -> str:
    """The first monitors by name, so an incident says which ones and not only how many."""

    shown = ", ".join(names[:NAMED])
    more = f", +{len(names) - NAMED}" if len(names) > NAMED else ""

    return f" ({shown}{more})"


def _monitors(reading: MonitorReading | None, definition: BootChecksDefinition, settled: bool) -> Result:
    """Uptime Kuma: a monitor that is down, and (with a reference list) one that is missing or paused."""

    if reading is None:
        return _skipped("monitor", "Uptime Kuma is not connected (its address and an API key, in Settings)")

    if not reading.reachable:
        return Result("monitor", UNKNOWN, f"not read: {reading.reason}")

    names = reading.monitors
    down = tuple(sorted(name for name, status in names.items() if status == DOWN))
    waiting = tuple(sorted(name for name, status in names.items() if status == WAITING))
    missing = tuple(name for name in definition.expected_monitors if name not in names)
    broken = (*down, *missing)

    if broken:
        parts = [f"{len(down)} down" if down else "", f"{len(missing)} missing or paused" if missing else ""]
        failed = _fails("monitor", "monitor_down", ", ".join(part for part in parts if part) + _named(broken), broken, definition, settled)

        return failed if failed is not None else _skipped("monitor", "monitor findings are ignored")

    if waiting:
        return _fails("monitor", "monitor_down", f"{len(waiting)} monitor(s) still pending", waiting, definition, settled) or _skipped(
            "monitor", "monitor findings are ignored"
        )

    running = sum(1 for status in names.values() if status != MAINTENANCE)
    note = "" if definition.expected_monitors else " (no reference list declared)"

    return _passes("monitor", f"{running} monitor(s) up, none down{note}")


def _rises(disk: Disk, now: datetime, days: int) -> list[tuple[int, int, int, datetime]]:
    """The watched counters of a disk that rose within the last `days`: (counter, from, to, since)."""

    found = []

    for number, points in disk.counters:
        inside = [point for point in points if now - point[0] <= timedelta(days=days)]

        if len(inside) >= 2 and inside[-1][1] > inside[0][1]:
            found.append((number, inside[0][1], inside[-1][1], inside[0][0]))

    return found


def _life_left(disk: Disk, definition: BootChecksDefinition) -> int | None:
    """An SSD's life left, in percent, from the attribute the owner declared for its model; `None` when none is declared or read."""

    model = disk.model.lower()
    number = next((attribute for part, attribute in definition.ssd_life.items() if part.lower() in model), None)

    if number is None:
        return None

    left = dict(disk.levels).get(number)

    return left if left is not None and 0 <= left <= 100 else None


def _ssd_pace(disk: Disk, left: int) -> str:
    """How long the life left lasts at the pace since new, said only once a month of use is behind and some life is gone."""

    used = 100 - left

    if disk.hours is None or disk.hours < 720 or used < 1:
        return ""

    return f", about {disk.hours * left / used / 8766:.1f} year(s) at the pace since new"


def _disks(reading: DiskReading | None, definition: BootChecksDefinition, now: datetime) -> Result:
    """Scrutiny: a SMART failure is to fix, a critical attribute above zero is to watch; age and statistics are only said."""

    if reading is None:
        return _skipped("disks", "Scrutiny is not connected (its address, in Settings)")

    if not reading.reachable:
        return Result("disks", UNKNOWN, f"not read: {reading.reason}")

    active = [disk for disk in reading.disks if not disk.archived]

    if not active:
        return Result("disks", UNKNOWN, "not read: Scrutiny reports no active disk")

    limit = timedelta(hours=definition.disk_report_hours)
    stale = [disk for disk in active if disk.collected_at is None or now - disk.collected_at > limit]
    fresh = [disk for disk in active if disk not in stale]
    unread = [disk for disk in fresh if not disk.attributes_read]
    failing = [disk for disk in fresh if disk.failed_smart]
    worn = [disk for disk in fresh if disk.worn and not disk.failed_smart]
    old = [disk for disk in fresh if definition.disk_old_hours is not None and disk.hours is not None and disk.hours >= definition.disk_old_hours]
    hint = [disk for disk in fresh if disk.statistical and not disk.failed_smart and not disk.worn]
    heat = definition.disk_temperature_celsius
    rises = {disk.wwn: _rises(disk, now, definition.disk_rising_days) for disk in fresh}
    rising = [disk for disk in fresh if rises[disk.wwn]]
    hot = [disk for disk in fresh if disk.temperature is not None and disk.temperature >= heat]
    peaked = [disk for disk in fresh if disk not in hot and disk.peak is not None and disk.peak[0] >= heat]
    life = {disk.wwn: _life_left(disk, definition) for disk in fresh}
    wearing = [disk for disk in fresh if life[disk.wwn] is not None and life[disk.wwn] <= definition.ssd_life_percent]  # type: ignore[operator]

    said_life = tuple(f"{disk.label}: {life[disk.wwn]} % of life left{_ssd_pace(disk, life[disk.wwn])}" for disk in fresh if life[disk.wwn] is not None)  # type: ignore[arg-type]

    def names(group: list[Disk]) -> tuple[str, ...]:
        return tuple(disk.label for disk in group)

    head = f"{len(active)} disk(s) read" + ("" if failing or worn else ", none failing")
    parts = [
        f"{len(failing)} failing SMART" if failing else "",
        f"{len(worn)} with a critical SMART attribute above zero" if worn else "",
        f"{len(stale)} not reported for over {definition.disk_report_hours} h" if stale else "",
        f"{len(unread)} without readable attributes" if unread else "",
        f"{len(old)} old" if old else "",
        f"{len(hint)} flagged only by Scrutiny's statistics" if hint else "",
        f"{len(rising)} with a counter rising" if rising else "",
        f"{len(hot)} at or above {heat} \u00b0C" if hot else "",
        f"{len(peaked)} peaked at or above {heat} \u00b0C" if peaked else "",
        f"{len(wearing)} SSD(s) at or below {definition.ssd_life_percent} % of life left" if wearing else "",
    ]
    summary = "; ".join([head, *(part for part in parts if part)])

    if failing:
        failed = _fails("disks", "disk_failing", summary, names(failing + worn), definition, True)

        return failed if failed is not None else _skipped("disks", "disk findings are ignored")

    if worn:
        failed = _fails("disks", "disk_attribute", summary, names(worn), definition, True)

        return failed if failed is not None else _skipped("disks", "disk findings are ignored")

    if rising:
        lines = tuple(
            f"{disk.label}: {COUNTERS[number]} rose from {before} to {after} since {since:%Y-%m-%d}"
            for disk in rising
            for number, before, after, since in rises[disk.wwn]
        )
        media = any(number not in LINK_COUNTERS for disk in rising for number, *_ in rises[disk.wwn])
        link = any(number in LINK_COUNTERS for disk in rising for number, *_ in rises[disk.wwn])
        todo = (("to do: back up the disks above now and plan to replace them",) if media else ()) + (
            ("to do: check the SATA cable and the power connector of the disks above",) if link else ()
        )
        failed = _fails("disks", "disk_counter_rising", summary, (*lines[: MAX_DETAILS - len(todo) - len(said_life)], *said_life, *todo), definition, True)

        return failed if failed is not None else _skipped("disks", "disk findings are ignored")

    if hot:
        lines = tuple(f"{disk.label}: {disk.temperature} \u00b0C now (limit {heat} \u00b0C)" for disk in hot)
        failed = _fails("disks", "disk_hot", summary, (*lines, *said_life, "to do: check the airflow and the fan of the machine"), definition, True)

        return failed if failed is not None else _skipped("disks", "disk findings are ignored")

    if wearing:
        lines = tuple(f"{disk.label}: {life[disk.wwn]} % of life left (limit {definition.ssd_life_percent} %)" for disk in wearing)
        failed = _fails("disks", "ssd_worn", summary, (*lines, "to do: back up the SSD above and plan its replacement"), definition, True)

        return failed if failed is not None else _skipped("disks", "disk findings are ignored")

    if stale or unread:
        return Result("disks", UNKNOWN, summary, names(stale + unread)[:MAX_DETAILS])

    if old or hint or peaked or said_life:
        said = names(old + [disk for disk in hint if disk not in old])
        past = tuple(f"{disk.label}: reached {disk.peak[0]} \u00b0C on {disk.peak[1]:%Y-%m-%d}" for disk in peaked if disk.peak is not None)

        return Result("disks", INFORMATION, summary, (*said, *past, *said_life)[:MAX_DETAILS])

    return _passes("disks", summary)


_STAMP = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})")


def _silent(system: BeszelSystemReading) -> str:
    """A machine Beszel calls down, with when its last measure arrived (UTC) when Beszel said; the bare name when it did not."""

    found = _STAMP.match(system.last_reading)

    return f"{system.name} (no reading since {found.group(1)} {found.group(2)} UTC)" if found else system.name


def _systems(reading: SystemsReading | None, definition: BootChecksDefinition) -> Result:
    """Beszel: a machine it calls down, or one whose disk, memory or temperature is at its declared limit, is to watch."""

    if reading is None:
        return _skipped("systems", "Beszel is not connected (its account, in Settings)")

    if not reading.reachable:
        return Result("systems", UNKNOWN, f"not read: {reading.reason}")

    judged = [system for system in reading.systems if system.status in (SYSTEM_UP, SYSTEM_DOWN)]

    if not judged:
        return Result("systems", UNKNOWN, "not read: Beszel reports no machine in service")

    down = [system for system in judged if system.status == SYSTEM_DOWN]
    alive = [system for system in judged if system.status == SYSTEM_UP]
    unread = [system for system in alive if system.disk_pct is None and system.mem_pct is None and system.temp_c is None]
    disk = [system for system in alive if system.disk_pct is not None and system.disk_pct >= definition.system_disk_percent]
    memory = [system for system in alive if system.mem_pct is not None and system.mem_pct >= definition.system_memory_percent]
    hot = [system for system in alive if system.temp_c is not None and system.temp_c >= definition.system_temperature_celsius]
    pressed = [system for system in alive if system in disk or system in memory or system in hot]

    def names(group: list[BeszelSystemReading]) -> tuple[str, ...]:
        return tuple(_silent(system) if system.status == SYSTEM_DOWN else system.name for system in group)

    head = f"{len(judged)} system(s) read" + ("" if down or pressed else ", none down, none under pressure")
    parts = [
        f"{len(down)} system(s) down" if down else "",
        f"{len(disk)} with disk use at or above {definition.system_disk_percent} %" if disk else "",
        f"{len(memory)} with memory use at or above {definition.system_memory_percent} %" if memory else "",
        f"{len(hot)} at or above {definition.system_temperature_celsius} \u00b0C" if hot else "",
        f"{len(unread)} without readings" if unread else "",
    ]
    summary = "; ".join([head, *(part for part in parts if part)])

    if down:
        failed = _fails("systems", "system_down", summary, names(down + pressed), definition, True)

        return failed if failed is not None else _skipped("systems", "system findings are ignored")

    if pressed:
        failed = _fails("systems", "system_pressure", summary, names(pressed), definition, True)

        return failed if failed is not None else _skipped("systems", "system findings are ignored")

    if unread:
        return Result("systems", UNKNOWN, summary, names(unread))

    return _passes("systems", summary)


def _disk_trend(reading: SystemsReading | None, definition: BootChecksDefinition, now: datetime) -> Result | None:
    """Beszel's measures of the system disks, as a line: a disk that would be full within the declared days is to watch."""

    if reading is None or not reading.reachable:
        return None  # the `systems` control already says why

    up = [system for system in reading.systems if system.status == SYSTEM_UP]

    if not up:
        return None

    history = dict(reading.history)
    measured: list[tuple[str, Trend]] = []
    short: list[str] = []

    for system in up:
        found = trend_of(history.get(system.name, ()), now, definition.disk_trend_days, definition.disk_trend_min_days)

        if found is None:
            short.append(system.name)
        else:
            measured.append((system.name, found))

    if not measured:
        return Result("disk_trend", UNKNOWN, f"not read: Beszel has less than {definition.disk_trend_min_days} days of measures for the system disks", tuple(short))

    soon = [(name, found) for name, found in measured if found.days_to_full is not None and found.days_to_full <= definition.disk_full_days]
    growing = [(name, found) for name, found in measured if found.days_to_full is not None and (name, found) not in soon]

    def said(group: list[tuple[str, Trend]]) -> tuple[str, ...]:
        return tuple(
            f"{name}: about {int(found.days_to_full or 0)} day(s) left at +{found.rate:.2f} GB/day ({found.used:.0f} of {found.total:.0f} GB)"
            for name, found in sorted(group, key=lambda pair: pair[1].days_to_full or 0.0)
        )

    summary = "; ".join(
        part
        for part in (
            f"{len(measured)} system(s) measured" + ("" if soon else f", none full within {definition.disk_full_days} days"),
            f"{len(soon)} full within {definition.disk_full_days} days" if soon else "",
            f"{len(short)} without enough history" if short else "",
        )
        if part
    )

    if soon:
        failed = _fails("disk_trend", "disk_full_soon", summary, said(soon) + said(growing), definition, True)

        return failed if failed is not None else _skipped("disk_trend", "disk trend findings are ignored")

    if short:
        return Result("disk_trend", UNKNOWN, summary, tuple(short) + said(growing))

    if growing:
        return Result("disk_trend", INFORMATION, summary, said(growing))

    return _passes("disk_trend", summary)


def _data_disks(reading: UsageReading | None, definition: BootChecksDefinition, now: datetime) -> Result | None:
    """The data disks of the host (O4b): at or above the declared percent, or filling within the declared days, is to watch."""

    if reading is None:
        return None

    if not reading.samples:
        return _skipped("data_disks", "no data disk to read (nothing under /media or /mnt, none declared)")

    history = dict(reading.history)
    full: list[tuple[str, str]] = []
    soon: list[tuple[str, Trend]] = []
    short: list[str] = []

    for sample in reading.samples:
        percent = 100.0 * sample.used / sample.total

        if percent >= definition.data_disk_percent:
            full.append((sample.point, f"{sample.point}: {percent:.1f} % used ({sample.used:.0f} of {sample.total:.0f} GB)"))

        found = trend_of(history.get(sample.point, ()), now, definition.disk_trend_days, definition.disk_trend_min_days)

        if found is None:
            short.append(sample.point)
        elif found.days_to_full is not None and found.days_to_full <= definition.disk_full_days:
            soon.append((sample.point, found))

    limit, days = definition.data_disk_percent, definition.disk_full_days
    parts = [
        f"{len(full)} at or above {limit} %" if full else "",
        f"{len(soon)} full within {days} days" if soon else "",
        f"{len(short)} without enough history" if short else "",
    ]
    quiet = not full and not soon
    summary = f"{len(reading.samples)} data disk(s) read" + (f", none at or above {limit} %, none full within {days} days" if quiet else "")
    summary = "; ".join([summary, *(part for part in parts if part)])
    lines = tuple(line for _, line in full) + tuple(
        f"{name}: about {int(found.days_to_full or 0)} day(s) left at +{found.rate:.2f} GB/day ({found.used:.0f} of {found.total:.0f} GB)"
        for name, found in sorted(soon, key=lambda pair: pair[1].days_to_full or 0.0)
    )

    for finding, group in (("data_disk_full", full), ("data_disk_soon", soon)):
        if group:
            failed = _fails("data_disks", finding, summary, lines, definition, True)

            if failed is not None:
                return failed

    if full or soon:
        return _skipped("data_disks", "data disk findings are ignored")

    return _passes("data_disks", summary)


def _copies(facts: BootFacts, definition: BootChecksDefinition, now: datetime) -> Result:
    """
    The copies the owner declared (O6): a backup folder, a rescue image, a folder of snapshots. A copy whose newest file
    is older than its limit is late, one with nothing in it is missing, one the host did not tell is *not read*.
    """

    if not definition.copies:
        return _skipped("copies", "no copy declared")

    if facts.sources.get("copies") == "absent":
        return Result("copies", UNKNOWN, "not read: the host unit was not told which copies to look at (AISTACK_BOOT_COPIES)")

    if facts.copies is None:
        return _unknown("copies", facts, "copies")

    late: list[str] = []
    missing: list[str] = []
    unread: list[str] = []

    for name, limit in sorted(definition.copies.items()):
        copy = facts.copies.get(name)

        if copy is None:
            unread.append(f"{name}: not read: the host unit does not report it")
        elif copy.error:
            unread.append(f"{name}: not read: {copy.error}")
        elif copy.newest is None:
            missing.append(f"{name}: no copy found")
        elif (age := (now - copy.newest).total_seconds() / 86400) > limit:
            late.append(f"{name}: newest copy is {math.ceil(age)} day(s) old (limit {limit} day(s))")

    if missing or late:
        action = "to do: check that the job that makes each copy above ran (its timer, its last log)"
        summary = f"{len(missing) + len(late)} copy(ies) late or missing"
        failed = _fails("copies", "copy_missing" if missing else "copy_late", summary, (*missing, *late, *unread, action), definition, True)

        return failed if failed is not None else _skipped("copies", "copy findings are ignored")

    if unread:
        return Result("copies", UNKNOWN, f"{len(unread)} declared copy(ies) not read", tuple(unread))

    return _passes("copies", f"{len(definition.copies)} declared copy(ies) within their limit")


def _restore_tests(reading: RestoreReading | None, definition: BootChecksDefinition, now: datetime) -> Result:
    """A backup never restored is not a backup (OPS-0009): a failed, old or missing restore test is to do again."""

    if reading is None:
        return _skipped("restore_tests", "restore tests were not read")

    if reading.reason:
        return Result("restore_tests", UNKNOWN, f"not read: {reading.reason}")

    if not reading.declared or not reading.tests:
        return _skipped("restore_tests", "no restore test declared")

    if not reading.gaps:
        return _passes("restore_tests", f"{reading.tests} restore test(s) within their limit")

    lines = []

    for gap in reading.gaps:
        if gap.reason == "failed":
            lines.append(f"{gap.service}: the last restore test failed")
        elif gap.reason == "untested":
            lines.append(f"{gap.service}: never tested")
        elif gap.tested_at is not None:
            lines.append(f"{gap.service}: last restore test {max(0, math.ceil((now - gap.tested_at).total_seconds() / 86400))} day(s) ago (limit {math.floor(gap.max_age_days)} day(s))")

    lines.append("to do: redo the restore tests above (a backup that was never restored is not a backup)")
    finding = "restore_test_failed" if any(gap.reason == "failed" for gap in reading.gaps) else "restore_test_old"
    summary = f"{len(reading.gaps)} of {reading.tests} restore test(s) to redo"
    failed = _fails("restore_tests", finding, summary, tuple(lines), definition, True)

    return failed if failed is not None else _skipped("restore_tests", "restore test findings are ignored")


def _expiries(
    control: str,
    kind: str,
    declared: bool,
    found: tuple[Expiry, ...] | None,
    soon: int,
    urgent: int,
    definition: BootChecksDefinition,
    now: datetime,
) -> Result:
    """
    What expires (O7): a certificate or a domain ending within `soon` days is to watch, within `urgent` days or past is to fix,
    one that could not be read is *not read*, never a good date, and one that is read but not to be trusted is to watch.
    """

    if not declared:
        return _skipped(control, f"no {kind} declared")

    if found is None:
        return _skipped(control, f"{kind}s were not read")

    ending: list[tuple[float, str]] = []
    untrusted: list[str] = []
    unread: list[str] = []
    levels: set[str] = set()
    nearest: float | None = None

    for item in found:
        if item.ends is None:
            unread.append(f"{item.name}: not read: {item.reason}")
            continue

        left = (item.ends - now).total_seconds() / 86400
        nearest = left if nearest is None else min(nearest, left)
        day = item.ends.strftime("%Y-%m-%d")

        if left < 0:
            ending.append((left, f"{item.name}: ended {math.ceil(-left)} day(s) ago ({day})"))
            levels.add("urgent")
        elif left <= soon:
            ending.append((left, f"{item.name}: ends in {math.floor(left)} day(s) ({day})"))
            levels.add("urgent" if left <= urgent else "soon")

        if item.problem:
            untrusted.append(f"{item.name}: not trusted: {item.problem}")
            levels.add("invalid")

    if levels:
        wrong = "urgent" if "urgent" in levels else "soon" if "soon" in levels else "invalid"
        action = {
            "certificate": "to do: renew the certificates above (check the renewal job and its last log)",
            "domain": "to do: renew the domains above at your registrar (and check that the automatic renewal is on)",
        }[kind]
        lines = (*(line for _, line in sorted(ending)), *untrusted, *unread, *((action,) if ending else ()))
        failed = _fails(control, f"{kind}_{wrong}", f"{len(ending)} {kind}(s) to renew" if ending else f"{len(untrusted)} {kind}(s) not trusted", lines, definition, True)

        return failed if failed is not None else _skipped(control, f"{kind} findings are ignored")

    if unread:
        return Result(control, UNKNOWN, f"{len(unread)} declared {kind}(s) not read", tuple(unread))

    return _passes(control, f"{len(found)} {kind}(s) valid, the nearest ends in {math.floor(nearest or 0)} day(s)")


def _reading(control: str, finding: str, name: str, reading: Reading | None, definition: BootChecksDefinition, settled: bool) -> Result | None:
    if reading is None:
        return _skipped(control, f"{name} was not read")

    if not reading.instrumented:
        return _skipped(control, reading.note or f"{name} is not instrumented on this host")

    if reading.findings:
        return _fails(control, finding, f"{reading.findings} finding(s) in the {name} domain", (), definition, settled)

    return _passes(control, f"nothing to report in the {name} domain")


def _recurrence(reading: RecurrenceReading | None, definition: BootChecksDefinition) -> Result:
    """
    What comes back (O3): a control that began to fail again at `recurrence_starts` distinct starts or more within
    `recurrence_days` days. To watch while one of them fails now, *said* (information) when they are all quiet at present.
    Nothing recorded yet is not "nothing came back": the control says so rather than pass.
    """

    if reading is None:
        return _skipped("recurrence", "the history was not read")

    if not reading.since:
        return Result("recurrence", INFORMATION, "no change recorded yet, nothing to compare")

    if not reading.found:
        return _passes("recurrence", f"no anomaly came back at {reading.starts} starts or more since {reading.since}")

    lines = [
        f"{item.control}: back at {item.starts} starts in {reading.days} days, the last on {item.last}" + (", failing now" if item.open else "")
        for item in reading.found
    ]
    lines.append("to do: find what brings them back at each start, rather than correcting the same symptom again")

    if not any(item.open for item in reading.found):
        return Result("recurrence", INFORMATION, f"{len(reading.found)} anomaly(ies) came back at several starts, none now", tuple(lines[:MAX_DETAILS]))

    failed = _fails("recurrence", "anomaly_recurring", f"{len(reading.found)} anomaly(ies) came back at several starts", tuple(lines), definition, True)

    return failed if failed is not None else _skipped("recurrence", "recurrence findings are ignored")


def evaluate(
    facts: BootFacts,
    definition: BootChecksDefinition,
    now: datetime,
    storage: Reading | None = None,
    backup: Reading | None = None,
    monitors: MonitorReading | None = None,
    disks: DiskReading | None = None,
    systems: SystemsReading | None = None,
    usage: UsageReading | None = None,
    restore: RestoreReading | None = None,
    expiry: ExpiryReading | None = None,
    recurrence: RecurrenceReading | None = None,
) -> list[Result]:
    """Every control of the base set, in a stable order."""

    settled = facts.booted_at is None or now - facts.booted_at >= timedelta(minutes=definition.settle_minutes)
    singles: list[Callable[[BootFacts, BootChecksDefinition, bool], Result | None]] = [_failed_units, _mounts]
    results: list[Result | None] = [check(facts, definition, settled) for check in singles]
    results.extend(_containers(facts, definition, settled))

    for check in (_docker_user, _probes, _kvm, _ups):
        results.append(check(facts, definition, settled))

    results.append(_monitors(monitors, definition, settled))
    results.append(_disks(disks, definition, now))
    results.append(_systems(systems, definition))
    results.append(_disk_trend(systems, definition, now))
    results.append(_data_disks(usage, definition, now))
    results.append(_reading("storage", "storage_low", "storage", storage, definition, settled))
    results.append(_reading("backup", "backup_late", "backup", backup, definition, settled))
    results.append(_copies(facts, definition, now))
    results.append(_restore_tests(restore, definition, now))
    results.append(
        _expiries("certificates", "certificate", bool(definition.certificates), expiry.certificates if expiry else None, definition.certificate_days, definition.certificate_urgent_days, definition, now)
    )
    results.append(
        _expiries("domains", "domain", bool(definition.domains), expiry.domains if expiry else None, definition.domain_days, definition.domain_urgent_days, definition, now)
    )
    results.append(_previous_boot(facts))
    results.append(_recurrence(recurrence, definition))

    return [result for result in results if result is not None]

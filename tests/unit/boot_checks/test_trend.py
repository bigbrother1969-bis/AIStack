"""How fast the system disks fill, from what Beszel measured (ADR-0032, slice O4)."""

from __future__ import annotations

from datetime import datetime, timedelta

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.boot_checks.controls import CRITICAL, INFORMATION, OK, SKIPPED, UNKNOWN, WARNING, Reading, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.phrases import say
from aistack.boot_checks.systems import SystemsReading, read_systems
from aistack.boot_checks.trend import DiskPoint, trend_of
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import DEFINITION, LATER, facts
from tests.unit.boot_checks.test_systems import _serve, machine

NOW = LATER


def line(days: float, per_day: float, start: float = 100.0, total: float = 200.0, step_hours: int = 8, until: datetime = NOW) -> tuple[DiskPoint, ...]:
    """Points every `step_hours` over `days` days, ending at `until`, the used space growing `per_day` GB a day."""

    count = int(days * 24 / step_hours)
    moments = [until - timedelta(hours=step_hours * (count - index)) for index in range(count + 1)]
    first = moments[0]

    return tuple(DiskPoint(moment, total, start + per_day * (moment - first).total_seconds() / 86400) for moment in moments)


def judged(reading: SystemsReading | None, definition: BootChecksDefinition = DEFINITION) -> Result | None:
    results = evaluate(facts(), definition, NOW, Reading(True, 0), Reading(True, 0), None, None, reading)

    return {result.control: result for result in results}.get("disk_trend")


def reading(*machines: tuple[str, str, tuple[DiskPoint, ...]]) -> SystemsReading:
    systems = tuple(machine(name, status=status) for name, status, _ in machines)

    return SystemsReading(True, "", systems, tuple((name, points) for name, _, points in machines))


def test_a_disk_that_grows_steadily_gives_its_rate_and_the_days_left() -> None:
    found = trend_of(line(10, 2.0), NOW, 14, 7)

    assert found is not None
    assert abs(found.rate - 2.0) < 1e-6
    assert found.days_to_full is not None and abs(found.days_to_full - (200 - found.used) / 2.0) < 1e-6
    assert found.total == 200.0


def test_a_flat_or_emptying_disk_is_never_full_and_a_far_horizon_is_not_said() -> None:
    flat = trend_of(line(10, 0.0), NOW, 14, 7)
    emptying = trend_of(line(10, -1.5), NOW, 14, 7)
    slow = trend_of(line(10, 0.01), NOW, 14, 7)

    assert flat is not None and flat.days_to_full is None
    assert emptying is not None and emptying.days_to_full is None and emptying.rate < 0
    assert slow is not None and slow.days_to_full is None  # more than a year away


def test_without_enough_history_there_is_no_trend_and_no_guess() -> None:
    assert trend_of(line(3, 2.0), NOW, 14, 7) is None  # a span shorter than the minimum
    assert trend_of(line(10, 2.0)[:5], NOW, 14, 7) is None  # fewer than six points
    assert trend_of((), NOW, 14, 7) is None
    # the newest point is old: a machine that was silent, its series is a past one
    assert trend_of(line(10, 2.0, until=NOW - timedelta(days=3)), NOW, 14, 7) is None
    assert trend_of((DiskPoint(NOW, 0.0, 0.0),) * 8, NOW, 14, 7) is None


def test_only_the_window_counts_and_the_line_follows_the_recent_growth() -> None:
    old = tuple(DiskPoint(NOW - timedelta(days=25) + timedelta(hours=8 * n), 200.0, 20.0 + 5.0 * n) for n in range(10))
    recent = line(10, 0.5, start=150.0)
    found = trend_of(old + recent, NOW, 14, 7)

    assert found is not None and abs(found.rate - 0.5) < 1e-6


def test_a_copy_that_jumps_the_disk_once_is_a_step_not_a_trend() -> None:
    # What the Raspberry did: two jumps of tens of GB, flat before, between and after.
    flat = line(13, 0.05, start=600.0, total=916.0)
    jumped = tuple(DiskPoint(p.at, p.total, p.used + (30.0 if p.at > NOW - timedelta(days=5) else 0.0) + (55.0 if p.at > NOW - timedelta(days=12) else 0.0)) for p in flat)
    found = trend_of(jumped, NOW, 14, 7)

    assert found is not None and found.rate < 0.2 and found.days_to_full is None


def test_a_steady_growth_by_daily_steps_is_still_seen() -> None:
    stepped = tuple(DiskPoint(p.at, p.total, 100.0 + 3.0 * int((p.at - (NOW - timedelta(days=10))).total_seconds() // 86400)) for p in line(10, 0.0))
    found = trend_of(stepped, NOW, 14, 7)

    assert found is not None and 2.5 < found.rate < 3.5


def test_a_disk_that_would_be_full_within_the_declared_days_is_to_watch_with_its_figures() -> None:
    result = judged(reading(("msi", "up", line(10, 5.0, start=100.0)), ("pi", "up", line(10, 0.0))))

    assert result is not None and result.status == WARNING and result.finding == "disk_full_soon"
    assert result.summary == "2 system(s) measured; 1 full within 30 days"
    assert result.details == ("msi: about 10 day(s) left at +5.00 GB/day (150 of 200 GB)",)


def test_a_disk_that_grows_but_is_not_near_is_information_and_a_steady_one_is_fine() -> None:
    growing = judged(reading(("msi", "up", line(10, 0.5, start=100.0)), ("pi", "up", line(10, 0.0))))
    steady = judged(reading(("msi", "up", line(10, 0.0)), ("pi", "up", line(10, -0.2))))

    assert growing is not None and growing.status == INFORMATION
    assert growing.summary == "2 system(s) measured, none full within 30 days"
    assert growing.details[0].startswith("msi: about ") and "+0.50 GB/day" in growing.details[0]
    assert steady is not None and steady.status == OK and steady.summary == "2 system(s) measured, none full within 30 days"


def test_a_machine_without_enough_history_is_not_read_never_fine() -> None:
    short = judged(reading(("msi", "up", line(10, 0.0)), ("new", "up", line(2, 0.0))))
    none = judged(reading(("msi", "up", line(2, 0.0))))

    assert short is not None and short.status == UNKNOWN and short.summary == "1 system(s) measured, none full within 30 days; 1 without enough history"
    assert short.details == ("new",)
    assert none is not None and none.status == UNKNOWN and none.summary.startswith("not read: Beszel has less than 7 days")


def test_a_danger_is_not_hidden_by_a_machine_that_is_still_young() -> None:
    result = judged(reading(("msi", "up", line(10, 5.0, start=100.0)), ("new", "up", line(2, 0.0))))

    assert result is not None and result.status == WARNING and "1 without enough history" in result.summary


def test_a_machine_that_is_down_is_not_trended_and_nothing_to_trend_says_nothing() -> None:
    assert judged(reading(("gigabyte", "down", line(10, 5.0, start=190.0)))) is None
    assert judged(None) is None
    assert judged(SystemsReading(False, "Beszel did not answer")) is None


def test_the_owner_sets_the_days_the_window_and_the_weight() -> None:
    slow = reading(("msi", "up", line(10, 0.5, start=100.0)))

    assert judged(slow, BootChecksDefinition(disk_full_days=400)).status == WARNING  # type: ignore[union-attr]
    assert judged(slow, BootChecksDefinition(disk_trend_min_days=12)).status == UNKNOWN  # type: ignore[union-attr]
    assert judged(reading(("msi", "up", line(10, 5.0))), BootChecksDefinition(severity={"disk_full_soon": "critical"})).status == CRITICAL  # type: ignore[union-attr]
    ignored = judged(reading(("msi", "up", line(10, 5.0))), BootChecksDefinition(severity={"disk_full_soon": "ignore"}))

    assert ignored is not None and ignored.status == SKIPPED


def test_the_sentences_are_told_in_french_with_their_numbers() -> None:
    fr = translator_for("fr")

    assert say(fr, "2 system(s) measured; 1 full within 30 days") == "2 machine(s) mesurée(s); 1 pleine(s) d'ici 30 jours"
    assert say(fr, "2 system(s) measured, none full within 30 days") == "2 machine(s) mesurée(s), aucune pleine d'ici 30 jours"
    assert say(fr, "1 system(s) measured, none full within 30 days; 1 without enough history").endswith("1 sans assez d'historique")
    assert say(fr, "msi: about 10 day(s) left at +5.00 GB/day (150 of 200 GB)") == "msi : environ 10 jour(s) restant(s) à +5.00 Go/jour (150 sur 200 Go)"
    assert say(fr, "not read: Beszel has less than 7 days of measures for the system disks") == "non lu : Beszel a moins de 7 jours de mesures pour les disques système"


def test_the_provider_reads_the_history_of_machines_that_are_up_and_the_checks_turn_it_into_points() -> None:
    day = NOW - timedelta(days=10)
    rows = [
        {"created": (day + timedelta(hours=8 * n)).strftime("%Y-%m-%d %H:%M:%S.000Z"), "stats": {"d": 200.0, "du": 100.0 + n}}
        for n in range(30)
    ] + [{"created": "bad", "stats": "x"}]
    records = [
        {"id": "up1", "name": "msi", "status": "up", "info": {}},
        {"id": "dn1", "name": "gigabyte", "status": "down", "info": {}},
        {"id": "up2", "name": "pi", "status": "up", "info": {}},
    ]
    server, url = _serve(records, history={"up1": rows})
    handler = server.RequestHandlerClass

    try:
        found = read_systems(url, "me@example.org", "secret")
    finally:
        server.shutdown()

    history = dict(found.history)

    assert handler.history_asked == ["system='up1' && type='480m'", "system='up2' && type='480m'"]
    assert set(history) == {"msi", "pi"} and history["pi"] == ()
    assert len(history["msi"]) == 30 and history["msi"][0].at < history["msi"][-1].at
    assert history["msi"][-1].used == 129.0 and history["msi"][-1].total == 200.0
    assert isinstance(machine(), BeszelSystemReading)


def test_the_real_raspberry_series_is_not_a_trend() -> None:
    # Measured 2026-11-26: a 916 GB disk filled by copies on 14 and 21 Nov, flat since (660.95 -> 661.14 in four days).
    used = [544.2, 602.34, 628.19, 628.17, 628.11, 628.14, 628.16, 628.17, 628.18, 628.18, 628.20, 628.21, 628.21, 628.22, 628.35, 628.60, 628.69,
            628.71, 628.72, 629.20, 629.37, 643.27, 660.23, 660.24, 660.48, 660.95, 660.96, 660.97, 660.98, 660.99, 661.00, 661.01, 661.01, 661.06,
            661.11, 661.12, 661.14]
    hours = [-312, -304, -296, -288, -280, -272, -264, -256, -248, -240, -232, -224, -216, -208, -200, -192, -184, -176, -168, -160, -152, -144,
             -136, -128, -118, -110, -102, -94, -86, -78, -70, -62, -54, -46, -38, -30, -14]
    points = tuple(DiskPoint(NOW + timedelta(hours=h), 916.0, u) for h, u in zip(hours, used, strict=True))
    found = trend_of(points, NOW, 14, 7)

    assert found is not None and found.rate < 1.0 and found.days_to_full is None

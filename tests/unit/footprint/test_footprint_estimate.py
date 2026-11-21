"""The calculation: one call, three levels, a range, and what is measured told apart from what is estimated."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aistack.ai_runtime.call_journal import Call
from aistack.footprint.declaration import DEFINITION, load_footprint_yaml
from aistack.footprint.estimate import (
    BASELINE,
    DATA_CENTER_EXTERNAL,
    DATA_CENTER_LOCAL,
    NETWORK,
    TERMINAL,
    Quantity,
    Triple,
    estimate,
)

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
DECLARATION = load_footprint_yaml(DEFINITION)


def call(**changes) -> Call:
    base = dict(
        at=(NOW - timedelta(hours=2)).isoformat(), caller="portal.chat", operation="ask", language="fr",
        answered_by="qwen2.5:7b", reached_external=False, reachable=True, seconds=10.0,
    )
    return Call(**{**base, **changes})


def ordered(quantity: Quantity) -> bool:
    return (
        quantity.energy_kwh.low <= quantity.energy_kwh.central <= quantity.energy_kwh.high
        and quantity.gwp_kg.low <= quantity.gwp_kg.central <= quantity.gwp_kg.high
    )


def test_with_no_call_only_the_permanent_load_is_counted():
    result = estimate((), DECLARATION, NOW)

    assert result.calls == 0 and result.answered == 0
    assert result.levels[BASELINE].energy_kwh.central == pytest.approx(5 * 24 * 30 / 1000)
    assert result.levels[DATA_CENTER_LOCAL] == Quantity()
    assert result.per_call == Quantity()


def test_the_permanent_load_follows_the_declared_power_and_the_french_grid():
    base = estimate((), DECLARATION, NOW).levels[BASELINE]

    assert base.energy_kwh.low == pytest.approx(2 * 720 / 1000)
    assert base.energy_kwh.high == pytest.approx(10 * 720 / 1000)
    assert base.gwp_kg.central == pytest.approx(3.6 * 0.0414)


def test_a_local_call_with_a_measured_power_is_counted_as_measured():
    result = estimate((call(gpu_watts=100.0),), DECLARATION, NOW)

    assert (result.local, result.measured, result.estimated, result.outside) == (1, 1, 0, 0)


def test_a_local_call_without_a_measure_uses_the_declared_power_and_says_so():
    result = estimate((call(gpu_watts=None),), DECLARATION, NOW)

    assert (result.measured, result.estimated) == (0, 1)
    # 100 W x 1.4 x PUE 1.0 for 10 s
    assert result.levels[DATA_CENTER_LOCAL].energy_kwh.central == pytest.approx(100 * 1.4 * 10 / 3_600_000)


def test_the_low_value_of_a_measured_call_keeps_only_what_the_card_added_to_its_rest():
    local = estimate((call(gpu_watts=100.0),), DECLARATION, NOW).levels[DATA_CENTER_LOCAL]

    assert local.energy_kwh.low == pytest.approx((100 - 33.57) * 1.2 * 10 / 3_600_000)
    assert local.energy_kwh.central == pytest.approx(100 * 1.4 * 10 / 3_600_000)


def test_a_card_reading_below_its_rest_never_gives_a_negative_energy():
    local = estimate((call(gpu_watts=20.0),), DECLARATION, NOW).levels[DATA_CENTER_LOCAL]

    assert local.energy_kwh.low == 0.0


def test_the_making_of_the_machine_is_allocated_by_time_of_use():
    declaration = DECLARATION
    long = estimate((call(gpu_watts=100.0, seconds=3600.0),), declaration, NOW).levels[DATA_CENTER_LOCAL]
    short = estimate((call(gpu_watts=100.0, seconds=36.0),), declaration, NOW).levels[DATA_CENTER_LOCAL]

    assert long.gwp_kg.central == pytest.approx(short.gwp_kg.central * 100)
    making = 350 * 3600 / (5 * 8766 * 3600)
    assert long.gwp_kg.central > making


def test_an_outside_call_costs_the_published_energy_at_the_providers_grid():
    result = estimate((call(reached_external=True, answered_by="gemini:gemini-3.5-flash-lite", seconds=3.0),), DECLARATION, NOW)
    outside = result.levels[DATA_CENTER_EXTERNAL]

    assert (result.outside, result.local) == (1, 0)
    assert outside.energy_kwh.low == pytest.approx(0.24 / 1000)
    assert outside.energy_kwh.high == pytest.approx(3.0 / 1000)
    assert outside.gwp_kg.central == pytest.approx(0.3 / 1000 * 0.384)
    assert result.levels[NETWORK].energy_kwh.central > 0
    assert result.levels[DATA_CENTER_LOCAL] == Quantity()


def test_a_local_call_uses_no_outside_network():
    result = estimate((call(gpu_watts=90.0),), DECLARATION, NOW)

    assert result.levels[NETWORK] == Quantity()


def test_the_terminal_is_counted_only_for_a_caller_somebody_waits_on():
    asked = estimate((call(caller="portal.chat"),), DECLARATION, NOW).levels[TERMINAL]
    background = estimate((call(caller="vigil.reason"),), DECLARATION, NOW).levels[TERMINAL]

    assert asked.energy_kwh.central == pytest.approx(15 * 10 / 3_600_000)
    assert background == Quantity()


def test_a_call_nothing_answered_is_counted_in_usage_and_not_in_energy():
    result = estimate((call(reachable=False, answered_by=""),), DECLARATION, NOW)

    assert (result.calls, result.answered, result.unanswered) == (1, 0, 1)
    assert result.calls_only == Quantity()
    assert result.seconds == 10.0


def test_only_the_calls_of_the_period_are_counted():
    old = call(at=(NOW - timedelta(days=31)).isoformat())
    recent = call(at=(NOW - timedelta(days=29)).isoformat())
    broken = call(at="not a date")

    assert estimate((old, recent, broken), DECLARATION, NOW).calls == 1


def test_a_date_without_a_time_zone_is_read_as_utc():
    assert estimate((call(at="2026-11-20T10:00:00"),), DECLARATION, NOW).calls == 1


def test_the_calls_are_listed_by_caller_and_by_day():
    calls = (
        call(caller="portal.chat", gpu_watts=95.0),
        call(caller="portal.chat", reached_external=True),
        call(caller="vigil.reason", at=(NOW - timedelta(days=3)).isoformat()),
    )
    result = estimate(calls, DECLARATION, NOW)

    assert result.by_caller_calls == {"portal.chat": 2, "vigil.reason": 1}
    assert [(d.day, d.calls, d.outside) for d in result.days] == [("2026-11-18", 1, 0), ("2026-11-21", 2, 1)]
    assert set(result.by_caller) == {"portal.chat", "vigil.reason"}


def test_the_per_call_figure_is_the_calls_only_average_without_the_permanent_load():
    result = estimate((call(gpu_watts=95.0), call(gpu_watts=95.0)), DECLARATION, NOW)

    assert result.per_call.energy_kwh.central == pytest.approx(result.calls_only.energy_kwh.central / 2)
    assert result.total.energy_kwh.central == pytest.approx(
        result.calls_only.energy_kwh.central + result.levels[BASELINE].energy_kwh.central
    )


def test_the_low_value_never_exceeds_the_central_and_the_central_never_exceeds_the_high():
    calls = (
        call(gpu_watts=95.0),
        call(gpu_watts=None, seconds=40.0),
        call(reached_external=True, caller="troubleshooting"),
        call(caller="vigil.reason", gpu_watts=70.0),
    )
    result = estimate(calls, DECLARATION, NOW)

    for quantity in (*result.levels.values(), *result.by_caller.values(), result.total, result.per_call):
        assert ordered(quantity)


def test_triples_add_and_scale():
    assert Triple(1, 2, 3) + Triple(1, 1, 1) == Triple(2, 3, 4)
    assert Triple(1, 2, 3).times(2) == Triple(2, 4, 6)
    assert Triple(1, 2, 3).at("central") == 2

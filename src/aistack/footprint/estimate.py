"""
The calculation (`ADR-0030`): from the journal of AI calls and the declared inputs to energy and greenhouse
gases, by level, each with a low, a central and a high value. Pure: it reads nothing and writes nothing.

The unit is one call to an AI engine, from the click to the answer, and three levels are counted for it:
the machine that answers (the data centre: the home machine for a local engine, the provider's for an
outside one), the network, and the terminal of the person who waits. Equipment is allocated by time of use:
a call carries the share of the machine's making that its duration is of the machine's life. The permanent
load of AIStack's containers, which no call explains, is counted apart.

What a figure rests on is told by the declaration (`measured`, `sourced`, `declared`) and by the counts of
calls measured and calls estimated that the result carries.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from aistack.ai_runtime.call_journal import Call
from aistack.footprint.declaration import CENTRAL, HIGH, LOW, SCENARIOS, Footprint

SECONDS_PER_YEAR = 8766 * 3600

# The levels, in the order a page lists them.
DATA_CENTER_LOCAL = "data_center_local"
DATA_CENTER_EXTERNAL = "data_center_external"
NETWORK = "network"
TERMINAL = "terminal"
BASELINE = "baseline"
LEVELS = (DATA_CENTER_LOCAL, DATA_CENTER_EXTERNAL, NETWORK, TERMINAL, BASELINE)


@dataclass(frozen=True)
class Triple:
    low: float = 0.0
    central: float = 0.0
    high: float = 0.0

    def __add__(self, other: "Triple") -> "Triple":
        return Triple(self.low + other.low, self.central + other.central, self.high + other.high)

    def times(self, factor: float) -> "Triple":
        return Triple(self.low * factor, self.central * factor, self.high * factor)

    def at(self, scenario: str) -> float:
        return {LOW: self.low, CENTRAL: self.central, HIGH: self.high}[scenario]


@dataclass(frozen=True)
class Quantity:
    """One level or one total, in kWh of final energy and in kgCO2e (GWP at 100 years)."""

    energy_kwh: Triple = Triple()
    gwp_kg: Triple = Triple()

    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.energy_kwh + other.energy_kwh, self.gwp_kg + other.gwp_kg)

    def times(self, factor: float) -> "Quantity":
        return Quantity(self.energy_kwh.times(factor), self.gwp_kg.times(factor))


@dataclass(frozen=True)
class Day:
    day: str
    calls: int
    outside: int


@dataclass
class Result:
    period_days: int
    calls: int = 0
    answered: int = 0
    unanswered: int = 0
    local: int = 0
    outside: int = 0
    measured: int = 0  # local calls whose GPU power was read
    estimated: int = 0  # local calls priced from the declared power
    seconds: float = 0.0
    levels: dict[str, Quantity] = field(default_factory=dict)
    by_caller: dict[str, Quantity] = field(default_factory=dict)
    by_caller_calls: dict[str, int] = field(default_factory=dict)
    days: tuple[Day, ...] = ()

    @property
    def total(self) -> Quantity:
        total = Quantity()

        for quantity in self.levels.values():
            total = total + quantity

        return total

    @property
    def calls_only(self) -> Quantity:
        """Everything but the permanent load: what the calls are responsible for."""

        total = Quantity()

        for level, quantity in self.levels.items():
            if level != BASELINE:
                total = total + quantity

        return total

    @property
    def per_call(self) -> Quantity:
        return self.calls_only.times(1 / self.answered) if self.answered else Quantity()


def _kwh(watts: float, seconds: float) -> float:
    return watts * seconds / 3_600_000


def _per_scenario(build) -> Quantity:  # type: ignore[no-untyped-def]
    """A quantity from a function of the scenario returning (kWh, kgCO2e)."""

    values = {scenario: build(scenario) for scenario in SCENARIOS}

    return Quantity(
        Triple(*(values[s][0] for s in SCENARIOS)),
        Triple(*(values[s][1] for s in SCENARIOS)),
    )


def _local_machine(call: Call, declaration: Footprint) -> Quantity:
    idle = declaration.get("gpu_idle_watts")
    active = declaration.get("gpu_active_watts")
    overhead = declaration.get("host_overhead_ratio")
    pue = declaration.get("pue_local")
    grid = declaration.get("grid_local")
    embodied = declaration.get("embodied_host")
    lifetime = declaration.get("host_lifetime_years")

    def build(scenario: str) -> tuple[float, float]:
        if call.gpu_watts is None:
            watts = active.at(scenario)
        elif scenario == LOW:
            # The low value keeps only what the call added to the idle card.
            watts = max(call.gpu_watts - idle.at(scenario), 0.0)
        else:
            watts = call.gpu_watts

        energy = _kwh(watts * (1 + overhead.at(scenario)) * pue.at(scenario), call.seconds)
        making = embodied.at(scenario) * call.seconds / (lifetime.at(scenario) * SECONDS_PER_YEAR)

        return energy, energy * grid.at(scenario) + making

    return _per_scenario(build)


def _external_machine(declaration: Footprint) -> Quantity:
    energy = declaration.get("external_energy_per_call")
    grid = declaration.get("grid_external")

    # The published figure already carries the overhead of the data centre and the idle machines.
    return _per_scenario(lambda s: (energy.at(s) / 1000, energy.at(s) / 1000 * grid.at(s)))


def _network(declaration: Footprint) -> Quantity:
    per_gb = declaration.get("network_kwh_per_gb")
    megabytes = declaration.get("external_exchange_mb")
    grid = declaration.get("grid_local")

    return _per_scenario(
        lambda s: (per_gb.at(s) * megabytes.at(s) / 1000, per_gb.at(s) * megabytes.at(s) / 1000 * grid.at(s))
    )


def _terminal(call: Call, declaration: Footprint) -> Quantity:
    watts = declaration.get("terminal_watts")
    grid = declaration.get("grid_local")

    return _per_scenario(lambda s: (_kwh(watts.at(s), call.seconds), _kwh(watts.at(s), call.seconds) * grid.at(s)))


def _baseline(declaration: Footprint) -> Quantity:
    watts = declaration.get("baseline_watts")
    grid = declaration.get("grid_local")
    hours = declaration.period_days * 24

    return _per_scenario(lambda s: (watts.at(s) * hours / 1000, watts.at(s) * hours / 1000 * grid.at(s)))


def _when(call: Call) -> datetime | None:
    try:
        moment = datetime.fromisoformat(call.at)
    except ValueError:
        return None

    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def estimate(calls: tuple[Call, ...], declaration: Footprint, now: datetime | None = None) -> Result:
    """The footprint of the calls of the last `period_days` days and of the permanent load over the same days."""

    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=declaration.period_days)
    result = Result(period_days=declaration.period_days)
    levels: dict[str, Quantity] = {level: Quantity() for level in LEVELS}
    by_caller: dict[str, Quantity] = defaultdict(Quantity)
    by_calls: dict[str, int] = defaultdict(int)
    per_day: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    outside_unit = _external_machine(declaration)
    network_unit = _network(declaration)

    for call in calls:
        moment = _when(call)

        if moment is None or moment < since or moment > now + timedelta(days=1):
            continue

        result.calls += 1
        result.seconds += call.seconds
        by_calls[call.caller] += 1
        counts = per_day[moment.astimezone(timezone.utc).date().isoformat()]
        counts[0] += 1
        counts[1] += 1 if call.reached_external else 0

        if not call.reachable:
            # Nothing answered: no answer to carry a footprint. The count says so.
            result.unanswered += 1
            continue

        result.answered += 1
        mine = Quantity()

        if call.reached_external:
            result.outside += 1
            levels[DATA_CENTER_EXTERNAL] = levels[DATA_CENTER_EXTERNAL] + outside_unit
            levels[NETWORK] = levels[NETWORK] + network_unit
            mine = mine + outside_unit + network_unit
        else:
            result.local += 1

            if call.gpu_watts is None:
                result.estimated += 1
            else:
                result.measured += 1

            machine = _local_machine(call, declaration)
            levels[DATA_CENTER_LOCAL] = levels[DATA_CENTER_LOCAL] + machine
            mine = mine + machine

        if call.caller in declaration.terminal_callers:
            terminal = _terminal(call, declaration)
            levels[TERMINAL] = levels[TERMINAL] + terminal
            mine = mine + terminal

        by_caller[call.caller] = by_caller[call.caller] + mine

    levels[BASELINE] = _baseline(declaration)
    result.levels = levels
    result.by_caller = dict(by_caller)
    result.by_caller_calls = dict(by_calls)
    result.days = tuple(Day(day, c[0], c[1]) for day, c in sorted(per_day.items()))

    return result

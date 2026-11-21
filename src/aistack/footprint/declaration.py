"""
`footprint.yml`: the inputs of the calculation, each with its three values, its unit and where it comes from.
A file that misses a parameter, a value or a source is refused with the name of what is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from aistack.config import configured

DEFINITION = Path(__file__).resolve().parent / "definitions" / "footprint.yml"

LOW, CENTRAL, HIGH = "low", "central", "high"
SCENARIOS = (LOW, CENTRAL, HIGH)
STATUSES = ("measured", "sourced", "declared")

REQUIRED = (
    "grid_local",
    "grid_external",
    "gpu_idle_watts",
    "gpu_active_watts",
    "host_overhead_ratio",
    "pue_local",
    "embodied_host",
    "host_lifetime_years",
    "external_energy_per_call",
    "terminal_watts",
    "network_kwh_per_gb",
    "external_exchange_mb",
    "baseline_watts",
)


@dataclass(frozen=True)
class Parameter:
    name: str
    unit: str
    low: float
    central: float
    high: float
    status: str
    source: str

    def at(self, scenario: str) -> float:
        return {LOW: self.low, CENTRAL: self.central, HIGH: self.high}[scenario]


@dataclass(frozen=True)
class Method:
    reference: str
    functional_unit: str
    computed: tuple[str, ...]
    not_computed: tuple[str, ...]


@dataclass(frozen=True)
class Footprint:
    method: Method
    period_days: int
    terminal_callers: tuple[str, ...]
    parameters: tuple[Parameter, ...]

    def get(self, name: str) -> Parameter:
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter

        raise KeyError(name)


def load_footprint_yaml(path: Path | None = None) -> Footprint:
    """Read `footprint.yml`; raises `ValueError` saying what is wrong."""

    path = path or configured(DEFINITION)

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"footprint.yml cannot be read: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("footprint.yml must be a mapping")

    method = data.get("method")

    if not isinstance(method, dict) or not str(method.get("reference") or "").strip():
        raise ValueError("footprint.yml: `method.reference` is missing")

    if not str(method.get("functional_unit") or "").strip():
        raise ValueError("footprint.yml: `method.functional_unit` is missing")

    period = data.get("period_days")

    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("footprint.yml: `period_days` must be a whole number of days, at least 1")

    callers = data.get("terminal_callers", [])

    if not isinstance(callers, list) or not all(isinstance(item, str) and item.strip() for item in callers):
        raise ValueError("footprint.yml: `terminal_callers` must be a list of names")

    raw = data.get("parameters")

    if not isinstance(raw, dict):
        raise ValueError("footprint.yml: `parameters` is missing")

    parameters: list[Parameter] = []

    for name in REQUIRED:
        entry = raw.get(name)

        if not isinstance(entry, dict):
            raise ValueError(f"footprint.yml: parameter `{name}` is missing")

        values: dict[str, float] = {}

        for scenario in SCENARIOS:
            value = entry.get(scenario)

            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"footprint.yml: `{name}.{scenario}` must be a number, zero or more")

            values[scenario] = float(value)

        if entry.get("status") not in STATUSES:
            raise ValueError(f"footprint.yml: `{name}.status` must be one of {', '.join(STATUSES)}")

        if not str(entry.get("source") or "").strip():
            raise ValueError(f"footprint.yml: `{name}.source` says nothing: a figure needs its source")

        if name == "host_lifetime_years" and 0 in values.values():
            raise ValueError("footprint.yml: `host_lifetime_years` cannot be zero")

        parameters.append(
            Parameter(
                name=name,
                unit=str(entry.get("unit") or ""),
                low=values[LOW],
                central=values[CENTRAL],
                high=values[HIGH],
                status=str(entry["status"]),
                source=" ".join(str(entry["source"]).split()),
            )
        )

    return Footprint(
        method=Method(
            reference=str(method["reference"]),
            functional_unit=str(method["functional_unit"]),
            computed=tuple(str(item) for item in method.get("computed") or ()),
            not_computed=tuple(str(item) for item in method.get("not_computed") or ()),
        ),
        period_days=period,
        terminal_callers=tuple(callers),
        parameters=tuple(parameters),
    )

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.pra_test_reading import PraTestReading
from aistack.contracts.pra_test_threshold import (
    PraTestThreshold,
    PraTestThresholdRegister,
)

_REQUIRED_SERVICE_FIELDS = ("name",)
_REQUIRED_LAST_TEST_FIELDS = ("status", "date")


def load_pra_tests_yaml(
    path: Path,
) -> tuple[tuple[PraTestReading, ...], PraTestThresholdRegister]:
    """
    Load the declared PRA test records (OPS-0009): one reading per service and its threshold.

    The file is hand-written and read-only, so a missing key raises a
    ValueError naming it and where. `max_age_days` is one value applied
    to every service. `observed_at` is the time of this call.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(
                f"PRA test definition {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(f"PRA test definition must contain a mapping: {path}")

    if "max_age_days" not in data:
        raise ValueError(f"PRA test definition {path} is missing: max_age_days")

    if "services" not in data:
        raise ValueError(f"PRA test definition {path} is missing: services")

    max_age_days = float(data["max_age_days"])
    services_data = data["services"]

    if not isinstance(services_data, list):
        raise ValueError(f"PRA test definition {path}: services must be a list")

    observed_at = datetime.now(timezone.utc)

    readings: list[PraTestReading] = []
    thresholds: list[PraTestThreshold] = []

    for index, item in enumerate(services_data):
        reading = _load_service(item, path, index, observed_at)
        readings.append(reading)
        thresholds.append(
            PraTestThreshold(service=reading.service, max_age_days=max_age_days)
        )

    return tuple(readings), PraTestThresholdRegister(thresholds=tuple(thresholds))


def _load_service(
    data: Any, path: Path, index: int, observed_at: datetime
) -> PraTestReading:
    label = f"PRA test definition {path}: services[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_SERVICE_FIELDS, label)

    last_test = data.get("last_test")

    if last_test is None:
        return PraTestReading(service=data["name"], observed_at=observed_at)

    if not isinstance(last_test, dict):
        raise ValueError(f"{label}.last_test must be a mapping, or null")

    test_label = f"{label}.last_test"
    _require(last_test, _REQUIRED_LAST_TEST_FIELDS, test_label)

    try:
        tested_at = datetime.strptime(
            str(last_test["date"]), "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ValueError(
            f"{test_label}.date {last_test['date']!r} is not a YYYY-MM-DD "
            f"date: {error}"
        ) from error

    rto_minutes = last_test.get("rto_minutes")

    return PraTestReading(
        service=data["name"],
        observed_at=observed_at,
        status=last_test["status"],
        tested_at=tested_at,
        rto_minutes=int(rto_minutes) if rto_minutes is not None else None,
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")

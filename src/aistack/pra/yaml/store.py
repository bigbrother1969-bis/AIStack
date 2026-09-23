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
    Load `OPS-0009`'s declared PRA test records from YAML: every
    service this render checks, and each one's own last-known
    restore-test outcome.

    Mirrors `load_backup_thresholds_yaml`/`load_console_links_yaml`
    field for field (written by hand, read-only — every value here is
    the owner's own declared record, `OPS-0009` § *Declared services
    and threshold* — so a missing key is a typo, and the error names
    which one and where; nothing writes this file back).

    **Two results, not one**, unlike `load_console_links_yaml`: this
    file declares both the reading (`services[].last_test`, this
    render's own observation of what the owner last recorded) and the
    threshold every service is checked against (`max_age_days`, one
    flat value for all — the owner's own choice, 2026-09-23, over a
    per-service value `PraTestThreshold` still leaves room for). Both
    are read from the one file in one call, the same "load once, use
    twice" shape `aistack.cli.health_render.build_cockpit` already
    expects of every other domain's own loader.

    `observed_at` is stamped as this call is made — the same "as of
    the last render" convention `BackupProvider.collect_freshness`
    already holds, even though nothing here is actually collected
    live.
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

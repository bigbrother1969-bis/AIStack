from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from aistack.contracts.pra_test_gap import (
    FAILED_REASON,
    NOT_DECLARED,
    STALE,
    UNTESTED,
    PraTestGap,
)
from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading
from aistack.contracts.pra_test_threshold import PraTestThreshold


def find_pra_test_gaps(
    readings: Sequence[PraTestReading],
    thresholds: Sequence[PraTestThreshold],
) -> tuple[PraTestGap, ...]:
    """
    Return the declared services that fail their `OPS-0009` check: never
    tested, last test failed, or last success older than `max_age_days`.

    A reading for a service with no declared threshold is skipped, not
    treated as healthy.
    """

    by_service = {threshold.service: threshold for threshold in thresholds}

    gaps: list[PraTestGap] = []

    for reading in readings:
        threshold = by_service.get(reading.service)

        if threshold is None:
            continue

        if reading.status is None:
            gaps.append(
                PraTestGap(
                    reading=reading,
                    max_age_days=threshold.max_age_days,
                    reason=UNTESTED,
                )
            )
            continue

        if reading.status == FAILED:
            gaps.append(
                PraTestGap(
                    reading=reading,
                    max_age_days=threshold.max_age_days,
                    reason=FAILED_REASON,
                )
            )
            continue

        # Only SUCCESS remains here, which implies `tested_at` is set; check it
        # explicitly so mypy can narrow the type.
        if reading.status != SUCCESS or reading.tested_at is None:
            continue

        age_days = (
            reading.observed_at - reading.tested_at
        ).total_seconds() / 86400

        if age_days > threshold.max_age_days:
            gaps.append(
                PraTestGap(
                    reading=reading,
                    max_age_days=threshold.max_age_days,
                    reason=STALE,
                )
            )

    return tuple(gaps)


def find_undeclared_pra_tests(
    stateful_services: Sequence[str],
    declared_services: Sequence[str],
    thresholds: Sequence[PraTestThreshold],
    observed_at: datetime,
) -> tuple[PraTestGap, ...]:
    """
    Return a NOT_DECLARED gap for each stateful service (`has_state: true`
    in `backup_strategy.yml`) that `pra_tests.yml` does not list.

    Checked in one direction only: a `pra_tests.yml` entry with no stateful
    counterpart (e.g. a host tested by imaging) is not flagged. Each gap
    carries `status=None`, never an invented test date, and the shared flat
    `max_age_days`. With no thresholds declared at all, returns no gaps.
    """

    if not thresholds:
        return ()

    max_age_days = thresholds[0].max_age_days
    declared = set(declared_services)

    gaps: list[PraTestGap] = []

    for service in sorted(set(stateful_services)):
        if service in declared:
            continue

        gaps.append(
            PraTestGap(
                reading=PraTestReading(service=service, observed_at=observed_at),
                max_age_days=max_age_days,
                reason=NOT_DECLARED,
            )
        )

    return tuple(gaps)

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.pra_test_gap import (
    FAILED_REASON,
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
    Which declared services have failed the check `OPS-0009` declares
    for them: never tested, a test already recorded as failed, or a
    successful test now older than the declared threshold allows.

    Mirrors `find_backup_gaps`: given readings already loaded and
    thresholds already declared, decides which ones actually fail —
    it never proposes a threshold itself.

    A reading for a service with no declared threshold is silently
    not evaluated, not treated as healthy — the same "not measured is
    not zero" convention `find_backup_gaps` already holds for a path
    `OPS-0006` has not been asked about yet.

    Pure: readings and thresholds already loaded in, gaps out — the
    same discipline `find_backup_gaps` already holds.
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

        # `reading.status not in (None, FAILED)` leaves only `SUCCESS`
        # (`PraTestReading.__post_init__` restricts `status` to
        # `STATUSES`), which in turn guarantees `tested_at is not
        # None` — but that guarantee lives on a different type, so
        # mypy cannot see it from here. Checking `tested_at` directly,
        # rather than asserting past it, narrows it for the rest of
        # this branch without a bare `assert` — the same choice
        # `evaluate_backup._interpretation` already makes.
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

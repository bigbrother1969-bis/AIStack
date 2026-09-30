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


def find_undeclared_pra_tests(
    stateful_services: Sequence[str],
    declared_services: Sequence[str],
    thresholds: Sequence[PraTestThreshold],
    observed_at: datetime,
) -> tuple[PraTestGap, ...]:
    """
    1.6 tranche 4's own gap (R9, 2026-09-30, `OPS-0004`'s eighth
    reference case): which services `OPS-0010`'s own declared record
    (`backup_strategy.yml`, `has_state: true`) already names stateful,
    but `OPS-0009`'s own declared record (`pra_tests.yml`) does not
    name at all — one step further upstream than `UNTESTED`, which
    already requires a `services:` entry to exist.

    Sorted, deduplicated service names only — the owner's own choice
    at cadrage (2026-09-30): checked in one direction only. A
    `pra_tests.yml` entry with no `has_state: true` counterpart (a
    host-level entry like `gigabyte`/`raspberry`, tested by imaging
    rather than by service) is never flagged the other way — that
    would be a false positive, not a real gap (`ARC-P-006`).

    **Never a fabricated `last_test`.** Each synthesized
    `PraTestReading` carries `status=None` — the roadmap's own words,
    "résultats seulement issus de vrais tests" — and the same
    `max_age_days` every currently-declared service already shares
    (`OPS-0009`'s one flat threshold, not a value invented for a
    service that is not declared yet).

    A missing threshold register (`pra_tests.yml` declares no service
    at all) yields no gaps here — there is no real flat threshold to
    attribute, the same "not measured is not zero" convention
    `find_pra_test_gaps` already holds for a path with no declared
    threshold. This has no real precedent in the owner's own declared
    file today (`ARC-P-006`: not built further than that).

    Pure: the two service-name sets, the thresholds already loaded,
    and one `observed_at` moment in, gaps out — the same discipline
    `find_pra_test_gaps` already holds.
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

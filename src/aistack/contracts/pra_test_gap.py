from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading

# Closed set of reasons: never tested, test failed, success older than
# OPS-0009 allows, or a service OPS-0010 declares stateful that is
# missing from the restore-test file altogether.
UNTESTED = "untested"
STALE = "stale"
FAILED_REASON = "failed"
NOT_DECLARED = "not_declared"

REASONS = (UNTESTED, STALE, FAILED_REASON, NOT_DECLARED)


@dataclass(frozen=True)
class PraTestGap:
    """
    A service that failed its OPS-0009 restore-test check. The
    constructor checks the reason against the reading.

    `NOT_DECLARED` carries a reading built by
    `aistack.runtime.pra_test_gap.find_undeclared_pra_tests` with
    `status=None`; only `reason` tells it apart from `UNTESTED`.
    `FAILED_REASON` applies at once, with no age check.

    `max_age_days` is the threshold that governed the service at the
    time, carried for every reason.
    """

    reading: PraTestReading
    max_age_days: float
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise ValueError(
                f"{self.reading.service} cites {self.reason!r} as a PRA "
                f"test gap reason; only {REASONS} are detected in this "
                f"scope"
            )

        if self.reason == UNTESTED and self.reading.status is not None:
            raise ValueError(
                f"{self.reading.service} cites 'untested' but its own "
                f"reading reports a last test status of "
                f"{self.reading.status!r}"
            )

        if self.reason == NOT_DECLARED and self.reading.status is not None:
            raise ValueError(
                f"{self.reading.service} cites 'not_declared' but its own "
                f"reading reports a last test status of "
                f"{self.reading.status!r} — a service with a real recorded "
                f"outcome is already declared, that is not this reason"
            )

        if self.reason == FAILED_REASON:
            if self.reading.status != FAILED:
                raise ValueError(
                    f"{self.reading.service} cites 'failed' but its own "
                    f"reading reports a last test status of "
                    f"{self.reading.status!r}, not {FAILED!r}"
                )

        if self.reason == STALE:
            if self.reading.status != SUCCESS or self.reading.tested_at is None:
                raise ValueError(
                    f"{self.reading.service} cites 'stale' but its own "
                    f"reading does not report a successful, dated test — "
                    f"that is 'untested' or 'failed', not 'stale'"
                )

            age_days = (
                self.reading.observed_at - self.reading.tested_at
            ).total_seconds() / 86400

            if age_days <= self.max_age_days:
                raise ValueError(
                    f"{self.reading.service}'s last successful test is "
                    f"{age_days:.1f} days old, at or below its declared "
                    f"threshold of {self.max_age_days:.1f} days: this is "
                    f"not what the threshold names as stale"
                )

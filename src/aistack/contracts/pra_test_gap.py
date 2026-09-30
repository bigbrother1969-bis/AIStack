from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading

# Four conditions this domain detects — the fourth added 1.6 tranche 4
# (R9, 2026-09-30, OPS-0004's eighth reference case), the first three
# unchanged since the gap was reopened (2026-09-23). A declared
# service is either never tested, was tested and the test itself
# failed, or was tested and succeeded but the result is now older than
# `OPS-0009` allows — and, since tranche 4, a service `OPS-0010`
# already declares stateful (`has_state: true`,
# `backup_strategy.yml`) may not be declared in `OPS-0009`'s own file
# at all, one step further upstream than `UNTESTED` (which already
# names a `services:` entry, only with `last_test: null`). No fifth
# reason without a real case naming one (`GOV-P-001`).
UNTESTED = "untested"
STALE = "stale"
FAILED_REASON = "failed"
NOT_DECLARED = "not_declared"

REASONS = (UNTESTED, STALE, FAILED_REASON, NOT_DECLARED)


@dataclass(frozen=True)
class PraTestGap:
    """
    One declared (or, since tranche 4, should-be-declared) service
    already found to have failed the check `OPS-0009` declares for it:
    never tested, a test already recorded as failed, a successful
    test now older than the declared threshold allows, or — the
    eighth `OPS-0004` reference case, 1.6 tranche 4, 2026-09-30 — not
    even declared in `pra_tests.yml` at all, despite `OPS-0010`
    already declaring it stateful.

    Mirrors `BackupGap`: the reading and the reason it was already
    found to fail, enforced here rather than only in the caller —
    `find_pra_test_gaps`/`find_undeclared_pra_tests`
    (`aistack.runtime.pra_test_gap`) only ever construct a `PraTestGap`
    already confirmed to be one; neither re-derives "untested, failed,
    stale, or not declared" from a bare reading handed to it from
    elsewhere.

    **`NOT_DECLARED` carries a synthesized reading, not one the loader
    itself produced.** `find_undeclared_pra_tests` builds a
    `PraTestReading` with `status=None` for a stateful service
    `pra_tests.yml`'s own `services:` list never names — the same
    honest "nothing to report" shape `UNTESTED` already carries for a
    declared service with `last_test: null`, never a fabricated status
    or date (the roadmap's own words: "résultats seulement issus de
    vrais tests"). The distinction between the two lives in `reason`
    alone, not in the reading's own shape.

    **`FAILED_REASON` fires immediately, without a staleness check.**
    A restore already recorded as having failed is a gap the moment it
    is recorded — the legacy `homelab_documentation` engine's own
    `runtime/pra_tests.json` already declares `status: failed` as a
    real possible outcome (found and read, not invented, 2026-09-23),
    even though no entry currently reports it; this domain treats a
    future one the same way `STALE` treats an aging success, not as a
    hypothetical this codebase has to wait for a real case to handle.

    `max_age_days` is copied from the `PraTestThreshold` that fired,
    not re-looked-up later — the same "state what fired, not what
    fires today" `BackupGap.max_age_hours` already holds. It is
    carried even for `UNTESTED`/`FAILED_REASON`, where it played no
    part in the decision, so every `PraTestGap` states the threshold
    that governed the service at the time, not only the ones that
    used it directly.
    """

    reading: PraTestReading
    max_age_days: float
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise ValueError(
                f"{self.reading.service} cites {self.reason!r} as a PRA "
                f"test gap reason; only {REASONS} are detected in this "
                f"scope (OPS-0009, 2026-09-23)"
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

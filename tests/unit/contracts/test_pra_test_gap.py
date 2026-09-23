from datetime import datetime, timedelta, timezone

import pytest

from aistack.contracts.pra_test_gap import FAILED_REASON, STALE, UNTESTED, PraTestGap
from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading

SERVICE = "nextcloud"


def untested_reading(observed_at: datetime | None = None) -> PraTestReading:
    return PraTestReading(
        service=SERVICE, observed_at=observed_at or datetime.now(timezone.utc)
    )


def failed_reading(observed_at: datetime | None = None) -> PraTestReading:
    observed_at = observed_at or datetime.now(timezone.utc)
    return PraTestReading(
        service=SERVICE, observed_at=observed_at, status=FAILED, tested_at=observed_at
    )


def successful_reading(age_days: float) -> PraTestReading:
    observed_at = datetime.now(timezone.utc)
    return PraTestReading(
        service=SERVICE,
        observed_at=observed_at,
        status=SUCCESS,
        tested_at=observed_at - timedelta(days=age_days),
    )


def test_a_gap_refuses_an_unknown_reason():

    with pytest.raises(ValueError, match=r"only .* are detected"):
        PraTestGap(reading=untested_reading(), max_age_days=90.0, reason="expired")


def test_untested_is_accepted_when_the_reading_has_no_status():

    gap = PraTestGap(reading=untested_reading(), max_age_days=90.0, reason=UNTESTED)

    assert gap.reason == UNTESTED


def test_untested_is_refused_when_the_reading_reports_a_status():

    with pytest.raises(ValueError, match="cites 'untested'"):
        PraTestGap(
            reading=successful_reading(age_days=1), max_age_days=90.0, reason=UNTESTED
        )


def test_failed_is_accepted_when_the_reading_reports_a_failed_status():

    gap = PraTestGap(reading=failed_reading(), max_age_days=90.0, reason=FAILED_REASON)

    assert gap.reason == FAILED_REASON


def test_failed_is_refused_when_the_reading_does_not_report_failed():

    with pytest.raises(ValueError, match="cites 'failed'"):
        PraTestGap(
            reading=successful_reading(age_days=1),
            max_age_days=90.0,
            reason=FAILED_REASON,
        )


def test_stale_is_refused_when_the_reading_has_no_status():
    """
    "Never tested" is `UNTESTED`, never `STALE` — a `PraTestGap`
    citing `STALE` states there was a successful, dated test, only
    one now too old.
    """

    with pytest.raises(ValueError, match="that is 'untested' or 'failed', not 'stale'"):
        PraTestGap(reading=untested_reading(), max_age_days=90.0, reason=STALE)


def test_stale_is_refused_when_the_reading_reports_failed():

    with pytest.raises(ValueError, match="that is 'untested' or 'failed', not 'stale'"):
        PraTestGap(reading=failed_reading(), max_age_days=90.0, reason=STALE)


def test_stale_is_refused_when_the_test_is_within_threshold():

    with pytest.raises(ValueError, match="not what the threshold names"):
        PraTestGap(
            reading=successful_reading(age_days=30), max_age_days=90.0, reason=STALE
        )


def test_stale_is_accepted_when_the_test_is_older_than_threshold():

    gap = PraTestGap(
        reading=successful_reading(age_days=200), max_age_days=90.0, reason=STALE
    )

    assert gap.reason == STALE


def test_stale_is_refused_exactly_at_the_threshold_boundary():
    """
    Mirrors `BackupGap`'s own "at or below is not yet stale"
    boundary — a `PraTestGap` can only ever be constructed for what
    already crossed it.
    """

    with pytest.raises(ValueError, match="not what the threshold names"):
        PraTestGap(
            reading=successful_reading(age_days=90.0), max_age_days=90.0, reason=STALE
        )

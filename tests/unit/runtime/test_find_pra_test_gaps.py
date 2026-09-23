from datetime import datetime, timedelta, timezone

from aistack.contracts.pra_test_gap import FAILED_REASON, STALE, UNTESTED
from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading
from aistack.contracts.pra_test_threshold import PraTestThreshold
from aistack.runtime.pra_test_gap import find_pra_test_gaps

SERVICE = "nextcloud"


def untested_reading(service: str = SERVICE) -> PraTestReading:
    return PraTestReading(service=service, observed_at=datetime.now(timezone.utc))


def failed_reading(service: str = SERVICE) -> PraTestReading:
    observed_at = datetime.now(timezone.utc)
    return PraTestReading(
        service=service, observed_at=observed_at, status=FAILED, tested_at=observed_at
    )


def reading_aged(days: float, service: str = SERVICE) -> PraTestReading:
    observed_at = datetime.now(timezone.utc)
    return PraTestReading(
        service=service,
        observed_at=observed_at,
        status=SUCCESS,
        tested_at=observed_at - timedelta(days=days),
    )


def threshold(service: str = SERVICE, max_age_days: float = 90.0) -> PraTestThreshold:
    return PraTestThreshold(service=service, max_age_days=max_age_days)


def test_a_never_tested_service_is_flagged():

    gaps = find_pra_test_gaps([untested_reading()], [threshold()])

    assert len(gaps) == 1
    assert gaps[0].reason == UNTESTED


def test_a_failed_test_is_flagged():

    gaps = find_pra_test_gaps([failed_reading()], [threshold()])

    assert len(gaps) == 1
    assert gaps[0].reason == FAILED_REASON


def test_a_fresh_successful_test_is_not_flagged():

    gaps = find_pra_test_gaps([reading_aged(1)], [threshold()])

    assert gaps == ()


def test_a_stale_successful_test_is_flagged():

    gaps = find_pra_test_gaps([reading_aged(200)], [threshold()])

    assert len(gaps) == 1
    assert gaps[0].reason == STALE


def test_exactly_at_the_threshold_is_not_flagged():
    """
    Mirrors `find_backup_gaps`'s own "strictly past" convention: the
    boundary itself is not yet stale.
    """

    gaps = find_pra_test_gaps([reading_aged(90.0)], [threshold(max_age_days=90.0)])

    assert gaps == ()


def test_a_service_with_no_declared_threshold_is_silently_not_evaluated():

    gaps = find_pra_test_gaps([untested_reading(service="undeclared")], [])

    assert gaps == ()


def test_only_the_service_crossing_its_own_threshold_is_flagged_in_a_batch():

    fresh = reading_aged(1, service="nextcloud")
    stale = reading_aged(200, service="immich")

    gaps = find_pra_test_gaps(
        [fresh, stale],
        [threshold(service="nextcloud"), threshold(service="immich")],
    )

    assert [gap.reading.service for gap in gaps] == ["immich"]


def test_an_empty_reading_set_flags_nothing():

    assert find_pra_test_gaps([], [threshold()]) == ()

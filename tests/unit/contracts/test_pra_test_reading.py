from datetime import datetime, timedelta, timezone

import pytest

from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading


def test_a_reading_requires_a_service():

    with pytest.raises(ValueError, match="names none"):
        PraTestReading(service="", observed_at=datetime.now(timezone.utc))


def test_a_reading_may_carry_no_test_at_all():
    """
    `status` defaults to `None` — "never tested", the fact this
    domain exists to surface, not an omission — the same
    "absence stated as a fact" `BackupReading.newest_file_mtime is
    None` already holds for "no backup file found".
    """

    reading = PraTestReading(service="arrstack", observed_at=datetime.now(timezone.utc))

    assert reading.status is None
    assert reading.tested_at is None
    assert reading.rto_minutes is None


def test_a_reading_refuses_an_unknown_status():

    with pytest.raises(ValueError, match=r"only .* are declared"):
        PraTestReading(
            service="nextcloud",
            observed_at=datetime.now(timezone.utc),
            status="partial",
            tested_at=datetime.now(timezone.utc),
        )


def test_a_status_without_a_test_date_is_refused():

    with pytest.raises(ValueError, match="no test date"):
        PraTestReading(
            service="nextcloud", observed_at=datetime.now(timezone.utc), status=SUCCESS
        )


def test_a_test_date_without_a_status_is_refused():

    with pytest.raises(ValueError, match="carries a test date or an RTO"):
        PraTestReading(
            service="nextcloud",
            observed_at=datetime.now(timezone.utc),
            tested_at=datetime.now(timezone.utc),
        )


def test_an_rto_without_a_status_is_refused():

    with pytest.raises(ValueError, match="carries a test date or an RTO"):
        PraTestReading(
            service="nextcloud", observed_at=datetime.now(timezone.utc), rto_minutes=2
        )


def test_a_tested_at_after_observed_at_is_refused():

    observed_at = datetime.now(timezone.utc)
    future = observed_at + timedelta(hours=1)

    with pytest.raises(ValueError, match="newer"):
        PraTestReading(
            service="nextcloud",
            observed_at=observed_at,
            status=SUCCESS,
            tested_at=future,
        )


def test_a_tested_at_equal_to_observed_at_is_allowed():

    observed_at = datetime.now(timezone.utc)

    reading = PraTestReading(
        service="nextcloud",
        observed_at=observed_at,
        status=SUCCESS,
        tested_at=observed_at,
    )

    assert reading.tested_at == observed_at


def test_a_negative_rto_is_refused():

    observed_at = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="negative RTO"):
        PraTestReading(
            service="nextcloud",
            observed_at=observed_at,
            status=SUCCESS,
            tested_at=observed_at,
            rto_minutes=-1,
        )


def test_a_successful_reading_may_carry_no_rto():

    observed_at = datetime.now(timezone.utc)

    reading = PraTestReading(
        service="nextcloud",
        observed_at=observed_at,
        status=SUCCESS,
        tested_at=observed_at,
    )

    assert reading.rto_minutes is None


def test_a_failed_reading_is_accepted():

    observed_at = datetime.now(timezone.utc)

    reading = PraTestReading(
        service="gigabyte",
        observed_at=observed_at,
        status=FAILED,
        tested_at=observed_at,
    )

    assert reading.status == FAILED

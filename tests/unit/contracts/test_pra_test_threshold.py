import pytest

from aistack.contracts.pra_test_threshold import (
    PraTestThreshold,
    PraTestThresholdRegister,
)


# --------------------------------------------------------------------
# `PraTestThreshold`
# --------------------------------------------------------------------


def test_a_threshold_requires_a_service():

    with pytest.raises(ValueError, match="names none"):
        PraTestThreshold(service="", max_age_days=90.0)


def test_a_threshold_refuses_a_zero_max_age():

    with pytest.raises(ValueError, match="non-positive"):
        PraTestThreshold(service="nextcloud", max_age_days=0)


def test_a_threshold_refuses_a_negative_max_age():

    with pytest.raises(ValueError, match="non-positive"):
        PraTestThreshold(service="nextcloud", max_age_days=-1.0)


# --------------------------------------------------------------------
# `PraTestThresholdRegister`
# --------------------------------------------------------------------


def nextcloud_threshold() -> PraTestThreshold:
    return PraTestThreshold(service="nextcloud", max_age_days=90.0)


def test_for_service_returns_that_services_own_threshold():

    register = PraTestThresholdRegister(thresholds=(nextcloud_threshold(),))

    assert register.for_service("nextcloud") == nextcloud_threshold()


def test_for_service_with_no_declared_entry_returns_none_not_an_error():

    register = PraTestThresholdRegister(thresholds=(nextcloud_threshold(),))

    assert register.for_service("raspberry") is None


def test_an_empty_register_declares_nothing_for_any_service():

    register = PraTestThresholdRegister(thresholds=())

    assert register.for_service("nextcloud") is None

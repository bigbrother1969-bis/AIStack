import pytest

from aistack.contracts.backup_threshold import (
    BackupThreshold,
    BackupThresholdRegister,
    HostBackupThresholds,
)


# --------------------------------------------------------------------
# `BackupThreshold`
# --------------------------------------------------------------------


def test_a_threshold_requires_a_path():

    with pytest.raises(ValueError, match="names none"):
        BackupThreshold(path="", max_age_hours=168.0)


def test_a_threshold_refuses_a_zero_max_age():

    with pytest.raises(ValueError, match="non-positive"):
        BackupThreshold(path="/media/BACKUP/wordpress/", max_age_hours=0)


def test_a_threshold_refuses_a_negative_max_age():

    with pytest.raises(ValueError, match="non-positive"):
        BackupThreshold(path="/media/BACKUP/wordpress/", max_age_hours=-1.0)


# --------------------------------------------------------------------
# `HostBackupThresholds`
# --------------------------------------------------------------------


def test_a_hosts_thresholds_require_a_host_name():

    with pytest.raises(ValueError, match="name no host"):
        HostBackupThresholds(host="", thresholds=())


def test_a_hosts_thresholds_may_be_empty():

    entry = HostBackupThresholds(host="GIGABYTE", thresholds=())

    assert entry.thresholds == ()


# --------------------------------------------------------------------
# `BackupThresholdRegister`
# --------------------------------------------------------------------


def wordpress_threshold() -> BackupThreshold:
    return BackupThreshold(
        path="/media/BACKUP/persiaut-consulting/wordpress/", max_age_hours=168.0
    )


def test_for_host_returns_only_that_hosts_own_thresholds():

    register = BackupThresholdRegister(
        hosts=(
            HostBackupThresholds(host="GIGABYTE", thresholds=(wordpress_threshold(),)),
        )
    )

    assert register.for_host("GIGABYTE") == (wordpress_threshold(),)


def test_for_host_with_no_declared_entry_returns_empty_not_an_error():

    register = BackupThresholdRegister(
        hosts=(
            HostBackupThresholds(host="GIGABYTE", thresholds=(wordpress_threshold(),)),
        )
    )

    assert register.for_host("raspberry") == ()


def test_an_empty_register_declares_nothing_for_any_host():

    register = BackupThresholdRegister(hosts=())

    assert register.for_host("GIGABYTE") == ()

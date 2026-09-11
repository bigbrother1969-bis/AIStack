import pytest

from aistack.contracts.storage_threshold import (
    FREE_BYTES,
    HostStorageThresholds,
    StorageThreshold,
    StorageThresholdRegister,
)


# --------------------------------------------------------------------
# `HostStorageThresholds`
# --------------------------------------------------------------------


def test_a_hosts_thresholds_require_a_host_name():

    with pytest.raises(ValueError, match="name no host"):
        HostStorageThresholds(host="", thresholds=())


def test_a_hosts_thresholds_may_be_empty():
    """
    A host declared in the file but with nothing yet named for it —
    `OPS-0005` growing one host at a time — is still a valid entry,
    not an error.
    """

    entry = HostStorageThresholds(host="gigabyte", thresholds=())

    assert entry.thresholds == ()


# --------------------------------------------------------------------
# `StorageThresholdRegister`
# --------------------------------------------------------------------


def gigabyte_root() -> StorageThreshold:
    return StorageThreshold(mount="/", kind=FREE_BYTES, value=20 * 1024**3)


def raspberry_root() -> StorageThreshold:
    return StorageThreshold(mount="/", kind=FREE_BYTES, value=2 * 1024**3)


def test_for_host_returns_only_that_hosts_own_thresholds():

    register = StorageThresholdRegister(
        hosts=(
            HostStorageThresholds(host="gigabyte", thresholds=(gigabyte_root(),)),
            HostStorageThresholds(host="raspberry", thresholds=(raspberry_root(),)),
        )
    )

    assert register.for_host("gigabyte") == (gigabyte_root(),)
    assert register.for_host("raspberry") == (raspberry_root(),)


def test_for_host_with_no_declared_entry_returns_empty_not_an_error():
    """
    FDN-0003 Article 12: a host `OPS-0005` has not been asked about
    yet is outside what this register can state anything about, not
    thereby "nothing to check" in the sense of a value it declared.
    `find_storage_shortage`'s own caller reads the returned `()`
    exactly the way it already reads a mount with no threshold at
    all.
    """

    register = StorageThresholdRegister(
        hosts=(HostStorageThresholds(host="gigabyte", thresholds=(gigabyte_root(),)),)
    )

    assert register.for_host("some-other-host") == ()


def test_an_empty_register_declares_nothing_for_any_host():

    register = StorageThresholdRegister(hosts=())

    assert register.for_host("gigabyte") == ()

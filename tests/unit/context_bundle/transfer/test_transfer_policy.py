from aistack.context_bundle.transfer.policy import (
    DefaultBundleTransferPolicy,
)


def test_default_transfer_policy_disabled():

    policy = DefaultBundleTransferPolicy()

    assert policy.enabled is False

    assert policy.target == ""

    assert policy.strategy == "filesystem"


def test_transfer_policy_configuration():

    policy = DefaultBundleTransferPolicy(
        _enabled=True,
        _target="laptop",
        _strategy="filesystem",
    )

    assert policy.enabled is True

    assert policy.target == "laptop"

    assert policy.strategy == "filesystem"

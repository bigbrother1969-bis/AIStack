from aistack.contracts.bundle_transfer_policy import (
    BundleTransferPolicy,
)


class DummyBundleTransferPolicy(
    BundleTransferPolicy
):

    @property
    def enabled(self) -> bool:
        return True

    @property
    def target(self) -> str:
        return "laptop"

    @property
    def strategy(self) -> str:
        return "filesystem"


def test_bundle_transfer_policy_contract():

    policy = DummyBundleTransferPolicy()

    assert policy.enabled is True

    assert policy.target == "laptop"

    assert policy.strategy == "filesystem"

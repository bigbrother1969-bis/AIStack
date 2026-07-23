from abc import ABC

from aistack.kernel.contracts import PackageCapability


def test_package_capability_is_an_abstract_contract() -> None:
    assert issubclass(PackageCapability, ABC)

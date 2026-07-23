from aistack.kernel.contracts import PackageCapability
from aistack.kernel.registries import ContractRegistry


def test_contract_registry_registers_contract() -> None:
    registry = ContractRegistry()

    registry.register(PackageCapability)

    assert registry.contains("PackageCapability")
    assert registry.get("PackageCapability") is PackageCapability

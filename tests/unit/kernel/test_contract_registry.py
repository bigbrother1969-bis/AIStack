from aistack.kernel.contracts import CatalogViewEngine
from aistack.kernel.registries import ContractRegistry


def test_contract_registry_registers_contract() -> None:
    """
    Registered `PackageCapability` until 2026-08-29, and that
    contract was removed with the Knowledge Package classes it
    described. `CatalogViewEngine` replaces it — a contract the
    heritage actually retrieves, since the Docker path and the
    Selection UI both resolve an engine through it.

    *The registry is what is under test, not the contract. But a
    sample that is itself dead makes a test that passes whatever
    happens to the thing it samples.*
    """

    registry = ContractRegistry()

    registry.register(CatalogViewEngine)

    assert registry.contains("CatalogViewEngine")
    assert registry.get("CatalogViewEngine") is CatalogViewEngine

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

    registry.register_contract(CatalogViewEngine)

    assert registry.contains("CatalogViewEngine")
    assert registry.get("CatalogViewEngine") is CatalogViewEngine


def test_the_inherited_register_still_takes_an_identifier_and_an_entry() -> None:
    """
    `register_contract` is a convenience layered on top of
    `Registry.register`, not a replacement for it — the base method
    stays reachable, and any polymorphic caller holding a
    `Registry[Type]` reference can still call it exactly as documented
    on `Registry` itself. Found missing 2026-09-10 by `mypy`, which
    flagged the class's own `register` override as incompatible with
    its superclass before this rename.
    """

    registry = ContractRegistry()

    registry.register("CatalogViewEngine", CatalogViewEngine)

    assert registry.contains("CatalogViewEngine")
    assert registry.get("CatalogViewEngine") is CatalogViewEngine

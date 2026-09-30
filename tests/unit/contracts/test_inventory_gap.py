import pytest

from aistack.contracts.inventory_gap import (
    DECLARED_UNDISCOVERED,
    DISCOVERED_UNDECLARED,
    InventoryGap,
)


def test_a_discovered_undeclared_gap_is_accepted():
    gap = InventoryGap(kind=DISCOVERED_UNDECLARED, container="mystery", host="GIGABYTE")

    assert gap.container == "mystery"
    assert gap.host == "GIGABYTE"
    assert gap.service is None


def test_a_discovered_undeclared_gap_without_a_host_is_accepted():
    gap = InventoryGap(kind=DISCOVERED_UNDECLARED, container="mystery")

    assert gap.host is None


def test_a_declared_undiscovered_gap_is_accepted():
    gap = InventoryGap(
        kind=DECLARED_UNDISCOVERED, container="wordpress", service="WordPress"
    )

    assert gap.container == "wordpress"
    assert gap.service == "WordPress"
    assert gap.host is None


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="must be one of"):
        InventoryGap(kind="mystery-kind", container="x")


def test_a_blank_kind_is_refused():
    with pytest.raises(ValueError, match="requires a kind"):
        InventoryGap(kind="", container="x")


def test_a_blank_container_is_refused():
    with pytest.raises(ValueError, match="non-blank container"):
        InventoryGap(kind=DISCOVERED_UNDECLARED, container="")


def test_a_declared_undiscovered_gap_without_a_service_is_refused():
    with pytest.raises(ValueError, match="names the declared service"):
        InventoryGap(kind=DECLARED_UNDISCOVERED, container="wordpress")


def test_a_declared_undiscovered_gap_with_a_blank_service_is_refused():
    with pytest.raises(ValueError, match="names the declared service"):
        InventoryGap(kind=DECLARED_UNDISCOVERED, container="wordpress", service="  ")


def test_a_discovered_undeclared_gap_with_a_service_is_refused():
    with pytest.raises(ValueError, match="names no declared service"):
        InventoryGap(
            kind=DISCOVERED_UNDECLARED, container="mystery", service="WordPress"
        )

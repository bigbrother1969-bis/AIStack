from aistack.architecture.definition import (
    ServiceCategoryDefinition,
    ServiceCategorizationDefinition,
    ServiceDefinition,
)
from aistack.contracts.inventory_gap import DECLARED_UNDISCOVERED, DISCOVERED_UNDECLARED
from aistack.runtime.inventory_gap import find_inventory_gaps


def categorization(*services: ServiceDefinition) -> ServiceCategorizationDefinition:
    return ServiceCategorizationDefinition(
        categories=(ServiceCategoryDefinition(name="Homelab", services=services),)
    )


def test_a_declared_and_discovered_container_is_not_flagged():
    gaps = find_inventory_gaps(
        categorization(ServiceDefinition(name="WordPress", container="wordpress")),
        discovered={"wordpress": None},
    )

    assert gaps == ()


def test_a_discovered_container_not_declared_anywhere_is_flagged():
    gaps = find_inventory_gaps(
        categorization(),
        discovered={"mystery": "GIGABYTE"},
    )

    assert len(gaps) == 1
    assert gaps[0].kind == DISCOVERED_UNDECLARED
    assert gaps[0].container == "mystery"
    assert gaps[0].host == "GIGABYTE"


def test_a_declared_container_never_discovered_is_flagged():
    gaps = find_inventory_gaps(
        categorization(ServiceDefinition(name="WordPress", container="wordpress")),
        discovered={},
    )

    assert len(gaps) == 1
    assert gaps[0].kind == DECLARED_UNDISCOVERED
    assert gaps[0].container == "wordpress"
    assert gaps[0].service == "WordPress"


def test_a_declared_service_with_no_container_is_never_flagged_in_either_direction():
    gaps = find_inventory_gaps(
        categorization(ServiceDefinition(name="Freebox")),
        discovered={},
    )

    assert gaps == ()


def test_both_directions_in_the_same_batch():
    gaps = find_inventory_gaps(
        categorization(
            ServiceDefinition(name="WordPress", container="wordpress"),
            ServiceDefinition(name="Arrstack", container="arrstack"),
        ),
        discovered={"wordpress": None, "mystery": "raspberry"},
    )

    kinds = {(gap.kind, gap.container) for gap in gaps}
    assert kinds == {
        (DECLARED_UNDISCOVERED, "arrstack"),
        (DISCOVERED_UNDECLARED, "mystery"),
    }


def test_an_empty_categorization_and_empty_discovery_flags_nothing():
    assert find_inventory_gaps(categorization(), discovered={}) == ()


def test_gaps_are_sorted_by_container_name_within_each_direction():
    gaps = find_inventory_gaps(
        categorization(),
        discovered={"zeta": "GIGABYTE", "alpha": "GIGABYTE"},
    )

    assert [gap.container for gap in gaps] == ["alpha", "zeta"]


def test_an_on_demand_service_stopped_is_not_a_gap_and_running_is_still_declared():
    """Frigate, 2026-10-04: started only when needed."""

    frigate = ServiceDefinition(name="Frigate", container="frigate", on_demand=True)

    assert find_inventory_gaps(categorization(frigate), discovered={}) == ()
    assert find_inventory_gaps(categorization(frigate), discovered={"frigate": None}) == ()

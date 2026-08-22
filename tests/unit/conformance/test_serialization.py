import json

from aistack.conformance.inventory import take_inventory
from aistack.conformance.serialization import (
    deserialize_inventory,
    serialize_inventory,
)
from aistack.contracts.contract_inventory import (
    ABSTRACT,
    PROTOCOL,
    ContractInventory,
    DeclaredContract,
)


def sample() -> ContractInventory:
    return ContractInventory(
        package="aistack",
        modules=300,
        implementations=145,
        contracts=(
            DeclaredContract(
                name="IntegrityCheck",
                module="aistack.contracts.integrity_check",
                kind=ABSTRACT,
                members=("evaluate", "name"),
                satisfied_by=("aistack.integrity.checks.x.XCheck",),
            ),
            DeclaredContract(
                name="TransferTarget",
                module="aistack.contracts.transfer_target",
                kind=PROTOCOL,
                members=("send",),
            ),
        ),
        unreadable=(("aistack.funnel.__main__", "ModuleNotFoundError"),),
    )


def test_a_round_trip_preserves_everything_that_is_measured():

    restored = deserialize_inventory(serialize_inventory(sample()))

    assert restored == sample()


def test_the_real_inventory_survives_a_round_trip():
    """
    The fixture above is small and agrees with itself. This one
    is the measurement that actually travels in the projection.
    """

    measured = take_inventory()

    restored = deserialize_inventory(serialize_inventory(measured))

    assert restored == measured
    assert restored.orphans == measured.orphans
    assert restored.is_partial == measured.is_partial


def test_the_payload_is_json_and_carries_its_format_version():
    """
    The format is explicit rather than `asdict`, which would make
    every attribute name part of the wire format silently and
    break published bundles on a rename.
    """

    payload = serialize_inventory(sample())

    assert json.loads(json.dumps(payload)) == payload
    assert payload["format_version"] == "1.0"


def test_the_counts_are_read_and_never_recomputed():
    """
    A bundle whose `modules` disagrees with what it contains is
    describing a walk it did not perform. Recomputing the number
    from the lists would hide that.
    """

    payload = serialize_inventory(sample())
    payload["modules"] = 9999

    assert deserialize_inventory(payload).modules == 9999


def test_a_payload_without_optional_lists_still_reads():
    """
    An inventory of a package with no contracts and no failures
    is a legitimate state, not a malformed file.
    """

    restored = deserialize_inventory(
        {
            "format_version": "1.0",
            "package": "empty",
            "modules": 1,
            "implementations": 0,
        }
    )

    assert restored.contracts == ()
    assert restored.unreadable == ()
    assert not restored.is_partial

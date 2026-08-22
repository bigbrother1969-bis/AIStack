"""
Carry a contract inventory in and out of a projection.

The measurement is taken where the source tree is — at
generation — and read where only the bundle is, which is the
whole point of putting it in the projection. An agent handed the
bundle and nothing else can state the debt of the heritage it
received.

The format is explicit rather than a dump of the dataclass.
`asdict` would make every field name part of the wire format
silently, and renaming an attribute would break every bundle
already published.
"""

from __future__ import annotations

from typing import Any

from aistack.contracts.contract_inventory import (
    ContractInventory,
    DeclaredContract,
)


FORMAT_VERSION = "1.0"


def serialize_inventory(inventory: ContractInventory) -> dict[str, Any]:

    return {
        "format_version": FORMAT_VERSION,
        "package": inventory.package,
        "modules": inventory.modules,
        "implementations": inventory.implementations,
        "unreadable": [
            {"module": module, "error": error}
            for module, error in inventory.unreadable
        ],
        "contracts": [
            {
                "name": contract.name,
                "module": contract.module,
                "kind": contract.kind,
                "members": list(contract.members),
                "satisfied_by": list(contract.satisfied_by),
            }
            for contract in inventory.contracts
        ],
    }


def deserialize_inventory(payload: dict[str, Any]) -> ContractInventory:
    """
    Rebuild the inventory a projection carries.

    Every count is read from the payload rather than recomputed
    from the lists. A bundle whose `modules` disagrees with what
    it contains is describing a walk it did not perform, and
    silently recomputing the number would hide that.
    """

    return ContractInventory(
        package=payload["package"],
        modules=payload["modules"],
        implementations=payload["implementations"],
        contracts=tuple(
            DeclaredContract(
                name=entry["name"],
                module=entry["module"],
                kind=entry["kind"],
                members=tuple(entry.get("members", ())),
                satisfied_by=tuple(entry.get("satisfied_by", ())),
            )
            for entry in payload.get("contracts", ())
        ),
        unreadable=tuple(
            (entry["module"], entry["error"])
            for entry in payload.get("unreadable", ())
        ),
    )

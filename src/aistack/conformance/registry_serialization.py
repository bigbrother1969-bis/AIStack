"""
Carry a registry inventory in and out of a projection.

Same reason as the contract inventory, and the same shape: the
measurement needs the source tree and a composed Kernel, and it is
read where only the bundle is. An agent handed the projection can
state what this heritage registers and what asks for it.

The format is explicit rather than a dump of the dataclass.
`asdict` would make every attribute name part of the wire format
silently, and renaming one would break every bundle already
published.
"""

from __future__ import annotations

from typing import Any

from aistack.contracts.registry_inventory import (
    RegisteredEntry,
    RegistryInventory,
    RetrievalSite,
)


FORMAT_VERSION = "1.0"


def serialize_registries(inventory: RegistryInventory) -> dict[str, Any]:

    return {
        "format_version": FORMAT_VERSION,
        "measured": inventory.measured,
        "sources": inventory.sources,
        "registries": list(inventory.registries),
        "registered": [
            {
                "registry": entry.registry,
                "identifier": entry.identifier,
                "entry": entry.entry,
            }
            for entry in inventory.registered
        ],
        "retrievals": [
            {
                "registry": retrieval.registry,
                # `null` and a missing key would both read as "no
                # identifier", and one of them means "computed".
                # The key is always written for that reason.
                "identifier": retrieval.identifier,
                "site": retrieval.site,
                "in_tests": retrieval.in_tests,
            }
            for retrieval in inventory.retrievals
        ],
        "unreadable": [
            {"source": source, "error": error}
            for source, error in inventory.unreadable
        ],
    }


def deserialize_registries(payload: dict[str, Any]) -> RegistryInventory:
    """
    Rebuild the registry inventory a projection carries.

    `measured` is read from the payload and never inferred from
    the lists. A bundle that carries this member with everything
    empty is saying the walk found nothing; a bundle that carries
    it with `measured` false is saying the walk did not happen,
    and those are two different facts.
    """

    return RegistryInventory(
        registries=tuple(payload.get("registries", ())),
        registered=tuple(
            RegisteredEntry(
                registry=entry["registry"],
                identifier=entry["identifier"],
                entry=entry["entry"],
            )
            for entry in payload.get("registered", ())
        ),
        retrievals=tuple(
            RetrievalSite(
                registry=retrieval["registry"],
                identifier=retrieval.get("identifier"),
                site=retrieval["site"],
                in_tests=retrieval.get("in_tests", False),
            )
            for retrieval in payload.get("retrievals", ())
        ),
        sources=payload.get("sources", 0),
        unreadable=tuple(
            (entry["source"], entry["error"])
            for entry in payload.get("unreadable", ())
        ),
        measured=payload.get("measured", False),
    )

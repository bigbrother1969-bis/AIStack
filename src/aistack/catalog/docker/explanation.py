from __future__ import annotations

from aistack.kernel.catalog import Catalog, CatalogItem


def explain_docker_catalog(catalog: Catalog) -> tuple[str, ...]:
    """One sentence per container in `catalog`, stating what the catalog
    observed.

    Every value comes from `item.metadata`; an empty field is stated in
    words ("no published ports") rather than omitted. Images, networks and
    volumes are not explained.
    """

    return tuple(
        _explain_container(item)
        for item in catalog.items
        if item.kind == "container"
    )


def _explain_container(item: CatalogItem) -> str:
    image = item.metadata.get("image") or "an unnamed image"
    state = item.metadata.get("state") or "undeclared"
    ports = item.metadata.get("ports") or "no published ports"
    mounts = item.metadata.get("mounts") or "no mounts"

    return (
        f"Container {item.label!r} runs image {image!r}, "
        f"state {state!r}, publishing {ports!r}, "
        f"with mounts {mounts!r}."
    )

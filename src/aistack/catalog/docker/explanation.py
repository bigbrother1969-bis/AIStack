from __future__ import annotations

from aistack.kernel.catalog import Catalog, CatalogItem


def explain_docker_catalog(catalog: Catalog) -> tuple[str, ...]:
    """
    One sentence per container in `catalog`, stating exactly what
    the catalog itself observed.

    `STD-0300` VS-1 criterion 1.4: *"every statement in the
    generated explanation references an observation present in the
    catalog."* Built 2026-09-04 rather than earlier because nothing
    in this heritage generated an explanation of the Docker catalog
    before this — `DockerCatalogArtifactGenerator` writes the
    catalog itself, not a sentence about it, and the criterion
    named a gap this repository had not yet closed.

    **Every value a sentence states is read from `item.metadata`,
    nothing invented.** Where a field is empty, the sentence says
    so in words ("no published ports") rather than omitting the
    clause — the same convention `DockerRuntimeCatalogBuilder`
    already uses for an absent value: what was observed to be
    absent is still an observation, not a gap in the sentence.

    **Containers only.** `catalog` also carries images, networks
    and volumes, but "a Docker infrastructure" in the criterion's
    own sense is what a container running or not running answers —
    extending this to the other three kinds is not what the
    criterion asks, and building it before a reader asks for it is
    exactly what `ARC-P-006` refuses.
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

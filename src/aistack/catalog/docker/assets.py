from __future__ import annotations

from typing import Any

from aistack.contracts.container_health import health_of
from aistack.kernel.catalog import Catalog, CatalogItem


class DockerRuntimeCatalogBuilder:
    """
    Build a governed Catalog from raw Docker observations.

    **One Catalog, four kinds.** The Docker runtime holds
    containers, images, networks and volumes; a `Catalog` is a
    flat list, and `CatalogItem.kind` is what a flat list has for
    saying which family an item belongs to. Decided 2026-08-29 by
    the owner, closing GOV-0002/OS-042: until then this builder
    returned a `dict` where its Compose twin returned a `Catalog`,
    and the two sat side by side under `aistack/catalog/`
    returning different kinds of thing.

    **Identifiers are unique within a kind, not across kinds.**
    A container and an image could carry the same natural name,
    and nothing here prevents it. That is why the Catalog View
    Engine that consumes this filters on `kind` before selecting:
    a view holds one family, and within it an identifier is
    unambiguous. Stated rather than guarded, because inventing a
    prefix scheme would change every identifier a human reads to
    protect against a collision this repository has never seen.
    """

    def build(self, observation: dict[str, Any]) -> Catalog:
        docker = observation["docker"]

        return Catalog(
            catalog_id="docker-runtime",
            title="Docker Runtime Catalog",
            metadata={
                "source_provider": observation["provider"]["id"],
                "collected_at": observation["collected_at"],
            },
            items=(
                *self._containers(docker["containers"]),
                *self._images(docker["images"]),
                *self._networks(docker["networks"]),
                *self._volumes(docker["volumes"]),
            ),
        )

    def _containers(
        self, containers: list[dict[str, Any]]
    ) -> tuple[CatalogItem, ...]:
        return tuple(
            CatalogItem(
                id=self._identity(item),
                label=self._identity(item),
                kind="container",
                source=self._text(item.get("Image")),
                metadata={
                    "docker_id": self._text(item.get("ID")),
                    "image": self._text(item.get("Image")),
                    "status": self._text(item.get("Status")),
                    "state": self._text(item.get("State")),
                    # What the runtime says of this container's
                    # health, separated from the sentence it says
                    # it in. Until 2026-08-27 the catalogue
                    # carried `status` and `state` and nothing
                    # else, so every consumer that wanted health
                    # had to parse a sentence — which is how the
                    # experimenter came to default a missing
                    # verdict to `healthy`. ADR-0009 § 6,
                    # GOV-0002/OS-035.
                    "health": health_of(item.get("Status")).value,
                    "ports": self._text(item.get("Ports")),
                    # `docker ps --format '{{json .}}'` already
                    # carries `Mounts` — the provider's own raw
                    # observation always had it, nothing here
                    # asked for it before `STD-0300` § *VS-1*
                    # criterion 1.2 named "published ports and
                    # mounts" as what a catalog entry must carry,
                    # 2026-09-04. Sorted rather than passed
                    # through: a live run against GIGABYTE the
                    # same day showed Docker's own comma-joined
                    # order for this field is not stable across
                    # two `docker ps` invocations with no host
                    # change, which broke `STD-0300` criterion
                    # 1.3 (regeneration determinism) on its first
                    # execution. Sorting is a property of this
                    # catalog, not a claim about Docker's mount
                    # order meaning anything.
                    "mounts": self._sorted_csv(item.get("Mounts")),
                },
            )
            for item in containers
        )

    def _images(self, images: list[dict[str, Any]]) -> tuple[CatalogItem, ...]:
        # Sorted by identity, not passed through in Docker's own
        # order. A live run against GIGABYTE, 2026-09-04, showed
        # two entries carrying the same `docker_id` — one image,
        # two repository tags — swap position between two
        # `docker images` calls with no host change, which broke
        # `STD-0300` criterion 1.3 (regeneration determinism) the
        # same way the unsorted `mounts` field did. Only `images`
        # showed this; containers, networks and volumes did not,
        # so only this family is sorted (`ARC-P-006`).
        images = sorted(images, key=self._image_identity)

        return tuple(
            CatalogItem(
                id=self._image_identity(item),
                label=self._image_identity(item),
                kind="image",
                source=self._text(item.get("Repository")),
                metadata={
                    "repository": self._text(item.get("Repository")),
                    "tag": self._text(item.get("Tag")),
                    "docker_id": self._text(item.get("ID")),
                    "size": self._text(item.get("Size")),
                },
            )
            for item in images
        )

    def _networks(
        self, networks: list[dict[str, Any]]
    ) -> tuple[CatalogItem, ...]:
        return tuple(
            CatalogItem(
                id=self._identity(item),
                label=self._identity(item),
                kind="network",
                source=self._text(item.get("Driver")),
                metadata={
                    "docker_id": self._text(item.get("ID")),
                    "driver": self._text(item.get("Driver")),
                    "scope": self._text(item.get("Scope")),
                },
            )
            for item in networks
        )

    def _volumes(
        self, volumes: list[dict[str, Any]]
    ) -> tuple[CatalogItem, ...]:
        return tuple(
            CatalogItem(
                id=self._identity(item),
                label=self._identity(item),
                kind="volume",
                source=self._text(item.get("Driver")),
                metadata={
                    "driver": self._text(item.get("Driver")),
                    "scope": self._text(item.get("Scope")),
                },
            )
            for item in volumes
        )

    def _identity(self, item: dict[str, Any]) -> str:
        """
        The name a human reads, falling back to the runtime id.

        `Names` is what the previous selection path used as an
        identifier and what the Compose twin uses for a project,
        so it is kept. **Nothing is dropped when it is absent**:
        the earlier selection builder skipped a nameless
        container silently, and a catalog that omits what it
        observed is worse than one carrying an ugly identifier.
        """

        return self._text(item.get("Names") or item.get("Name") or item.get("ID"))

    def _image_identity(self, item: dict[str, Any]) -> str:
        repository = self._text(item.get("Repository"))
        tag = self._text(item.get("Tag"))

        if repository and tag:
            return f"{repository}:{tag}"

        return repository or self._text(item.get("ID"))

    def _text(self, value: Any) -> str:
        """
        `CatalogItem.metadata` is `dict[str, str]`, and the
        observation is whatever the runtime printed. `None` is a
        real input — the previous builder passed it through and
        the JSON carried `null`.
        """

        return "" if value is None else str(value)

    def _sorted_csv(self, value: Any) -> str:
        """
        Sort a Docker comma-joined field alphabetically by entry.

        `mounts` is the one field this builder sorts. Discovered
        2026-09-04, against GIGABYTE: two consecutive
        `docker ps --format '{{json .}}'` calls with no host
        change rendered the same container's `Mounts` string in a
        different order — `STD-0300/VS-1` criterion 1.3 failed on
        its first live execution because of it, not because
        anything on the host had changed. No other field this
        builder reads showed the same instability that day, so
        only this one is sorted (`ARC-P-006`).
        """

        text = self._text(value)

        if not text:
            return text

        return ",".join(sorted(part.strip() for part in text.split(",")))

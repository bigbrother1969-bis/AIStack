from __future__ import annotations

from typing import Any

from aistack.contracts.container_health import health_of
from aistack.kernel.catalog import Catalog, CatalogItem


class DockerRuntimeCatalogBuilder:
    """Build a Catalog from raw Docker observations.

    One flat catalog holds containers, images, networks and volumes,
    distinguished by `CatalogItem.kind`. Identifiers are unique within a
    kind only, so views filter on `kind` before selecting.
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
                    # Health parsed once from the status sentence, so
                    # consumers never guess it (`ADR-0009` § 6).
                    "health": health_of(item.get("Status")).value,
                    "ports": self._text(item.get("Ports")),
                    # Sorted: Docker's order for this field is not
                    # stable between `docker ps` calls.
                    "mounts": self._sorted_csv(item.get("Mounts")),
                },
            )
            for item in containers
        )

    def _images(self, images: list[dict[str, Any]]) -> tuple[CatalogItem, ...]:
        # Sorted: entries sharing a `docker_id` (one image, several
        # tags) swap order between `docker images` calls.
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
        """The human-readable name, falling back to the runtime id, so a
        nameless item is never dropped."""

        return self._text(item.get("Names") or item.get("Name") or item.get("ID"))

    def _image_identity(self, item: dict[str, Any]) -> str:
        repository = self._text(item.get("Repository"))
        tag = self._text(item.get("Tag"))

        if repository and tag:
            return f"{repository}:{tag}"

        return repository or self._text(item.get("ID"))

    def _text(self, value: Any) -> str:
        """`str(value)`, with `None` as `""` (metadata values are strings)."""

        return "" if value is None else str(value)

    def _sorted_csv(self, value: Any) -> str:
        """Sort the entries of a Docker comma-joined field alphabetically."""

        text = self._text(value)

        if not text:
            return text

        return ",".join(sorted(part.strip() for part in text.split(",")))

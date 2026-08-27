from __future__ import annotations

from typing import Any

from aistack.contracts.container_health import health_of


class DockerRuntimeCatalogBuilder:
    """Build canonical Docker infrastructure assets from raw observations."""

    def build(self, observation: dict[str, Any]) -> dict[str, Any]:
        docker = observation["docker"]

        return {
            "catalog_type": "docker_runtime_catalog",
            "source_provider": observation["provider"]["id"],
            "collected_at": observation["collected_at"],
            "infrastructure_assets": {
                "containers": self._containers(docker["containers"]),
                "images": self._images(docker["images"]),
                "networks": self._networks(docker["networks"]),
                "volumes": self._volumes(docker["volumes"]),
            },
        }

    def _containers(self, containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item.get("ID"),
                "name": item.get("Names"),
                "image": item.get("Image"),
                "status": item.get("Status"),
                "state": item.get("State"),
                # What the runtime says of this container's
                # health, separated from the sentence it says it
                # in. Until 2026-08-27 the catalogue carried
                # `status` and `state` and nothing else, so every
                # consumer that wanted health had to parse a
                # sentence — which is how the experimenter came to
                # default a missing verdict to `healthy`.
                # ADR-0009 § 6, GOV-0002/OS-035.
                "health": health_of(item.get("Status")).value,
                "ports": item.get("Ports"),
            }
            for item in containers
        ]

    def _images(self, images: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "repository": item.get("Repository"),
                "tag": item.get("Tag"),
                "id": item.get("ID"),
                "size": item.get("Size"),
            }
            for item in images
        ]

    def _networks(self, networks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item.get("ID"),
                "name": item.get("Name"),
                "driver": item.get("Driver"),
                "scope": item.get("Scope"),
            }
            for item in networks
        ]

    def _volumes(self, volumes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": item.get("Name"),
                "driver": item.get("Driver"),
                "scope": item.get("Scope"),
            }
            for item in volumes
        ]

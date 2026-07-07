from __future__ import annotations

from typing import Any


class DockerKnowledgeAssetBuilder:
    """Build stable Docker Knowledge Assets from raw Docker observations."""

    def build(self, observation: dict[str, Any]) -> dict[str, Any]:
        docker = observation["docker"]

        return {
            "asset_type": "docker_runtime_inventory",
            "source_provider": observation["provider"]["id"],
            "collected_at": observation["collected_at"],
            "assets": {
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
                "ports": item.get("Ports"),
                "compose_project": item.get("Label", ""),
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

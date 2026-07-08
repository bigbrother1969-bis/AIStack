from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aistack.providers.docker import DockerProvider


class ComposeProvider:
    """Docker Compose Knowledge Provider.

    This provider derives Compose project observations from the Docker
    runtime labels exposed by running or stopped containers.
    """

    provider_id = "aistack.provider.compose"
    provider_name = "Docker Compose Provider"

    def collect(self) -> dict[str, Any]:
        docker_observation = DockerProvider().collect()
        containers = docker_observation["docker"]["containers"]

        projects: dict[str, dict[str, Any]] = {}

        for container in containers:
            labels = self._parse_labels(container.get("Labels", ""))

            project_name = labels.get("com.docker.compose.project")
            if not project_name:
                continue

            project = projects.setdefault(
                project_name,
                {
                    "name": project_name,
                    "working_dir": labels.get("com.docker.compose.project.working_dir"),
                    "config_files": labels.get("com.docker.compose.project.config_files"),
                    "services": {},
                },
            )

            service_name = labels.get("com.docker.compose.service", container.get("Names"))

            project["services"][service_name] = {
                "container_name": container.get("Names"),
                "image": container.get("Image"),
                "state": container.get("State"),
                "status": container.get("Status"),
                "ports": container.get("Ports"),
            }

        return {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "compose": {
                "projects": list(projects.values()),
            },
        }

    def _parse_labels(self, raw_labels: str) -> dict[str, str]:
        labels: dict[str, str] = {}

        if not raw_labels:
            return labels

        for item in raw_labels.split(","):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            labels[key.strip()] = value.strip()

        return labels

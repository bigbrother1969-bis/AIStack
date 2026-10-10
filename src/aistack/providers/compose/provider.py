from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml

from aistack.providers.docker import DockerProvider


class ComposeProvider:
    """Derive Compose project observations from container labels.

    Also reads each project's compose file(s), named by the
    `com.docker.compose.project.config_files` label (possibly
    comma-separated), to extract each service's `depends_on:` as a flat
    tuple of service names. `ComposeRuntimeCatalogBuilder` turns them into
    container edges.

    Never raises: a missing or unreadable compose file just leaves that
    project's services without `depends_on`.
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

        for project in projects.values():
            depends_on_by_service = self._read_depends_on(project.get("config_files"))

            for service_name, depends_on in depends_on_by_service.items():
                service = project["services"].get(service_name)
                if service is not None and depends_on:
                    service["depends_on"] = list(depends_on)

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

    def _read_depends_on(
        self, config_files: str | None
    ) -> dict[str, tuple[str, ...]]:
        """Each service's `depends_on:` service names from the compose
        file(s) `config_files` names.

        Later files win, as with Compose's `-f` merge order; a later file
        without `depends_on:` for a service does not clear an earlier one.
        """

        result: dict[str, tuple[str, ...]] = {}

        if not config_files:
            return result

        for raw_path in config_files.split(","):
            path = raw_path.strip()
            if not path:
                continue

            try:
                with open(path, encoding="utf-8") as stream:
                    document = yaml.safe_load(stream)
            except (OSError, yaml.YAMLError):
                continue

            if not isinstance(document, dict):
                continue

            services = document.get("services")
            if not isinstance(services, dict):
                continue

            for service_name, service_body in services.items():
                if not isinstance(service_body, dict):
                    continue

                names = self._normalize_depends_on(service_body.get("depends_on"))
                if names:
                    result[service_name] = names

        return result

    def _normalize_depends_on(self, depends_on: Any) -> tuple[str, ...]:
        """Service names from `depends_on:`, given either as a list or as a
        mapping to `condition:` blocks (conditions are ignored)."""

        if isinstance(depends_on, list):
            return tuple(name for name in depends_on if isinstance(name, str))

        if isinstance(depends_on, dict):
            return tuple(name for name in depends_on if isinstance(name, str))

        return ()

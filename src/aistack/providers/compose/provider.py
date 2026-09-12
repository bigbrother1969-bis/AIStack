from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml

from aistack.providers.docker import DockerProvider


class ComposeProvider:
    """Docker Compose Knowledge Provider.

    This provider derives Compose project observations from the Docker
    runtime labels exposed by running or stopped containers.

    **Also reads each project's own `docker-compose.yml`, added
    2026-09-12** (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, third
    gap). Until then this class read only the labels Docker itself
    attaches to a container — enough to know a project's name,
    working directory and member containers, never what one service
    inside it declares about another. `com.docker.compose.project.
    config_files` already names the real file on disk (confirmed
    2026-09-12 against GIGABYTE's own 33 real projects: always one
    path, never Compose's documented comma-separated multi-file
    form, but this reads that general form anyway rather than
    assuming the single-file case seen so far is the only one that
    will ever exist) — this reads it and extracts each service's own
    `depends_on:`, the one real, owner-authored dependency fact this
    heritage did not previously observe at all.

    **Read, not parsed into a graph — same discipline as the rest of
    this class.** A service's raw `depends_on:` (Compose allows a
    plain list, or a mapping with `condition:` keys — GIGABYTE's own
    files use both, confirmed 2026-09-12) is normalized here to a
    flat tuple of the service names it names, and nothing more.
    Turning those service names into container-to-container edges
    belongs to `ComposeRuntimeCatalogBuilder`, the same boundary this
    class already keeps for `container_name`/`compose_project`.

    **Tolerant, never raising.** A project's compose file can be
    absent, unreadable, or shaped in a way this does not expect — the
    same "an ordinary state, not an exceptional one" rule
    `BeszelProvider` follows for a hub it does not control the shape
    of. Here the file is local, not a network call, but the same
    reasoning applies: a stale label pointing at a file GIGABYTE has
    since moved or deleted must not break every other project's
    observation. That project's services then simply carry no
    `depends_on` — `ComposeRuntimeCatalogBuilder` already treats
    "nothing declared" as ordinary for every other field here.
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
        """
        Read the real compose file(s) `config_files` names, and
        return each service's own `depends_on:`, normalized to a flat
        tuple of service names regardless of which of Compose's two
        forms declared it.

        **Later files win, matching Compose's own merge order** — the
        documented meaning of a comma-separated `config_files` (`-f`
        given more than once). A later file mentioning a service
        without a `depends_on:` of its own does not clear an earlier
        file's — Compose does not document override-by-absence
        either, and GOV-P-001 favours under-asserting over guessing
        at a merge rule never observed.
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
        """
        Compose accepts `depends_on:` as a plain list of service
        names, or a mapping of service name to a `condition:` block
        (`service_healthy`, etc.) — GIGABYTE's own files use both
        (`booklore`/`romm` the mapping form, most others the plain
        list). Only the names matter to this heritage; a condition is
        Compose's own startup-ordering concern, not a fact this
        observes.
        """

        if isinstance(depends_on, list):
            return tuple(name for name in depends_on if isinstance(name, str))

        if isinstance(depends_on, dict):
            return tuple(name for name in depends_on if isinstance(name, str))

        return ()

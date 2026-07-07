from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any


class DockerProvider:
    """Minimal Docker Knowledge Provider.

    This provider observes the local Docker runtime and returns
    governed raw observations without interpretation.
    """

    provider_id = "aistack.provider.docker"
    provider_name = "Docker Provider"

    def collect(self) -> dict[str, Any]:
        return {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "docker": {
                "version": self._run_json(["docker", "version", "--format", "{{json .}}"]),
                "containers": self._run_json_lines([
                    "docker", "ps", "-a",
                    "--format", "{{json .}}",
                ]),
                "images": self._run_json_lines([
                    "docker", "images",
                    "--format", "{{json .}}",
                ]),
                "networks": self._run_json_lines([
                    "docker", "network", "ls",
                    "--format", "{{json .}}",
                ]),
                "volumes": self._run_json_lines([
                    "docker", "volume", "ls",
                    "--format", "{{json .}}",
                ]),
            },
        }

    def _run_json(self, command: list[str]) -> Any:
        output = self._run(command)
        return json.loads(output) if output else None

    def _run_json_lines(self, command: list[str]) -> list[Any]:
        output = self._run(command)
        if not output:
            return []
        return [json.loads(line) for line in output.splitlines() if line.strip()]

    def _run(self, command: list[str]) -> str:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

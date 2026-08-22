from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any

from aistack.contracts.runtime_observation import RuntimeObservation

from aistack.providers.docker.log_normalization import (
    normalize_log_evidence,
)


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

    def collect_logs(
        self,
        subject: str,
        depth: int,
        state: str,
    ) -> RuntimeObservation:
        """
        Read what one container printed, and conclude nothing.

        ARC-P-012 places the boundary here: this returns lines,
        never a verdict. The experimenter this replaces called
        `container.logs()` and drew conclusions from the result
        in the same function, which is why its code does not
        migrate and its knowledge does.

        `depth` comes from the catalogue — `SignatureCatalogue.deepest`
        — so collection happens once at the deepest declared
        window and each signature then evaluates its own. One
        Docker call, not one per rule.

        `--timestamps` is passed so that every line carries its
        age regardless of what the container prints. Without it,
        a finding's evidence has a date only when the service
        happens to write one — which is how a report of eleven
        connection refusals eighteen hours old read as current on
        2026-08-22.

        `state` is supplied by the caller rather than observed
        here, because the caller has just read it from
        `collect()` and asking Docker again for every container
        would double the calls to say the same thing. It is
        passed through, not invented.

        Standard error is merged into standard output. A great
        many containers log there and nowhere else; reading only
        stdout would return an empty observation for a service
        that had been reporting a failure for hours, and the
        qualifier could not tell that from silence.
        """

        if depth <= 0:
            raise ValueError(
                f"collecting {depth} lines observes nothing"
            )

        result = subprocess.run(
            [
                "docker",
                "logs",
                "--timestamps",
                "--tail",
                str(depth),
                subject,
            ],
            check=True,
            capture_output=True,
            text=True,
            errors="replace",
        )

        return normalize_log_evidence(
            result.stdout + result.stderr,
            subject=subject,
            provider=self.provider_id,
            state=state,
            depth=depth,
            collected_at=datetime.now(timezone.utc),
        )

    def _run(self, command: list[str]) -> str:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

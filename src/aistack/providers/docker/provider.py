from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any

from aistack.contracts.resource_reading import ContainerCpuReading
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

    def collect_cpu_readings(self) -> tuple[ContainerCpuReading, ...]:
        """
        Every running container's own CPU usage, in one call.

        No container is named. `docker stats` with no argument
        reports every container Docker knows of, the same family of
        call `CpuThresholdDetector._read_cpu_percent` already makes
        for one — this is that call without the trailing name,
        which is the mechanism `STD-0300` § VS-4 criterion 4.1 asks
        for: detection without being pointed at a service.

        **Docker's field here is `Name`, singular — not `Names`,
        which is what `docker ps` prints for the same container.**
        Reading the wrong one would silently return no readings at
        all rather than an error, so it is named explicitly here
        rather than assumed to match `collect()`'s own containers.

        An unreadable `CPUPerc` is folded to `0.0`, the convention
        `CpuThresholdDetector` already carries: what could not be
        measured must never be read as busy. A line naming no
        container at all is dropped — there is nothing to attach a
        reading to.
        """

        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return ()

        readings: list[ContainerCpuReading] = []

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            name = payload.get("Name")

            if not name:
                continue

            try:
                cpu_percent = float(str(payload.get("CPUPerc", "0%")).rstrip("%"))
            except (ValueError, AttributeError):
                cpu_percent = 0.0

            readings.append(
                ContainerCpuReading(container=name, cpu_percent=cpu_percent)
            )

        return tuple(readings)

    def collect_commands(self) -> dict[str, str]:
        """
        Every container's own launch command, untruncated.

        `docker ps` truncates `Command` by default — under
        `--format '{{json .}}'` exactly as it does in the table
        view — so a flag appearing past the truncation point would
        be invisible to anything reading the field. `--no-trunc` is
        what makes this call different from `collect()`'s own
        `docker ps`, which never reads `Command` at all today; a
        second, dedicated call is made here rather than widening
        `collect()`'s output — and its own tested determinism —
        for a field only this caller needs.

        `STD-0300` § VS-4 criterion 4.3 is what this exists for:
        the reference incident's `--reload` is a property of the
        command a container was started with, not of anything it
        prints afterward.
        """

        entries = self._run_json_lines(
            ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"]
        )

        return {
            entry["Names"]: entry.get("Command", "")
            for entry in entries
            if isinstance(entry, dict) and entry.get("Names")
        }

    def _run(self, command: list[str]) -> str:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any

from aistack.contracts.container_health import health_of
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_observation import RuntimeObservation

from aistack.providers.docker.log_normalization import (
    normalize_log_evidence,
)


class DockerProvider:
    """Observe the local Docker runtime and return raw observations,
    without interpretation."""

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
        """Read the last `depth` lines one container printed, without
        drawing conclusions.

        `depth` is the deepest window any signature needs, so one call
        serves every rule.
        `--timestamps` gives every line an age even when the service
        writes none. `state` is passed through from the caller's
        `collect()`. Stderr is merged in: many containers log only there.
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
        """CPU usage of every running container (`docker stats`, one call).

        `docker stats` names the field `Name`, singular, unlike `docker ps`
        (`Names`). An unreadable `CPUPerc` reads as `0.0`, never as busy;
        a line with no name is dropped.
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

    def collect_container_states(self) -> tuple[ContainerStateReading, ...]:
        """State and health of every container, in one call (Services
        domain, `OPS-0004`).

        A container with no `Names` is dropped. A missing state becomes
        `'unknown'`, since `ContainerStateReading` refuses an empty one.
        """

        entries = self._run_json_lines(
            ["docker", "ps", "-a", "--format", "{{json .}}"]
        )

        readings: list[ContainerStateReading] = []

        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("Names"):
                continue

            readings.append(
                ContainerStateReading(
                    container=entry["Names"],
                    state=entry.get("State") or "unknown",
                    health=health_of(entry.get("Status")),
                )
            )

        return tuple(readings)

    def collect_commands(self) -> dict[str, str]:
        """Every container's launch command, untruncated.

        `docker ps` truncates `Command` even in JSON format, hiding late
        flags such as `--reload`; hence `--no-trunc`.
        """

        entries = self._run_json_lines(
            ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"]
        )

        return {
            entry["Names"]: entry.get("Command", "")
            for entry in entries
            if isinstance(entry, dict) and entry.get("Names")
        }

    def collect_process(self, container: str) -> str:
        """The `CMD` of the first process running in one container
        (`docker top`).

        Unlike `collect_commands` (the configured command), this is what
        actually runs; a wrapper or re-exec can make them differ. The table
        is split up to the `CMD` column so a command with spaces stays
        whole. Returns `""` on any failure; never raises.
        """

        try:
            result = subprocess.run(
                ["docker", "top", container], capture_output=True, text=True
            )
        except OSError:
            return ""

        if result.returncode != 0:
            return ""

        lines = result.stdout.splitlines()

        if not lines:
            return ""

        header = lines[0].split()

        if "CMD" not in header:
            return ""

        cmd_index = header.index("CMD")

        for line in lines[1:]:
            if not line.strip():
                continue

            fields = line.split(None, cmd_index)

            if len(fields) > cmd_index:
                return fields[cmd_index]

        return ""

    def _run(self, command: list[str]) -> str:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

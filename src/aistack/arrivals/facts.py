"""What to show about a container so the owner can recognize it: its image, its ports, whether it asks for the GPU."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Collection, Mapping
from typing import Any

Run = Callable[..., "subprocess.CompletedProcess[str]"]


def local_facts(names: Collection[str], run: Run = subprocess.run) -> dict[str, dict[str, Any]]:
    """
    Image and ports of the named local containers (one `docker ps -a`), and
    whether each requests a GPU (one `docker inspect` each). Anything Docker
    does not answer is simply missing: a fact is never guessed.
    """

    wanted = set(names)

    if not wanted:
        return {}

    listing = _lines(run, ["docker", "ps", "-a", "--format", "{{json .}}"])
    facts: dict[str, dict[str, Any]] = {}

    for item in listing:
        name = str(item.get("Names") or item.get("Name") or "")

        if name in wanted:
            facts[name] = {"image": item.get("Image"), "ports": item.get("Ports")}

    for name in facts:
        facts[name]["gpu"] = _asks_for_gpu(run, name)

    return facts


def remote_facts(observation: Mapping[str, Any], observed: Mapping[str, str | None]) -> dict[str, dict[str, Any]]:
    """Image and ports of the containers found on other machines, from the last network discovery."""

    facts: dict[str, dict[str, Any]] = {}

    for host_entry in (observation.get("network_docker") or {}).get("hosts") or []:
        for item in host_entry.get("containers") or []:
            name = str(item.get("Names") or item.get("Name") or item.get("ID") or "")

            if name in observed and observed[name] == host_entry.get("host"):
                facts[name] = {"image": item.get("Image"), "ports": item.get("Ports")}

    return facts


def _lines(run: Run, command: list[str]) -> list[dict[str, Any]]:
    try:
        done = run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []

    if done.returncode != 0:
        return []

    items: list[dict[str, Any]] = []

    for line in done.stdout.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue

        if isinstance(item, dict):
            items.append(item)

    return items


def _asks_for_gpu(run: Run, name: str) -> bool:
    try:
        done = run(
            ["docker", "inspect", "--format", "{{json .HostConfig.DeviceRequests}}", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return done.returncode == 0 and "gpu" in done.stdout.lower()

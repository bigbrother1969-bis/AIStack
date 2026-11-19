"""
What the containers are allowed to do to the host, read and judged
(ADR-0028 § 2, slice T2a).

Read-only, from `docker inspect` of the running containers. A container
that is privileged, holds the Docker socket, shares the host's process
or IPC namespace, adds a capability that reaches the kernel, or mounts
a sensitive host directory can take the host over if it is compromised.
Many of them are meant to (a monitor, a container manager): the owner
accepts those by name in `security.yml`, and the assessment keeps the
rest in front of him. A finding names containers and images, never a
value from a container's environment.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH, Finding

CommandRunner = Callable[..., "subprocess.CompletedProcess[str]"]

PRIVILEGED = "privileged"
DOCKER_SOCKET = "docker_socket"
HOST_NAMESPACES = "host_namespaces"
CAPABILITIES = "capabilities"
HOST_MOUNTS = "host_mounts"
KINDS = (PRIVILEGED, DOCKER_SOCKET, HOST_NAMESPACES, CAPABILITIES, HOST_MOUNTS)

_TITLES = {
    PRIVILEGED: "container(s) run privileged",
    DOCKER_SOCKET: "container(s) hold the Docker socket",
    HOST_NAMESPACES: "container(s) share the host's process or IPC namespace",
    CAPABILITIES: "container(s) add a capability that reaches the kernel",
    HOST_MOUNTS: "container(s) mount a sensitive host directory",
}
_UNKNOWN = {
    PRIVILEGED: "Whether this one needs it; a privileged container has the host's devices and kernel.",
    DOCKER_SOCKET: "Whether this one needs it; the socket gives control of every container and the host.",
    HOST_NAMESPACES: "Whether this one needs it; it sees the host's processes or shares its memory.",
    CAPABILITIES: "Whether this one needs it; these capabilities reach the kernel.",
    HOST_MOUNTS: "Whether this one needs it; it reads, and may write, the host's own files.",
}

DANGEROUS_CAPABILITIES = {"ALL", "SYS_ADMIN", "SYS_MODULE", "SYS_PTRACE", "SYS_RAWIO", "DAC_READ_SEARCH"}
# "/" is matched exactly; the others with everything under them.
SENSITIVE_MOUNTS = ("/etc", "/root", "/boot", "/var/lib/docker")


@dataclass(frozen=True)
class Container:
    name: str
    image: str
    risks: frozenset[str]
    host_network: bool


def _sensitive(source: str) -> bool:
    return source == "/" or any(source == path or source.startswith(path + "/") for path in SENSITIVE_MOUNTS)


def parse_inspect(text: str) -> list[Container] | None:
    """The containers `docker inspect` describes; None when it cannot be read."""

    try:
        entries = json.loads(text)
    except ValueError:
        return None

    if not isinstance(entries, list):
        return None

    containers: list[Container] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        host = entry.get("HostConfig") or {}
        config = entry.get("Config") or {}
        risks: set[str] = set()

        if host.get("Privileged"):
            risks.add(PRIVILEGED)
        if host.get("PidMode") == "host" or host.get("IpcMode") == "host":
            risks.add(HOST_NAMESPACES)
        if DANGEROUS_CAPABILITIES & {str(item).removeprefix("CAP_").upper() for item in (host.get("CapAdd") or [])}:
            risks.add(CAPABILITIES)

        for mount in entry.get("Mounts") or []:
            source = str((mount or {}).get("Source") or "")
            if "docker.sock" in source:
                risks.add(DOCKER_SOCKET)
            elif mount.get("Type") == "bind" and _sensitive(source):
                risks.add(HOST_MOUNTS)

        containers.append(
            Container(
                name=str(entry.get("Name") or "").lstrip("/"),
                image=str(config.get("Image") or ""),
                risks=frozenset(risks),
                host_network=host.get("NetworkMode") == "host",
            )
        )

    return containers


def read_containers(run_command: CommandRunner = subprocess.run) -> list[Container] | None:
    """The running containers, from `docker ps` then `docker inspect`; None when Docker cannot be asked."""

    try:
        listed = run_command(["docker", "ps", "-q", "--no-trunc"], capture_output=True, text=True, timeout=20)
        if listed.returncode != 0:
            return None
        identifiers = listed.stdout.split()
        if not identifiers:
            return []
        inspected = run_command(["docker", "inspect", *identifiers], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None

    return parse_inspect(inspected.stdout) if inspected.returncode == 0 else None


def _label(container: Container) -> str:
    return f"{container.name} ({container.image})" if container.image else container.name


def _listed(names: list[str], limit: int) -> tuple[str, ...]:
    return tuple(names) if len(names) <= limit else (*names[:limit], f"and {len(names) - limit} more")


def risky(containers: list[Container], definition: SecurityDefinition) -> dict[str, list[Container]]:
    """Per kind, the containers that carry the risk and are not accepted by name."""

    return {
        kind: [
            item
            for item in containers
            if kind in item.risks and item.name not in definition.accepted.get(kind, ())
        ]
        for kind in KINDS
    }


def assess_hygiene(containers: list[Container] | None, definition: SecurityDefinition) -> list[Finding]:
    if containers is None:
        return [
            Finding(
                "hygiene.unreadable",
                WATCH,
                "The containers could not be inspected",
                unknown="What the containers are allowed to do to the host.",
            )
        ]

    findings: list[Finding] = []

    for kind, found in risky(containers, definition).items():
        if found:
            findings.append(
                Finding(
                    f"hygiene.{kind}",
                    WATCH,
                    f"{len(found)} {_TITLES[kind]}",
                    _listed([_label(item) for item in found], definition.max_listed),
                    unknown=_UNKNOWN[kind],
                )
            )

    accepted = [
        f"{kind}: {item.name}"
        for kind in KINDS
        for item in containers
        if kind in item.risks and item.name in definition.accepted.get(kind, ())
    ]
    if accepted:
        findings.append(
            Finding(
                "hygiene.accepted",
                INFORMATION,
                f"{len(accepted)} risk(s) are accepted in security.yml",
                _listed(accepted, definition.max_listed),
                unknown="Whether each is still needed.",
            )
        )

    on_host = [item.name for item in containers if item.host_network]
    if on_host:
        findings.append(
            Finding(
                "hygiene.host_network",
                INFORMATION,
                f"{len(on_host)} container(s) use the host's network",
                _listed(on_host, definition.max_listed),
                unknown="Their ports are guarded by the firewall's INPUT chain, not by DOCKER-USER.",
            )
        )

    return findings


def propose_accepted(containers: list[Container], definition: SecurityDefinition) -> str:
    """The `accepted` block that would silence what the containers carry today; never applied."""

    lines: list[str] = []
    for kind, found in risky(containers, definition).items():
        if found:
            lines.append(f"  {kind}:")
            lines.extend(f"    - {name}" for name in sorted({item.name for item in found}))

    return "accepted:\n" + "\n".join(lines) + "\n" if lines else "accepted: {}\n"

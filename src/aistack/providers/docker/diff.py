from __future__ import annotations

import subprocess
from typing import Any

from aistack.providers.docker.identity import identities_of, list_running_container_names

# Periodic `docker diff` of running containers.
#
# - `docker diff` has no JSON output (plain `<A|C|D> <path>` lines) and
#   does not reliably exclude mounted-volume paths (moby/moby#3840), so
#   paths under each container's `.Mounts[].Destination` are filtered
#   here.
# - The full listing is recorded, not a computed delta: `docker diff` is
#   already cumulative since container creation.

_KIND_CODES = {"A", "C", "D"}


def collect_docker_diff(name: str) -> list[dict[str, str]]:
    """`docker diff <name>` as `{"kind": "A"|"C"|"D", "path": ...}` entries,
    sorted by path then kind.

    Returns `[]` on any failure (no daemon, no such container); never
    raises.
    """

    try:
        result = subprocess.run(
            ["docker", "diff", name], capture_output=True, text=True
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    changes: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        kind, separator, path = line.partition(" ")
        if not separator or kind not in _KIND_CODES or not path:
            continue
        changes.append({"kind": kind, "path": path})

    # `docker diff` line order is not stable between calls, even when the
    # set of changes is identical; sort so write-on-change comparisons
    # see no spurious change.
    changes.sort(key=lambda change: (change["path"], change["kind"]))

    return changes


def _under_any_mount(path: str, mount_destinations: tuple[str, ...]) -> bool:
    """True when `path` is a mount destination or below one (a sibling
    sharing only a prefix does not match)."""

    for mount in mount_destinations:
        stripped = mount.rstrip("/")
        if path == stripped or path.startswith(f"{stripped}/"):
            return True

    return False


def collect_running_container_diffs() -> list[dict[str, Any]]:
    """One cycle: `{"subject", "changes"}` for each running container, with
    paths under its mounts removed.

    A container that stopped between `docker ps` and `docker inspect` is
    absent. `changes` may be empty; `record_docker_diff` decides whether
    to write.
    """

    names = list_running_container_names()
    identities = identities_of(names)

    results: list[dict[str, Any]] = []
    for identity in identities:
        raw_changes = collect_docker_diff(identity.name)
        kept = [
            change
            for change in raw_changes
            if not _under_any_mount(change["path"], identity.mount_destinations)
        ]
        results.append({"subject": identity.stable_subject, "changes": kept})

    return results

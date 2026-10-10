from __future__ import annotations

import subprocess
from typing import Any, MutableMapping

from aistack.providers.docker.identity import identities_of, list_running_container_names

# Declared once so `aistack.providers.docker.events` can recognise these
# `docker exec` probes and leave them out of the event stream.
DPKG_QUERY_COMMAND: tuple[str, ...] = ("dpkg-query", "-W", "-f=${Package}\t${Version}\n")
APK_DB_COMMAND: tuple[str, ...] = ("cat", "/lib/apk/db/installed")

# Package inventory of running containers:
# 1. `dpkg-query -W -f=...` first. No shell is involved on either side of
#    `docker exec`, so the `${...}` placeholders need no escaping.
# 2. Alpine fallback: read `/lib/apk/db/installed` (documented `P:`/`V:`
#    records) rather than parse `apk info -v`, which joins name and
#    version with no reliable separator.
# 3. When neither answers, `mechanism` is `"none"`, distinct from an
#    inventory that found zero packages.


def _dpkg_packages(name: str) -> list[dict[str, str]] | None:
    """Packages listed by `dpkg-query` in the container, as
    `{"name", "version"}` entries sorted by name (for stable comparisons).

    `None`, not `[]`, on any failure, meaning "try the next mechanism".
    """

    try:
        result = subprocess.run(
            ["docker", "exec", name, *DPKG_QUERY_COMMAND],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    packages: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        package_name, separator, version = line.partition("\t")
        if not separator or not package_name:
            continue
        packages.append({"name": package_name, "version": version})

    packages.sort(key=lambda entry: entry["name"])
    return packages


def _parse_apk_installed(content: str) -> list[dict[str, str]]:
    """Parse Alpine's `/lib/apk/db/installed`: blank-line-separated
    records of `X:` fields. Only `P:` (name) and `V:` (version) are read;
    a record missing either is skipped."""

    packages: list[dict[str, str]] = []
    current_name: str | None = None
    current_version: str | None = None

    def _flush() -> None:
        if current_name and current_version:
            packages.append({"name": current_name, "version": current_version})

    for line in content.splitlines():
        if line.startswith("P:"):
            current_name = line[2:]
        elif line.startswith("V:"):
            current_version = line[2:]
        elif not line.strip():
            _flush()
            current_name = None
            current_version = None

    _flush()

    packages.sort(key=lambda entry: entry["name"])
    return packages


def _apk_packages(name: str) -> list[dict[str, str]] | None:
    """Packages from the container's apk database; `None`, not `[]`, on any
    failure (e.g. not Alpine)."""

    try:
        result = subprocess.run(
            ["docker", "exec", name, *APK_DB_COMMAND],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return _parse_apk_installed(result.stdout)


def collect_package_inventory(name: str) -> dict[str, Any]:
    """One container's inventory: `{"mechanism": "dpkg" | "apk" | "none",
    "packages": [{"name", "version"}, ...]}`."""

    dpkg_packages = _dpkg_packages(name)
    if dpkg_packages is not None:
        return {"mechanism": "dpkg", "packages": dpkg_packages}

    apk_packages = _apk_packages(name)
    if apk_packages is not None:
        return {"mechanism": "apk", "packages": apk_packages}

    return {"mechanism": "none", "packages": []}


def collect_running_container_packages() -> list[dict[str, Any]]:
    """One cycle: `{"subject", "mechanism", "packages"}` for each running
    container `docker inspect` could still resolve."""

    names = list_running_container_names()
    identities = identities_of(names)

    results: list[dict[str, Any]] = []
    for identity in identities:
        inventory = collect_package_inventory(identity.name)
        results.append(
            {
                "subject": identity.stable_subject,
                "mechanism": inventory["mechanism"],
                "packages": inventory["packages"],
            }
        )

    return results


def collect_packages_on_image_change(
    seen_digests: MutableMapping[str, str],
) -> list[dict[str, Any]]:
    """Like `collect_running_container_packages`, but only for containers
    whose image digest changed since they were last inventoried.

    Packages come from the image, so this avoids a `docker exec` per
    container on every poll. `seen_digests` (subject -> digest) is updated
    in place; an empty mapping inventories every container once. A
    container with no digest is inventoried every time. Trade-off: a
    package installed by hand without an image change is not seen until
    the image changes or the monitor restarts.
    """

    names = list_running_container_names()
    identities = identities_of(names)
    results: list[dict[str, Any]] = []

    for identity in identities:
        digest = identity.image_digest
        if digest and seen_digests.get(identity.stable_subject) == digest:
            continue
        inventory = collect_package_inventory(identity.name)
        results.append(
            {
                "subject": identity.stable_subject,
                "mechanism": inventory["mechanism"],
                "packages": inventory["packages"],
            }
        )
        if digest:
            seen_digests[identity.stable_subject] = digest

    return results

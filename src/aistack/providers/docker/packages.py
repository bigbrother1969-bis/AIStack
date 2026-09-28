from __future__ import annotations

import subprocess
from typing import Any

from aistack.providers.docker.identity import identities_of, list_running_container_names

# 1.5's fourth and last named collector (inventaire des paquets),
# explicitly deferred past 1.5.0 (`ADR-0011` § 22's own closing note)
# and cadré for 1.5.1, 2026-09-28. Three decisions, confirmed with the
# owner (`AskUserQuestion`) before any code, grounded in real research
# (`ARC-P-006`) rather than assumed from either tool's own display
# output:
#
# 1. **`docker exec` + `dpkg-query` first.** Verified against `dpkg-
#    query(1)`'s own manual page (man7.org): `-W` ("list") with a
#    custom `-f` format string prints exactly what this collector
#    needs, one package per line, with no parsing of a human-oriented
#    table required — `-f='${Package}\t${Version}\n'`, passed as a
#    single argv entry (`subprocess.run` never goes through a shell,
#    on either side of `docker exec`, so dpkg-query itself resolves
#    the `${...}` placeholders — nothing here needs to escape them).
# 2. **`/lib/apk/db/installed`, not `apk info -v`, as the Alpine
#    fallback.** Verified against the Alpine wiki's own `Apk_spec`
#    page: the installed-package database is a plain, documented,
#    line-prefixed, blank-line-separated record format (`P:` the
#    package name, `V:` its version, among other fields this collector
#    does not need). `apk info -v`'s own display output was considered
#    and rejected: it concatenates a package's name and version into
#    one string with no declared separator contract, and splitting it
#    back apart reliably is exactly the kind of guess `ARC-P-006`
#    forbids when a structured, documented alternative already exists.
# 3. **Neither mechanism answering is itself recorded as a fact**
#    (`mechanism = "none"`), never silently treated as "zero packages"
#    — a container with no package manager this collector knows how to
#    query is a different observation from one a real inventory found
#    empty, the same restraint `aistack.providers.docker.digest`'s own
#    module already holds for an absent `.Image` (skipped, never
#    recorded as `""`) — here there is nothing to skip (`mechanism` is
#    always known), but the two cases stay distinguishable in the
#    stream itself rather than collapsed.
#
# **Running containers only, the shared identity module, unchanged —**
# the same restriction and the same shared `aistack.providers.docker
# .identity` module every 1.5 collector already holds, for the same
# reasons those modules' own comments already give.


def _dpkg_packages(name: str) -> list[dict[str, str]] | None:
    """
    `docker exec <name> dpkg-query -W -f='${Package}\\t${Version}\\n'`,
    parsed into `{"name", "version"}` entries, sorted by name for a
    deterministic write-on-change comparison — the same reasoning
    `aistack.providers.docker.diff.collect_docker_diff`'s own sort
    already gives, applied here from the start rather than found as a
    production incident later, since nothing in dpkg-query's own
    contract promises a stable listing order either.

    `None` — not `[]` — on any failure (no daemon, no such container,
    dpkg-query not installed in it): a real, empty inventory (`[]`)
    and "this mechanism did not answer, try the next one" are
    different outcomes this collector's own caller needs to tell
    apart.
    """

    try:
        result = subprocess.run(
            ["docker", "exec", name, "dpkg-query", "-W", "-f=${Package}\t${Version}\n"],
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
    """
    Alpine's own `/lib/apk/db/installed` format (the Alpine wiki's own
    `Apk_spec` page): one record per package, each line prefixed by a
    single-letter field code, records separated by a blank line. Only
    `P:` (package name) and `V:` (version) are read; every other field
    this format carries (`A:`, `S:`, `I:`, ...) is not this collector's
    concern. A record missing either field is skipped rather than
    recorded with an empty name or version — the same restraint this
    module's own module comment gives for an unresolved mechanism as a
    whole, applied here to one malformed record within an otherwise
    real answer.
    """

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
    """
    `docker exec <name> cat /lib/apk/db/installed`, parsed by
    `_parse_apk_installed`. `None` — not `[]` — on any failure, the
    same distinction `_dpkg_packages` already draws and for the same
    reason: this container may simply have no such file (it is not
    Alpine-based, or uses neither package manager this collector
    knows), which is "try the next mechanism," not "zero packages."
    """

    try:
        result = subprocess.run(
            ["docker", "exec", name, "cat", "/lib/apk/db/installed"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return _parse_apk_installed(result.stdout)


def collect_package_inventory(name: str) -> dict[str, Any]:
    """
    One container's own package inventory: `dpkg-query` tried first,
    `/lib/apk/db/installed` as the fallback, `"none"` — with an empty
    list — when neither answered. `{"mechanism": "dpkg" | "apk" |
    "none", "packages": [{"name", "version"}, ...]}` — cadrage
    decisions 1, 2, and 3 above, applied together, in that order.
    """

    dpkg_packages = _dpkg_packages(name)
    if dpkg_packages is not None:
        return {"mechanism": "dpkg", "packages": dpkg_packages}

    apk_packages = _apk_packages(name)
    if apk_packages is not None:
        return {"mechanism": "apk", "packages": apk_packages}

    return {"mechanism": "none", "packages": []}


def collect_running_container_packages() -> list[dict[str, Any]]:
    """
    One cycle: every running container's own stable identity (§ 3)
    paired with its own current package inventory —
    `{"subject": ..., "mechanism": ..., "packages": [...]}` per
    container `docker inspect` could still resolve at the moment this
    ran (`identities_of`'s own contract, the same race every other 1.5
    collector already documents: a container that stopped between
    `docker ps` and here is simply absent, never an error).
    """

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

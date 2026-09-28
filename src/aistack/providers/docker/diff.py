from __future__ import annotations

import subprocess
from typing import Any

from aistack.providers.docker.identity import identities_of, list_running_container_names

# 1.5's second collector (`docker diff` périodique), cadrage
# 2026-09-28. Four decisions, all confirmed with the owner before any
# code:
#
# 1. **Running containers only** — `list_running_container_names`
#    (`docker ps`, not `docker ps -a`): a stopped container's
#    filesystem is not drifting under active use, and `docker diff`
#    against one still works but reports nothing new happening; the
#    owner chose not to poll that.
# 2. **Volume/mount paths filtered at the collector level.** Verified
#    2026-09-28 against Docker's own reference
#    (https://docs.docker.com/engine/reference/commandline/diff/) and
#    a real `moby/moby` issue (#3840): `docker diff` takes no
#    `--format`/JSON option (plain-text `<A|C|D> <path>` lines only),
#    and its own exclusion of mounted-volume paths is not reliable —
#    a bind mount is indistinguishable from a real filesystem change
#    via `stat()` across storage drivers, a maintainer's own
#    clarification on that issue explains. So this collector filters
#    explicitly, using each container's own `docker inspect`-reported
#    `.Mounts[].Destination` (`aistack.providers.docker.identity
#    .ContainerIdentity.mount_destinations`), rather than trusting
#    `docker diff` itself or deferring to the graph-side, statically-
#    declared `aistack.timemachine.projection.filter.filter_fact`
#    (R2's own mechanism, built for a *different* case — a path whose
#    root is declared once, config-side, not a per-container mount
#    Docker itself already knows).
# 3. **Shared identity module, factored out now** —
#    `aistack.providers.docker.identity`, reused by this collector and
#    by the two still to come (dérive du digest, inventaire des
#    paquets), rather than three copies of the same rule against the
#    same `docker inspect` shape.
# 4. **Write the full current diff listing, not an invented
#    incremental delta.** `docker diff` itself is already cumulative
#    since container creation, not since the last poll — inventing a
#    delta on top would mean this collector tracking its own separate
#    "since I last looked" state, duplicating exactly what `docker
#    diff` already does for free, and risking drift from what Docker
#    itself would report if asked directly.

_KIND_CODES = {"A", "C", "D"}


def collect_docker_diff(name: str) -> list[dict[str, str]]:
    """
    `docker diff <name>`, parsed into `{"kind": "A"|"C"|"D", "path":
    ...}` entries, sorted by `path` (then `kind`) — **not** Docker's
    own reported order, deliberately, since 2026-09-28 (see the sort
    call's own comment below for the production incident that found
    this needed) — plain-text `<A|C|D> <path>` lines, confirmed
    2026-09-28 against Docker's own reference: no `--format`/JSON
    option exists for this command, unlike `docker events`
    (`aistack.providers.docker.events.collect_docker_events`).

    `[]` on any failure — no daemon, no such container, malformed
    output — the same convention every collector in this package
    already holds (`collect_docker_events`,
    `aistack.providers.docker.identity.list_running_container_names`):
    what could not be observed is reported as nothing observed, never
    raised.
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

    # Found in production, 2026-09-28, the day this monitor was first
    # enabled on GIGABYTE: `docker diff`'s own line order is not
    # stable across repeated calls against the same container, even
    # when the underlying set of changes is identical — a diagnostic
    # against the real host's own recorded history showed 30 of 32
    # multi-snapshot subjects holding the exact same set of changes,
    # re-ordered, on every poll (one genuine content change, in a
    # container actively writing new session files, was the only real
    # exception). `docker diff` itself gives no documented ordering
    # guarantee (this heritage's own research before building this
    # collector, § *Decision* above, found none) — Docker's own
    # overlay-filesystem enumeration order is the plausible cause,
    # itself not guaranteed stable by any storage driver. Sorted here,
    # once, at the source, rather than left to `aistack.providers
    # .docker.diff_history.has_changed`'s own comparison: order was
    # never itself a fact worth keeping (unlike `docker events`, whose
    # order is real chronology `aistack.providers.docker.events` never
    # reorders), so canonicalising it here makes both the stored
    # content and the "did anything actually change" comparison
    # deterministic, without asking every future caller of `changes`
    # to remember to do it themselves.
    changes.sort(key=lambda change: (change["path"], change["kind"]))

    return changes


def _under_any_mount(path: str, mount_destinations: tuple[str, ...]) -> bool:
    """
    `True` when `path` falls under one of a container's own declared
    mount destinations — decision 2 above, applied to one path:
    matches the destination itself and anything below it, but never a
    sibling that merely shares its prefix (`aistack.timemachine
    .projection.filter.is_user_data_path`'s own matching rule, the
    same shape, applied here at collection time instead of at
    projection time — a deliberate difference, since a mount path is
    a real, per-container fact `docker inspect` already states, not a
    statically-declared root).
    """

    for mount in mount_destinations:
        stripped = mount.rstrip("/")
        if path == stripped or path.startswith(f"{stripped}/"):
            return True

    return False


def collect_running_container_diffs() -> list[dict[str, Any]]:
    """
    One cycle: every running container's own stable identity (§ 3)
    paired with its current `docker diff`, with every path under one
    of that container's own declared mounts already filtered out —
    decisions 1 and 2 above, applied together.

    One entry per container `docker inspect` could still resolve at
    the moment this ran (`identities_of`'s own contract — a container
    that stopped between `docker ps` and here is simply absent, never
    an error): `{"subject": ..., "changes": [{"kind", "path"}, ...]}`.
    `changes` may be empty — a container `docker diff` reports nothing
    new for is still a real observation, not withheld (`aistack
    .providers.docker.diff_history.record_docker_diff`'s own
    write-on-change contract decides whether that is worth a new
    write, not this function).
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

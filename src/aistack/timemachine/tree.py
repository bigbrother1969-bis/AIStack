"""
The network tree — 1.4's own contribution to the Time Machine
(`ADR-0011` § 18, roadmap `ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.4,
"Plan des rayonnages" in the library analogy).

**Réseau → Hôte → Stack → Conteneur, from the same real catalogs
every other screen already reads — not from the graph.** `timemachine_
ui`'s node/stream views read `OxigraphGraphStore` because a stream's
own history is exactly what the graph projects; the Docker/Compose
hierarchy is not itself in the graph (`ADR-0011` § *Open Points*
leaves the raw streams' own business schema, container-level
structure included, to 1.5) — it already exists as real, live,
governed data via `DockerRuntimeCatalogBuilder`/
`ComposeRuntimeCatalogBuilder`, the same builders `architecture_
render` already calls. This module takes their output — a `Catalog`,
built by the caller exactly the way `architecture_render.main` already
builds one — and orders it into a tree, the same "flat, depth-first,
every parent immediately before its own descendants" idiom
`MediaTreeViewEngine` already established for a foldable list a
surface can render in one pass without knowing the tree shape.

**Historique is a separate concern, answered from the graph** — see
`historique_names` below — because whether a name has real history to
show is a fact about the *graph*, not about the catalog this module
orders.

**No Stack level for a remote host, ever** (owner's decision,
2026-09-28, 1.4 cadrage): a remote host is known only through an
explicit `network_docker_discover` scan, itself only `docker ps`, no
compose file read over SSH — inventing a Stack grouping there from
nothing observed would be exactly the guessed infrastructure
`ARC-P-006` forbids. A remote host's containers attach directly to
their host node.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aistack.kernel.catalog import Catalog
from aistack.timemachine.graph import GraphStore
from aistack.timemachine.iri import subject_iri
from aistack.timemachine.vocabulary import AISTACK_EXPLAINS, AISTACK_STABLE_SUBJECT


@dataclass(frozen=True)
class NetworkTreeNode:
    """
    One row of the flat, depth-first ordering `build_network_tree`
    returns — same shape and same reasoning as
    `aistack.catalog.views.media.tree.CatalogViewItem`'s own
    `has_children` field: a surface draws a fold control without
    looking ahead in the list.
    """

    id: str
    label: str
    kind: str  # "network" | "host" | "stack" | "container"
    parent_id: str | None
    depth: int
    has_children: bool


@dataclass(frozen=True)
class RemoteHost:
    """One host `parse_remote_hosts` found in a stored scan — a real
    IP address (or hostname, whatever the scan's own `host` field
    said) and the container names `docker ps` reported there, never a
    stack grouping (no compose file read over SSH)."""

    host: str
    containers: tuple[str, ...]


def parse_remote_hosts(observation: dict[str, Any]) -> tuple[RemoteHost, ...]:
    """
    `NetworkDockerDiscoveryProvider.collect()`'s own JSON shape,
    exactly as `NetworkDockerObservationArtifactGenerator` wrote it
    and `aistack.history` hands back the latest snapshot of — never
    a live scan triggered from here (that collector is deliberately
    "never triggered automatically", `NetworkDockerDiscoveryProvider`'s
    own docstring). A container without a resolvable name (`docker ps
    --format '{{json .}}'`'s own `Names` field, blank or absent) is
    skipped and never invented.

    Tolerant, not strict — the same reasoning
    `aistack.architecture.dependency_graph.build_dependency_graph`
    already gives for reading a governed `Catalog`: a missing or
    oddly-shaped section degrades to "nothing observed here" rather
    than raising, since this reads a machine-written artifact, not a
    hand-edited file whose typo is the owner's own mistake to fix.
    """

    network_docker = observation.get("network_docker")
    if not isinstance(network_docker, dict):
        return ()

    hosts_data = network_docker.get("hosts")
    if not isinstance(hosts_data, list):
        return ()

    hosts: list[RemoteHost] = []

    for entry in hosts_data:
        if not isinstance(entry, dict):
            continue

        host = str(entry.get("host") or "").strip()
        if not host:
            continue

        containers_data = entry.get("containers")
        names = (
            _container_names(containers_data)
            if isinstance(containers_data, list)
            else ()
        )

        hosts.append(RemoteHost(host=host, containers=names))

    hosts.sort(key=lambda remote: remote.host)
    return tuple(hosts)


def _container_names(containers_data: list[Any]) -> tuple[str, ...]:
    names: set[str] = set()

    for raw in containers_data:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("Names") or "").strip()
        if name:
            names.add(name)

    return tuple(sorted(names))


def build_network_tree(
    *,
    cidr: str,
    local_host_label: str,
    docker_catalog: Catalog,
    compose_catalog: Catalog,
    remote_hosts: tuple[RemoteHost, ...] = (),
) -> list[NetworkTreeNode]:
    """
    `Réseau ⊃ Hôte ⊃ Stack ⊃ Conteneur`, flat and depth-first, ready
    for a foldable list.

    `docker_catalog`/`compose_catalog` are built by the caller exactly
    as `architecture_render.main` already builds them (live
    `DockerRuntimeCatalogBuilder`/`ComposeRuntimeCatalogBuilder`, this
    module never collects anything itself) — the local host's own real
    Stack/Container structure. A local container that belongs to no
    Compose project (started by hand, or by a tool nothing here
    curates) attaches directly under the local host, same "no
    invented grouping" rule the remote hosts already follow.
    """

    nodes: list[NetworkTreeNode] = [
        NetworkTreeNode(
            id="network",
            label=cidr,
            kind="network",
            parent_id=None,
            depth=0,
            has_children=bool(local_host_label) or bool(remote_hosts),
        )
    ]

    local_host_id = f"host:{local_host_label}"
    grouped_containers: set[str] = set()

    stacks_by_project: list[tuple[str, list[NetworkTreeNode]]] = []
    for item in compose_catalog.items:
        if item.kind != "compose-project":
            continue

        container_names = _split(item.metadata.get("containers", ""))
        grouped_containers.update(container_names)

        stack_id = f"stack:{local_host_label}:{item.id}"
        containers = sorted(container_names)
        stacks_by_project.append(
            (
                item.id,
                [
                    NetworkTreeNode(
                        id=f"container:{local_host_label}:{name}",
                        label=name,
                        kind="container",
                        parent_id=stack_id,
                        depth=3,
                        has_children=False,
                    )
                    for name in containers
                ],
            )
        )

    stacks_by_project.sort(key=lambda entry: entry[0])

    orphan_containers = sorted(
        item.id
        for item in docker_catalog.items
        if item.kind == "container" and item.id not in grouped_containers
    )

    local_children_count = len(stacks_by_project) + len(orphan_containers)

    nodes.append(
        NetworkTreeNode(
            id=local_host_id,
            label=local_host_label,
            kind="host",
            parent_id="network",
            depth=1,
            has_children=local_children_count > 0,
        )
    )

    for project_name, container_nodes in stacks_by_project:
        stack_id = f"stack:{local_host_label}:{project_name}"
        nodes.append(
            NetworkTreeNode(
                id=stack_id,
                label=project_name,
                kind="stack",
                parent_id=local_host_id,
                depth=2,
                has_children=bool(container_nodes),
            )
        )
        nodes.extend(container_nodes)

    for name in orphan_containers:
        nodes.append(
            NetworkTreeNode(
                id=f"container:{local_host_label}:{name}",
                label=name,
                kind="container",
                parent_id=local_host_id,
                depth=2,
                has_children=False,
            )
        )

    for remote in remote_hosts:
        host_id = f"host:{remote.host}"
        nodes.append(
            NetworkTreeNode(
                id=host_id,
                label=remote.host,
                kind="host",
                parent_id="network",
                depth=1,
                has_children=bool(remote.containers),
            )
        )
        for name in remote.containers:
            nodes.append(
                NetworkTreeNode(
                    id=f"container:{remote.host}:{name}",
                    label=name,
                    kind="container",
                    parent_id=host_id,
                    depth=2,
                    has_children=False,
                )
            )

    return nodes


def _split(raw: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in raw.split(",") if name.strip())


def historique_names(store: GraphStore, candidate_names: frozenset[str]) -> frozenset[str]:
    """
    Which of `candidate_names` (a host, stack or container label) has
    at least one real fact attached in the graph today — either as an
    `aistack:stableSubject` on some observation entity (the CPU
    priority decisions for `jellyfin` are today's one real case), or
    as the subject an Explication `aistack:explains` (a commit scope,
    a `pra_tests.yml` entry, an `explain` answer, a `claude/` note).

    **Honestly narrow today, by design** (1.4 cadrage, 2026-09-28):
    per-container passive collectors are 1.5's own work, so most
    container names will not appear here yet — the caller shows that
    plainly rather than hiding the gap, the same discipline
    `timemachine_ui`'s v1 already holds against the four richer
    maquettes (`ADR-0011` § *Open Points*).

    **Two batched queries, never one per name** — `VALUES` lets the
    whole candidate set travel in a single `SELECT`, the same reason
    `explications_import_commits`/`pra_tests` importers batch their
    own idempotency checks rather than querying per subject.
    """

    if not candidate_names:
        return frozenset()

    stable_matches = frozenset(
        row["name"]
        for row in store.query(
            "SELECT DISTINCT ?name WHERE { "
            f"VALUES ?name {{ {_literal_values(candidate_names)} }} "
            f"?entity <{AISTACK_STABLE_SUBJECT}> ?name . "
            "}"
        )
        if row["name"] is not None
    )

    subject_iri_by_name = {subject_iri(name): name for name in candidate_names}

    explained_matches = frozenset(
        subject_iri_by_name[row["subj"]]
        for row in store.query(
            "SELECT DISTINCT ?subj WHERE { "
            f"VALUES ?subj {{ {_iri_values(subject_iri_by_name)} }} "
            f"?entity <{AISTACK_EXPLAINS}> ?subj . "
            "}"
        )
        if row["subj"] in subject_iri_by_name
    )

    return stable_matches | explained_matches


def historique_entity_iri(store: GraphStore, name: str) -> str | None:
    """
    A real entity IRI to link `name` to, once `historique_names` has
    already said it has one — never called for the full candidate set
    (that is exactly the per-name querying `historique_names` itself
    avoids); the caller invokes this only for the small number of
    names a prior `historique_names` call already confirmed match
    (in practice today, zero or one).

    Checks the same two predicates, in the same order, and returns the
    first entity either finds — `aistack:stableSubject` (a literal
    match) before `aistack:explains` (an IRI match via `subject_iri`).
    `None` only if the store changed between the two calls (a rebuild
    landing mid-request, `ADR-0011` § *Decision* 13's own read-only
    handle is opened fresh per request but not held across two calls
    of this module) — the caller degrades to an unlinked label rather
    than treating this as an error.
    """

    stable_rows = list(
        store.query(
            "SELECT ?entity WHERE { "
            f"?entity <{AISTACK_STABLE_SUBJECT}> {_sparql_literal(name)} . "
            "} LIMIT 1"
        )
    )
    if stable_rows and stable_rows[0]["entity"] is not None:
        return stable_rows[0]["entity"]

    explain_rows = list(
        store.query(
            "SELECT ?entity WHERE { "
            f"?entity <{AISTACK_EXPLAINS}> <{subject_iri(name)}> . "
            "} LIMIT 1"
        )
    )
    if explain_rows and explain_rows[0]["entity"] is not None:
        return explain_rows[0]["entity"]

    return None


def _literal_values(names: frozenset[str]) -> str:
    return " ".join(_sparql_literal(name) for name in sorted(names))


def _iri_values(subject_iri_by_name: dict[str, str]) -> str:
    return " ".join(f"<{iri}>" for iri in sorted(subject_iri_by_name))


def _sparql_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

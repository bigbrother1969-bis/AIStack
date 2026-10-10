"""
The network tree of the Time Machine (`ADR-0011` § 18): Réseau → Hôte
→ Stack → Conteneur.

Built from the Docker and Compose catalogs, not from the graph, which
does not hold that hierarchy. The result is flat and depth-first, each
parent immediately before its descendants, for a foldable list.
Whether a name has history is answered from the graph by
`historique_names`.

A remote host has no Stack level: it is known only from a
`network_docker_discover` scan (`docker ps`, no compose file read), so
its containers attach directly to the host.
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
    One row of `build_network_tree`'s flat ordering. `has_children`
    lets a surface draw a fold control without looking ahead.
    """

    id: str
    label: str
    kind: str  # "network" | "host" | "stack" | "container"
    parent_id: str | None
    depth: int
    has_children: bool


@dataclass(frozen=True)
class RemoteHost:
    """A host from a stored scan (address or hostname, as scanned) and
    the container names `docker ps` reported there."""

    host: str
    containers: tuple[str, ...]


def parse_remote_hosts(observation: dict[str, Any]) -> tuple[RemoteHost, ...]:
    """
    Remote hosts from a stored `NetworkDockerDiscoveryProvider`
    observation (never a live scan), sorted by host.

    Tolerant: a missing or malformed section yields nothing rather than
    raising, and a container without a `Names` value is skipped.
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

    The caller builds `docker_catalog`/`compose_catalog` (as
    `architecture_render.main` does). A local container in no Compose
    project attaches directly under the local host.
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
    Which of `candidate_names` (host, stack or container labels) has
    at least one fact in the graph, either as an `aistack:stableSubject`
    or as the subject an Explication `aistack:explains`.

    Two batched `VALUES` queries, never one per name.
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
    An entity IRI to link `name` to, for a name `historique_names`
    already matched (one query per name, so not for the full set).

    Tries `aistack:stableSubject` then `aistack:explains`. `None` only
    if a rebuild changed the store between the two calls; the caller
    then shows an unlinked label.
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

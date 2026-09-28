from __future__ import annotations

from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.timemachine import OxigraphGraphStore
from aistack.timemachine.iri import subject_iri
from aistack.timemachine.tree import (
    RemoteHost,
    build_network_tree,
    historique_entity_iri,
    historique_names,
    parse_remote_hosts,
)
from aistack.timemachine.vocabulary import (
    AISTACK_EXPLAINS,
    AISTACK_STABLE_SUBJECT,
    PROV_ENTITY,
    RDF_TYPE,
)


def _docker_catalog(container_ids: tuple[str, ...]) -> Catalog:
    return Catalog(
        catalog_id="docker-runtime",
        title="Docker Runtime Catalog",
        items=tuple(
            CatalogItem(id=cid, label=cid, kind="container") for cid in container_ids
        ),
    )


def _compose_catalog(projects: dict[str, tuple[str, ...]]) -> Catalog:
    return Catalog(
        catalog_id="compose-runtime",
        title="Docker Compose Runtime Catalog",
        items=tuple(
            CatalogItem(
                id=name,
                label=name,
                kind="compose-project",
                metadata={"containers": ",".join(containers)},
            )
            for name, containers in projects.items()
        ),
    )


def test_build_network_tree_orders_network_host_stack_container_depth_first():
    docker_catalog = _docker_catalog(("jellyfin", "jellyfin-db"))
    compose_catalog = _compose_catalog({"jellyfin": ("jellyfin", "jellyfin-db")})

    nodes = build_network_tree(
        cidr="192.168.1.0/24",
        local_host_label="GIGABYTE",
        docker_catalog=docker_catalog,
        compose_catalog=compose_catalog,
    )

    assert [node.id for node in nodes] == [
        "network",
        "host:GIGABYTE",
        "stack:GIGABYTE:jellyfin",
        "container:GIGABYTE:jellyfin",
        "container:GIGABYTE:jellyfin-db",
    ]

    network, host, stack, container_a, container_b = nodes
    assert network.kind == "network" and network.depth == 0 and network.parent_id is None
    assert host.kind == "host" and host.depth == 1 and host.parent_id == "network"
    assert stack.kind == "stack" and stack.depth == 2 and stack.parent_id == "host:GIGABYTE"
    assert container_a.kind == "container"
    assert container_a.depth == 3
    assert container_a.parent_id == "stack:GIGABYTE:jellyfin"
    assert container_a.has_children is False
    assert stack.has_children is True
    assert host.has_children is True


def test_a_container_in_no_compose_project_attaches_directly_under_its_host():
    docker_catalog = _docker_catalog(("standalone",))
    compose_catalog = _compose_catalog({})

    nodes = build_network_tree(
        cidr="192.168.1.0/24",
        local_host_label="GIGABYTE",
        docker_catalog=docker_catalog,
        compose_catalog=compose_catalog,
    )

    orphan = next(node for node in nodes if node.id == "container:GIGABYTE:standalone")
    assert orphan.kind == "container"
    assert orphan.depth == 2
    assert orphan.parent_id == "host:GIGABYTE"


def test_remote_hosts_get_no_stack_level_ever():
    """Owner's own decision, 1.4 cadrage 2026-09-28: no compose file
    is ever read over SSH, so no Stack node is invented for a remote
    host — its containers attach directly to it."""

    docker_catalog = _docker_catalog(())
    compose_catalog = _compose_catalog({})
    remote_hosts = (RemoteHost(host="192.168.1.53", containers=("pihole",)),)

    nodes = build_network_tree(
        cidr="192.168.1.0/24",
        local_host_label="GIGABYTE",
        docker_catalog=docker_catalog,
        compose_catalog=compose_catalog,
        remote_hosts=remote_hosts,
    )

    remote_host_node = next(node for node in nodes if node.id == "host:192.168.1.53")
    assert remote_host_node.kind == "host"
    assert remote_host_node.parent_id == "network"

    remote_container = next(
        node for node in nodes if node.id == "container:192.168.1.53:pihole"
    )
    assert remote_container.parent_id == "host:192.168.1.53"
    assert remote_container.kind == "container"
    assert not any(node.kind == "stack" and "192.168.1.53" in node.id for node in nodes)


def test_an_empty_catalog_still_yields_the_network_and_host_nodes():
    nodes = build_network_tree(
        cidr="192.168.1.0/24",
        local_host_label="GIGABYTE",
        docker_catalog=_docker_catalog(()),
        compose_catalog=_compose_catalog({}),
    )

    assert [node.id for node in nodes] == ["network", "host:GIGABYTE"]
    assert nodes[1].has_children is False


def test_parse_remote_hosts_reads_the_real_provider_shape():
    observation = {
        "network_docker": {
            "cidr": "192.168.1.0/24",
            "hosts": [
                {
                    "host": "192.168.1.53",
                    "ssh_username": "pi",
                    "containers": [
                        {"Names": "pihole"},
                        {"Names": "unifi"},
                        {"Names": "pihole"},
                    ],
                },
                {"host": "192.168.1.99", "ssh_username": "pi-hole", "containers": []},
            ],
        }
    }

    hosts = parse_remote_hosts(observation)

    assert hosts == (
        RemoteHost(host="192.168.1.53", containers=("pihole", "unifi")),
        RemoteHost(host="192.168.1.99", containers=()),
    )


def test_parse_remote_hosts_skips_an_entry_with_no_resolvable_host_name():
    observation = {
        "network_docker": {
            "hosts": [
                {"ssh_username": "pi", "containers": []},
                {"host": "  ", "containers": []},
            ]
        }
    }

    assert parse_remote_hosts(observation) == ()


def test_parse_remote_hosts_tolerates_a_missing_or_malformed_section():
    assert parse_remote_hosts({}) == ()
    assert parse_remote_hosts({"network_docker": "not-a-mapping"}) == ()
    assert parse_remote_hosts({"network_docker": {"hosts": "not-a-list"}}) == ()


def test_historique_names_finds_a_stable_subject_match():
    store = OxigraphGraphStore()
    store.add("urn:e:1", RDF_TYPE, PROV_ENTITY)
    store.add("urn:e:1", AISTACK_STABLE_SUBJECT, _literal("jellyfin"))

    assert historique_names(store, frozenset({"jellyfin", "unifi"})) == frozenset(
        {"jellyfin"}
    )


def test_historique_names_finds_an_explains_match():
    store = OxigraphGraphStore()
    store.add("urn:e:1", AISTACK_EXPLAINS, subject_iri("kernel"))

    assert historique_names(store, frozenset({"kernel", "unifi"})) == frozenset(
        {"kernel"}
    )


def test_historique_names_is_empty_when_nothing_in_the_graph_matches():
    store = OxigraphGraphStore()
    store.add("urn:e:1", AISTACK_STABLE_SUBJECT, _literal("jellyfin"))

    assert historique_names(store, frozenset({"unifi", "pihole"})) == frozenset()


def test_historique_names_short_circuits_on_an_empty_candidate_set():
    store = OxigraphGraphStore()
    assert historique_names(store, frozenset()) == frozenset()


def test_historique_entity_iri_finds_a_stable_subject_match():
    store = OxigraphGraphStore()
    store.add("urn:e:1", RDF_TYPE, PROV_ENTITY)
    store.add("urn:e:1", AISTACK_STABLE_SUBJECT, _literal("jellyfin"))

    assert historique_entity_iri(store, "jellyfin") == "urn:e:1"


def test_historique_entity_iri_finds_an_explains_match():
    store = OxigraphGraphStore()
    store.add("urn:e:2", AISTACK_EXPLAINS, subject_iri("kernel"))

    assert historique_entity_iri(store, "kernel") == "urn:e:2"


def test_historique_entity_iri_is_none_when_nothing_matches():
    store = OxigraphGraphStore()
    assert historique_entity_iri(store, "unifi") is None


def _literal(value: str):
    from aistack.timemachine.graph import Literal

    return Literal(value)

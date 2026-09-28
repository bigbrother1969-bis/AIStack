from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.architecture.yaml import load_infrastructure_topology_yaml
from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.history.query import available_instants, observation_at
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.kernel.bootstrap import create_kernel
from aistack.network_discovery.yaml import load_network_discovery_yaml
from aistack.providers.repository import RepositoryProvider
from aistack.renderers.architecture.html import load_vendored_mermaid_js
from aistack.renderers.timemachine import ProvenanceNeighbor, render_provenance_mermaid
from aistack.timemachine import (
    GraphStore,
    NetworkTreeNode,
    OxigraphGraphStore,
    RemoteHost,
    build_network_tree,
    historique_entity_iri,
    historique_names,
    parse_remote_hosts,
    stream_stem,
)
from aistack.timemachine.iri import short_label
from aistack.timemachine.projection import DEFAULT_GENERATED_DIR
from aistack.timemachine.vocabulary import (
    AISTACK_COLLECTION_GAP,
    AISTACK_OCCURRED_AT,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_USED,
    PROV_WAS_ATTRIBUTED_TO,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)

# `ADR-0011` § 18 (1.4 cadrage, 2026-09-28) — same
# `Path(__file__).resolve()`-relative convention `architecture_render
# .py`'s own `DEFAULT_TOPOLOGY`/`DEFAULT_CATEGORIZATION` already use,
# each CLI/screen declaring its own default rather than importing one
# from another entry-point module. `REPO_ROOT` already exists below
# for `RepositoryProvider`; these two are resolved through it the same
# way `GENERATED_DIR`/`STORE_PATH` already are.
DEFAULT_TOPOLOGY = "src/aistack/architecture/definitions/infrastructure_topology.yml"
DEFAULT_NETWORK_DISCOVERY = "src/aistack/network_discovery/definitions/network_discovery.yml"
NETWORK_DOCKER_OBSERVATION_STEM = "network-docker-observation"

# `ADR-0011` § 19 — the same guard `aistack.renderers.architecture.html
# .render_html` makes before embedding `load_vendored_mermaid_js()`'s
# own return value verbatim inside a `<script>` tag: a browser ends a
# script element at the first literal `</script` it finds, wherever in
# the source it sits. `load_vendored_mermaid_js()` itself performs no
# such check (it is a bare file read, shared by both callers); each
# caller that embeds it raw checks again at render time rather than
# trusting the other caller's own check to somehow cover this one too
# — `vendor/PROVENANCE.md` records today's bundle carries no such
# substring, not that it never could after a future
# `npm install mermaid@<newer>`.
_SCRIPT_TERMINATOR = "</script"

# A fifth mini-app, same family as `priority_ui`/`selection_ui`/
# `network_discovery_ui`/`troubleshooting_assistant_ui` — decided with
# the owner 2026-09-27 over a static-HTML page generated once by a CLI
# command (`console_render`'s own pattern): the Time Machine is
# something a person chooses an instant or a subject in and follows
# provenance edges from, not a fixed snapshot.
#
# **LAN-only, the same way as the other four (`ADR-0011` roadmap R1) —
# an operational convention, not a code-level restriction.** Bound to
# `0.0.0.0` below so it is reachable from anywhere on the owner's own
# LAN (`run_timemachine_ui.sh`'s own comment gives the exact reasoning
# `run_network_discovery_ui.sh` already established); LAN-only comes
# from never declaring a Proxy Host for this port in Nginx Proxy
# Manager, and from `console_links.yml` linking to the direct LAN
# address, never a `...persiaut-family.fr` subdomain. R1 stays true
# until 1.7's connection layer exists — this screen shows the same
# commands, packages and AI reasoning `network_discovery_ui`'s own
# warning already calls "a reconnaissance map for an attacker".
#
# **Read-only, never a writer** (`ADR-0011` § *Decision* 10:
# reconstruction is a full rebuild, on demand, run by
# `aistack.cli.timemachine_rebuild` — never by a screen a browser
# reaches). `OxigraphGraphStore.read_only` opens a fresh handle per
# request rather than holding one for the process's lifetime — cheap
# (SPARQL over an on-disk RocksDB store, not a network round trip),
# and it means a rebuild that replaces the store between two requests
# is picked up by the next one without a restart, with no long-lived
# handle to keep coordinated with the owner's own rebuild command.
#
# **v1 scope, chosen with the owner 2026-09-27**: a three-level
# browser — streams, the instants each one recorded, the facts known
# about one instant — reproducing what `aistack.cli.history_query`
# already shows, but read from the graph, so the graph is seen to
# agree with the files it was built from. Not the four richer
# maquettes already validated for the Time Machine (a time ribbon, a
# network tree, a "why" panel) — those assume data this graph does not
# hold yet (`aistack:occurredAt`, collection gaps, Explications), which
# is 1.4/1.5's own concern; building toward their visual richness now,
# ahead of that data, is exactly the invented infrastructure
# `ARC-P-006` forbids. `ADR-0011`'s own revision records this gap
# against the roadmap's four maquettes explicitly, rather than let the
# difference between what was demoed and what shipped go unstated.
REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

GENERATED_DIR = repository.resolve(DEFAULT_GENERATED_DIR)
STORE_PATH = GENERATED_DIR / "timemachine" / "graph"

app = FastAPI(title="AIStack Time Machine")
templates = Jinja2Templates(directory=str(repository.resolve("timemachine_ui/templates")))

# One label, and whether its object is an IRI (linkable) or a literal
# (displayed as-is) — the closed set `aistack.timemachine.projection`
# actually writes today (`ADR-0011` § *Decision* 2), not a guess at
# predicates that might exist: an outgoing fact this dict does not
# know falls back to its own raw IRI, both as label and as a literal
# value, rather than a wrong guess at either.
_PREDICATE_LABELS: dict[str, tuple[str, bool]] = {
    RDF_TYPE: ("timemachine.predicate.type", True),
    PROV_GENERATED_AT_TIME: ("timemachine.predicate.generated_at", False),
    PROV_WAS_GENERATED_BY: ("timemachine.predicate.generated_by", True),
    AISTACK_STABLE_SUBJECT: ("timemachine.predicate.stable_subject", False),
    PROV_WAS_ATTRIBUTED_TO: ("timemachine.predicate.attributed_to", True),
    PROV_USED: ("timemachine.predicate.used", True),
}

_TYPE_LABELS = {
    PROV_ENTITY: "timemachine.type_label.entity",
    PROV_ACTIVITY: "timemachine.type_label.activity",
    PROV_AGENT: "timemachine.type_label.agent",
}

# `NetworkTreeNode.kind` -> its i18n key, resolved here rather than
# built at runtime in the template: a translator call's own key must
# be a literal string for `tests/unit/i18n/test_the_real_catalogs.py`'s
# static scan to see it — the same reason `_PREDICATE_LABELS`/
# `_TYPE_LABELS` above are a dict, not a string built from a
# predicate's own name.
_TREE_KIND_LABELS: dict[str, str] = {
    "network": "timemachine.tree.kind_label.network",
    "host": "timemachine.tree.kind_label.host",
    "stack": "timemachine.tree.kind_label.stack",
    "container": "timemachine.tree.kind_label.container",
}


def _language(request: Request) -> PageLanguage:
    """ADR-0010 — same mechanism every mini-app already shares
    (`aistack.i18n.web`), tested by the governed suite even though
    this screen's own `app.py` is not (decision #9, 2026-08-29)."""

    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
    )


def _open_store() -> OxigraphGraphStore | None:
    """The graph, read-only, or `None` when
    `aistack.cli.timemachine_rebuild` has never run against this
    `GENERATED_DIR` — a real, expected state (a fresh checkout, or a
    host where the rebuild command has not been run yet), not this
    screen's own error."""

    try:
        return OxigraphGraphStore.read_only(STORE_PATH)
    except FileNotFoundError:
        return None


def _iri_term(iri: str) -> str:
    """
    `iri` embedded as a SPARQL `IRIREF`, or `ValueError` for anything
    that could break out of the `<...>` it is embedded in. Every real
    IRI this screen ever links to came out of a previous query's own
    result — `<`/`>`/a newline in one would mean the graph itself
    holds a malformed term, not a normal request — so this is a
    defensive check, not a feature.
    """

    if not iri or any(character in iri for character in "<>\r\n"):
        raise ValueError(f"not a usable IRI: {iri!r}")
    return f"<{iri}>"


def _finish(response: HTMLResponse, language: PageLanguage) -> HTMLResponse:
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response


def _not_built(request: Request, language: PageLanguage) -> HTMLResponse:
    context = {"store_path": str(STORE_PATH)}
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="not_built.html", context=context),
        language,
    )


def _local_host_label() -> str:
    """
    The local host's own real name — `infrastructure_topology.yml`'s
    first `hardware:` entry, hand-confirmed by the owner
    (`ADR-0011` § 18, `infrastructure_topology.yml`'s own header
    comment: "écrit à la main... chaque fait ci-dessous a été
    confirmé directement avec le owner"). GIGABYTE today; never
    guessed from `socket.gethostname()` or an environment variable
    nothing here declares.
    """

    topology = load_infrastructure_topology_yaml(repository.resolve(DEFAULT_TOPOLOGY))
    return topology.hardware[0].name if topology.hardware else ""


def _remote_hosts() -> tuple[RemoteHost, ...]:
    """
    The remote hosts the last `network_docker_discover` run actually
    found — read from its own last stored Observation History
    snapshot, **never a live scan triggered from here** (`ADR-0011`
    § 18, `NetworkDockerDiscoveryProvider`'s own docstring: "never
    triggered automatically"). `()` when the scan has never run —
    a real, expected state on a fresh checkout, not this screen's own
    error, the same degradation `_open_store` already gives the graph.
    """

    instants = available_instants(GENERATED_DIR, NETWORK_DOCKER_OBSERVATION_STEM)
    if not instants:
        return ()

    historical = observation_at(GENERATED_DIR, NETWORK_DOCKER_OBSERVATION_STEM, instants[-1])
    if historical is None:
        return ()

    observation = json.loads(historical.read())
    return parse_remote_hosts(observation)


def _network_cidr() -> str:
    return load_network_discovery_yaml(repository.resolve(DEFAULT_NETWORK_DISCOVERY)).cidr


def _build_tree() -> list[NetworkTreeNode]:
    """
    Réseau ⊃ Hôte ⊃ Stack ⊃ Conteneur, from the same live catalogs
    `architecture_render.main` already builds (`ADR-0011` § 18) — not
    from the graph, which does not hold this structure yet.
    """

    ctx = create_kernel()
    docker_observation = ctx.registries.providers.get("docker").collect()
    docker_catalog = DockerRuntimeCatalogBuilder().build(docker_observation)

    compose_observation = ctx.registries.providers.get("compose").collect()
    compose_catalog = ComposeRuntimeCatalogBuilder().build(compose_observation)

    return build_network_tree(
        cidr=_network_cidr(),
        local_host_label=_local_host_label(),
        docker_catalog=docker_catalog,
        compose_catalog=compose_catalog,
        remote_hosts=_remote_hosts(),
    )


def _filter_tree(nodes: list[NetworkTreeNode], query: str) -> list[NetworkTreeNode]:
    """
    `nodes`, narrowed to every node whose own label matches `query`
    (case-insensitive substring) plus every ancestor of a match — so
    a matched container stays reachable through its real stack and
    host rather than appearing detached from the tree it lives in.
    Original depth-first order is preserved. An empty/blank `query`
    returns `nodes` unchanged.
    """

    needle = query.strip().lower()
    if not needle:
        return nodes

    by_id = {node.id: node for node in nodes}
    keep: set[str] = set()
    for node in nodes:
        if needle not in node.label.lower():
            continue
        current: str | None = node.id
        while current is not None and current not in keep:
            keep.add(current)
            current = by_id[current].parent_id

    return [node for node in nodes if node.id in keep]


def _historique_links(
    store: GraphStore | None, nodes: list[NetworkTreeNode]
) -> dict[str, str | None]:
    """
    One entry per node whose label has real history in the graph
    today (`historique_names`, batched — `ADR-0011` § 18), mapped to
    the entity IRI it links to (`historique_entity_iri`, called only
    for that small, already-matched set — never per candidate).
    `{}` when the graph itself has not been built yet.
    """

    if store is None:
        return {}

    candidate_names = frozenset(
        node.label for node in nodes if node.kind in ("host", "stack", "container")
    )
    matched_names = historique_names(store, candidate_names)
    return {name: historique_entity_iri(store, name) for name in matched_names}


@app.get("/", response_class=HTMLResponse)
def streams(request: Request):
    language = _language(request)
    store = _open_store()
    if store is None:
        return _not_built(request, language)

    rows = store.query(f"SELECT DISTINCT ?activity WHERE {{ ?activity a {_iri_term(PROV_ACTIVITY)} }}")
    entries = sorted(
        (
            {
                "iri": row["activity"],
                "label": stream_stem(row["activity"]) or row["activity"],
            }
            for row in rows
            if row["activity"] is not None
        ),
        key=lambda entry: entry["label"],
    )

    context: dict[str, object] = {"streams": entries}
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="streams.html", context=context),
        language,
    )


def _node_href(neighbor_iri: str, language: PageLanguage) -> str:
    return f"/node?iri={quote(neighbor_iri, safe='')}&lang={language.lang}"


def _provenance_neighbors(
    facts: list[dict[str, object]],
    referenced_by: list[dict[str, str]],
    language: PageLanguage,
) -> tuple[ProvenanceNeighbor, ...]:
    """
    `ADR-0011` § 19 — the same `facts`/`referenced_by` `node`'s own
    text view already computed, narrowed to real neighbours only: a
    fact whose object is a literal, or `RDF_TYPE`'s own type badge
    (`object_type_label_key` set), names nothing to draw an edge to —
    `node.html`'s existing table already makes this exact distinction
    (it shows the type badge as plain text, never as a link), this
    reuses it rather than re-deriving it.
    """

    neighbors: list[ProvenanceNeighbor] = []

    for fact in facts:
        object_iri = fact["object_iri"]
        if object_iri is None or fact["object_type_label_key"] is not None:
            continue
        label_key = fact["predicate_label_key"]
        predicate_label = language.t(label_key) if label_key else str(fact["predicate"])
        neighbors.append(
            ProvenanceNeighbor(
                href=_node_href(str(object_iri), language),
                label=short_label(str(object_iri)),
                predicate_label=predicate_label,
                direction="out",
            )
        )

    for ref in referenced_by:
        label_key = ref["predicate_label_key"]
        predicate_label = language.t(label_key) if label_key else ref["predicate"]
        neighbors.append(
            ProvenanceNeighbor(
                href=_node_href(ref["iri"], language),
                label=short_label(ref["iri"]),
                predicate_label=predicate_label,
                direction="in",
            )
        )

    return tuple(neighbors)


@app.get("/node", response_class=HTMLResponse)
def node(request: Request, iri: str):
    language = _language(request)

    try:
        term = _iri_term(iri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = _open_store()
    if store is None:
        return _not_built(request, language)

    outgoing = list(store.query(f"SELECT ?p ?o WHERE {{ {term} ?p ?o }}"))
    incoming = list(store.query(f"SELECT ?s ?p WHERE {{ ?s ?p {term} }}"))

    is_activity = any(
        row["p"] == RDF_TYPE and row["o"] == PROV_ACTIVITY for row in outgoing
    )

    instants: list[dict[str, object]] = []
    referenced_by: list[dict[str, str]] = []

    if is_activity:
        instants = [
            {
                "iri": row["entity"],
                "generated_at": row["generated_at"],
                "subject": row["subject"],
            }
            for row in store.query(
                "SELECT ?entity ?generated_at ?subject WHERE { "
                f"?entity {_iri_term(PROV_WAS_GENERATED_BY)} {term} ; "
                f"{_iri_term(PROV_GENERATED_AT_TIME)} ?generated_at . "
                f"OPTIONAL {{ ?entity {_iri_term(AISTACK_STABLE_SUBJECT)} ?subject }} "
                "} ORDER BY DESC(?generated_at)"
            )
        ]

    for row in incoming:
        if is_activity and row["p"] == PROV_WAS_GENERATED_BY:
            continue  # already shown, time-sorted, as `instants` above
        predicate = row["p"]
        label_key, _ = _PREDICATE_LABELS.get(predicate, (None, False))
        referenced_by.append(
            {"iri": row["s"], "predicate": predicate, "predicate_label_key": label_key}
        )

    facts = []
    for row in outgoing:
        predicate, obj = row["p"], row["o"]
        label_key, object_is_iri = _PREDICATE_LABELS.get(predicate, (None, False))
        object_type_label_key = (
            _TYPE_LABELS.get(obj) if predicate == RDF_TYPE else None
        )
        facts.append(
            {
                "predicate": predicate,
                "predicate_label_key": label_key,
                "object": obj,
                "object_type_label_key": object_type_label_key,
                "object_iri": obj if object_is_iri else None,
            }
        )

    node_type_label_key = next(
        (
            _TYPE_LABELS[row["o"]]
            for row in outgoing
            if row["p"] == RDF_TYPE and row["o"] in _TYPE_LABELS
        ),
        None,
    )

    # `ADR-0011` § 19 (1.4, "une vue du graphe", maquette 2 "graphe de
    # provenance centré sur l'étape") — a real diagram of this node's
    # own immediate neighbours, drawn from the exact same `facts`/
    # `referenced_by` the text view above already computed. `None`
    # when there is nothing real to draw (no fact points at another
    # node, nothing points back) — the template falls back to the
    # same `.empty` convention every other section already holds,
    # rather than a diagram of one lone, edgeless box.
    neighbors = _provenance_neighbors(facts, referenced_by, language)
    provenance_graph = (
        render_provenance_mermaid(short_label(iri), neighbors) if neighbors else None
    )
    # The vendored bundle is only worth embedding when there is a
    # diagram to render with it (`load_vendored_mermaid_js` reads a
    # multi-megabyte file every call — cheap on the LAN this screen
    # never leaves, but no reason to pay it for a node with nothing to
    # draw).
    mermaid_js = load_vendored_mermaid_js() if provenance_graph else None
    if mermaid_js is not None and _SCRIPT_TERMINATOR in mermaid_js.lower():
        raise ValueError(
            "The vendored mermaid.js bundle contains "
            f"{_SCRIPT_TERMINATOR!r}, which would truncate the "
            "<script> tag it is embedded in — see "
            "src/aistack/renderers/architecture/vendor/PROVENANCE.md"
        )

    context: dict[str, object] = {
        "iri": iri,
        "node_type_label_key": node_type_label_key,
        "instants": instants,
        "facts": facts,
        "referenced_by": referenced_by,
        "provenance_graph": provenance_graph,
        "mermaid_js": mermaid_js,
    }
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="node.html", context=context),
        language,
    )


@app.get("/tree", response_class=HTMLResponse)
def tree_view(request: Request, q: str = ""):
    """
    `ADR-0011` § 18 — Réseau ⊃ Hôte ⊃ Stack ⊃ Conteneur, `timemachine_
    ui`'s second view, built from the live Docker/Compose catalogs
    (never the graph) plus the last stored network-discovery snapshot,
    with each node's real Historique looked up in the graph (empty,
    honestly, when the graph has never been built). `q` narrows the
    tree to matches and their ancestors (`_filter_tree`); an empty
    result for a non-blank `q` is a real, distinct state from "no
    devices observed at all", both handled by the template.
    """

    language = _language(request)

    nodes = _build_tree()
    store = _open_store()
    historique_links = _historique_links(store, nodes)

    filtered = _filter_tree(nodes, q)
    children_by_parent: dict[str, list[NetworkTreeNode]] = {}
    for node in filtered:
        if node.parent_id is not None:
            children_by_parent.setdefault(node.parent_id, []).append(node)

    def _to_context(node: NetworkTreeNode) -> dict[str, object]:
        has_historique = node.kind in ("host", "stack", "container") and (
            node.label in historique_links
        )
        return {
            "id": node.id,
            "label": node.label,
            "kind": node.kind,
            "kind_label_key": _TREE_KIND_LABELS[node.kind],
            "depth": node.depth,
            "has_historique": has_historique,
            "historique_iri": historique_links.get(node.label) if has_historique else None,
            "children": [_to_context(child) for child in children_by_parent.get(node.id, [])],
        }

    root_node = next((node for node in filtered if node.id == "network"), None)
    root = _to_context(root_node) if root_node is not None else None

    context: dict[str, object] = {
        "root": root,
        "query": q,
        "search_empty": bool(q.strip()) and root is None,
    }
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="tree.html", context=context),
        language,
    )


# `ADR-0011` §24 (1.5.1 cadrage, 2026-09-28) — maquette 1's own
# "ruban du temps", one v1 slice of it: every recorded instant, from
# every stream the graph currently holds (a cadrage decision — the
# owner's own, over limiting this to the four 1.5 Docker streams —
# the same generic-over-whatever-the-graph-holds philosophy `streams`
# and `tree_view` above already hold, so a future stream needs no
# change here to appear). A fixed six-colour, six-shape palette
# assigns each stream a badge — colour *and* shape together, never
# colour alone, the same accessibility rule this palette was chosen
# against (dataviz skill: "identity is never colour-alone").
# Deliberately not built in this slice: a stepping "curseur" control
# and the network tree shown alongside it (both real pieces of the
# validated maquette) — this screen is a full, filterable,
# chronological list instead, the same kind of narrower-than-the-
# maquette v1 §19's own graph view already shipped, with the gap
# stated honestly here and in `ADR-0011` rather than left to discover.
_RIBBON_PALETTE: tuple[dict[str, str], ...] = (
    {"color": "#2f6fed", "shape": "●"},  # bleu, rond
    {"color": "#e2703a", "shape": "▲"},  # orange, triangle
    {"color": "#1f9e6d", "shape": "■"},  # vert, carré
    {"color": "#8952e0", "shape": "◆"},  # violet, losange
    {"color": "#c2296b", "shape": "★"},  # magenta, étoile
    {"color": "#3f8fa8", "shape": "▶"},  # bleu-vert, flèche
)


def _ribbon_entries(store: GraphStore) -> list[dict[str, object]]:
    """
    Every entity any stream's own activity generated, oldest first —
    the same `prov:wasGeneratedBy`/`prov:generatedAtTime` shape
    `node`'s own `instants` query already reads for one stream at a
    time, widened here to the whole graph in a single pass.

    **Which instant places an entry on the ribbon.** `aistack
    :occurredAt` — where a stream states a real occurrence instant
    independently of recording time (`ADR-0011` §4; today, only
    `docker-events` and R11's own collection-gap facts) — decides an
    entry's position when present; `prov:generatedAtTime` (recording
    time) otherwise. `is_occurred_at` records which one so the
    template can say so honestly, never presenting a recording time as
    if it were a real occurrence.

    **A collection gap is not a normal entry.** It is generated by a
    stream's own activity exactly like every other entity (R11,
    `aistack.timemachine.projection.collection_gaps`), but it states
    an absence, not an observation — a second query
    (`aistack:collectionGap`, the activity's own pointer to its gap
    entities) marks which entity IRIs are gaps so the template can
    show that plainly rather than letting a "nothing was observed
    here" fact look like one more ordinary event on that stream's own
    band.
    """

    rows = store.query(
        "SELECT ?activity ?entity ?generated_at ?occurred_at ?subject WHERE { "
        f"?entity {_iri_term(PROV_WAS_GENERATED_BY)} ?activity ; "
        f"{_iri_term(PROV_GENERATED_AT_TIME)} ?generated_at . "
        f"OPTIONAL {{ ?entity {_iri_term(AISTACK_OCCURRED_AT)} ?occurred_at }} "
        f"OPTIONAL {{ ?entity {_iri_term(AISTACK_STABLE_SUBJECT)} ?subject }} "
        "}"
    )

    gap_iris = {
        row["gap"]
        for row in store.query(
            f"SELECT ?gap WHERE {{ ?activity {_iri_term(AISTACK_COLLECTION_GAP)} ?gap }}"
        )
    }

    entries: list[dict[str, object]] = []
    for row in rows:
        entity = row["entity"]
        occurred_at = row["occurred_at"]
        entries.append(
            {
                "iri": entity,
                "stream": stream_stem(row["activity"]) or row["activity"],
                "instant": occurred_at if occurred_at is not None else row["generated_at"],
                "is_occurred_at": occurred_at is not None,
                "is_gap": entity in gap_iris,
                "subject": row["subject"],
            }
        )

    entries.sort(key=lambda entry: (str(entry["instant"]), str(entry["stream"])))
    return entries


@app.get("/ribbon", response_class=HTMLResponse)
def ribbon_view(
    request: Request,
    streams: list[str] = Query(default=[]),
    submitted: str = "",
):
    """
    `ADR-0011` §24 — the filter form's own hidden `submitted` field is
    what tells "the form was submitted with every box unchecked" (a
    real, if unusual, choice — show nothing) apart from "no query
    string at all" (a fresh link — show every stream): an empty
    `streams` list means something different in each of those two
    requests, and a GET form has no other way to say which one this
    is. Badges are assigned once, over every stream the graph holds,
    before filtering — so a stream's own colour/shape never shifts
    when another stream is hidden.
    """

    language = _language(request)
    store = _open_store()
    if store is None:
        return _not_built(request, language)

    entries = _ribbon_entries(store)
    all_streams = sorted({str(entry["stream"]) for entry in entries})
    badges = {
        stream: _RIBBON_PALETTE[index % len(_RIBBON_PALETTE)]
        for index, stream in enumerate(all_streams)
    }

    visible = set(streams) if submitted else set(all_streams)
    filtered: list[dict[str, object]] = []
    for entry in entries:
        if entry["stream"] not in visible:
            continue
        row = dict(entry)
        row["badge"] = badges[str(entry["stream"])]
        row["href"] = _node_href(str(entry["iri"]), language)
        filtered.append(row)

    context: dict[str, object] = {
        "entries": filtered,
        "filter_streams": [
            {"stream": stream, "badge": badges[stream], "checked": stream in visible}
            for stream in all_streams
        ],
        "submitted": bool(submitted),
    }
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="ribbon.html", context=context),
        language,
    )

"""
What the Time Machine screen shows, computed without a web framework
(`ADR-0012` § 4) — moved out of `timemachine_ui/app.py` on 2026-10-03,
when the screen joined AIStack's single web application under
`/timemachine` (`aistack.web.timemachine`).

The screen is read-only, never a writer (`ADR-0011` § *Decision* 10):
the graph is rebuilt on demand by `aistack.cli.timemachine_rebuild`,
and every function here only reads it, the Explications store, or the
last stored network-discovery snapshot.

A link to a graph node is built by the caller (`NodeHref`), since only
the route knows the prefix it is mounted under and the reader's
language.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aistack.explications.human import DISCARDED, PROPOSED, VALIDATED, status_of, versions
from aistack.history import available_stems
from aistack.history.subject_names import subject_for_stem
from aistack.history.query import available_instants, observation_at
from aistack.renderers.architecture.html import load_vendored_mermaid_js
from aistack.renderers.timemachine import (
    ProvenanceNeighbor,
    RibbonMark,
    RibbonSvg,
    render_ribbon_svg,
)
from aistack.timemachine.graph import GraphStore
from aistack.timemachine.iri import short_label, stream_stem
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection.docker_diff import STEM as DOCKER_DIFF_STEM
from aistack.timemachine.projection.docker_digest import STEM as DOCKER_DIGEST_STEM
from aistack.timemachine.projection.docker_events import STEM as DOCKER_EVENTS_STEM
from aistack.timemachine.projection.docker_packages import STEM as DOCKER_PACKAGES_STEM
from aistack.timemachine.tree import (
    NetworkTreeNode,
    RemoteHost,
    historique_entity_iri,
    historique_names,
    parse_remote_hosts,
)
from aistack.timemachine.vocabulary import (
    AISTACK_COLLECTION_GAP,
    AISTACK_CONFIDENCE,
    AISTACK_EXPLAINS,
    AISTACK_EXPLICATION_STATUS,
    AISTACK_OCCURRED_AT,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_USED,
    PROV_WAS_ATTRIBUTED_TO,
    PROV_WAS_GENERATED_BY,
    PROV_WAS_REVISION_OF,
    RDF_TYPE,
)

NodeHref = Callable[[str], str]
Translate = Callable[..., str]
Fact = dict[str, Any]
Entry = dict[str, Any]

# Where the graph and the Explications live, under the generated
# directory the application serves — the same paths
# `aistack.cli.timemachine_rebuild` and `project_explications` derive.
GRAPH_DIR = Path("timemachine") / "graph"
EXPLICATIONS_DIR = Path("explications")
NETWORK_DOCKER_OBSERVATION_STEM = "network-docker-observation"

# One label per predicate the projection actually writes, and whether
# its object is an IRI (a link) or a literal. A predicate this map does
# not know is shown by its own IRI, never a guessed label.
PREDICATE_LABELS: dict[str, tuple[str, bool]] = {
    RDF_TYPE: ("timemachine.predicate.type", True),
    PROV_GENERATED_AT_TIME: ("timemachine.predicate.generated_at", False),
    PROV_WAS_GENERATED_BY: ("timemachine.predicate.generated_by", True),
    AISTACK_STABLE_SUBJECT: ("timemachine.predicate.stable_subject", False),
    PROV_WAS_ATTRIBUTED_TO: ("timemachine.predicate.attributed_to", True),
    PROV_USED: ("timemachine.predicate.used", True),
    AISTACK_EXPLAINS: ("timemachine.predicate.explains", True),
    AISTACK_CONFIDENCE: ("timemachine.predicate.confidence", False),
    AISTACK_EXPLICATION_STATUS: ("timemachine.predicate.explication_status", False),
    PROV_WAS_REVISION_OF: ("timemachine.predicate.revision_of", True),
}

TYPE_LABELS: dict[str, str] = {
    PROV_ENTITY: "timemachine.type_label.entity",
    PROV_ACTIVITY: "timemachine.type_label.activity",
    PROV_AGENT: "timemachine.type_label.agent",
}

# Literal keys, so the catalog test sees every one of them.
TREE_KIND_LABELS: dict[str, str] = {
    "network": "timemachine.tree.kind_label.network",
    "host": "timemachine.tree.kind_label.host",
    "stack": "timemachine.tree.kind_label.stack",
    "container": "timemachine.tree.kind_label.container",
}

# One colour and one shape per stream, together — identity is never
# colour alone (`ADR-0011` § 24).
RIBBON_PALETTE: tuple[dict[str, str], ...] = (
    {"color": "#2f6fed", "shape": "●"},
    {"color": "#e2703a", "shape": "▲"},
    {"color": "#1f9e6d", "shape": "■"},
    {"color": "#8952e0", "shape": "◆"},
    {"color": "#c2296b", "shape": "★"},
    {"color": "#3f8fa8", "shape": "▶"},
)

# The flat list's page size (owner's cadrage, 2026-09-30: "50-100 par page").
RIBBON_PAGE_SIZE = 100

# The hosts' streams (1.11, `ADR-0020`): `host-<name>`, one per host.
HOST_STEM_PREFIX = "host-"

# The ribbon's two real categories (`ADR-0011` § 26): the four 1.5
# Docker collectors, each with its own projector, and every other stream.
DOCKER_COLLECTOR_STREAMS: frozenset[str] = frozenset(
    {DOCKER_DIFF_STEM, DOCKER_DIGEST_STEM, DOCKER_EVENTS_STEM, DOCKER_PACKAGES_STEM}
)

# A browser ends a script element at the first `</script` it finds.
SCRIPT_TERMINATOR = "</script"


# --------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------


def open_graph(generated_dir: Path) -> OxigraphGraphStore | None:
    """The graph, read-only, or `None` when it has never been rebuilt —
    an expected state on a fresh host, not an error."""

    try:
        return OxigraphGraphStore.read_only(generated_dir / GRAPH_DIR)
    except FileNotFoundError:
        return None


def graph_version(generated_dir: Path) -> float:
    """The freshest modification time among the graph's files: it
    changes only when a rebuild writes the store. `0.0` without one."""

    try:
        return max(
            (
                path.stat().st_mtime
                for path in (generated_dir / GRAPH_DIR).rglob("*")
                if path.is_file()
            ),
            default=0.0,
        )
    except FileNotFoundError:
        return 0.0


def iri_term(iri: str) -> str:
    """`iri` as a SPARQL `IRIREF`, or `ValueError` for anything that
    could break out of the `<...>` it is embedded in."""

    if not iri or any(character in iri for character in "<>\r\n"):
        raise ValueError(f"not a usable IRI: {iri!r}")
    return f"<{iri}>"


def stream_list(store: GraphStore) -> list[dict[str, str]]:
    """Every stream (`prov:Activity`) the graph holds, by name."""

    rows = store.query(f"SELECT DISTINCT ?activity WHERE {{ ?activity a {iri_term(PROV_ACTIVITY)} }}")
    return sorted(
        (
            {"iri": str(row["activity"]), "label": stream_stem(str(row["activity"])) or str(row["activity"])}
            for row in rows
            if row["activity"] is not None
        ),
        key=lambda entry: entry["label"],
    )


def _fact(predicate: str, obj: str) -> Fact:
    label_key, object_is_iri = PREDICATE_LABELS.get(predicate, (None, False))
    return {
        "predicate": predicate,
        "predicate_label_key": label_key,
        "object": obj,
        "object_type_label_key": TYPE_LABELS.get(obj) if predicate == RDF_TYPE else None,
        "object_iri": obj if object_is_iri else None,
    }


def entity_facts(store: GraphStore, iri: str) -> list[Fact]:
    """What the graph states about `iri`, one labelled fact per triple."""

    rows = store.query(f"SELECT ?p ?o WHERE {{ {iri_term(iri)} ?p ?o }}")
    return [_fact(str(row["p"]), str(row["o"])) for row in rows]


@dataclass(frozen=True)
class NodeView:
    """One node of the graph: its facts, what points at it and, for a
    stream, the instants it recorded (newest first)."""

    facts: list[Fact]
    referenced_by: list[dict[str, Any]]
    instants: list[dict[str, Any]] | None
    type_label_key: str | None


def node_view(store: GraphStore, iri: str) -> NodeView:
    """`ValueError` for an IRI that cannot be queried."""

    term = iri_term(iri)
    facts = entity_facts(store, iri)
    is_activity = any(
        fact["predicate"] == RDF_TYPE and fact["object"] == PROV_ACTIVITY for fact in facts
    )

    instants = None
    if is_activity:
        instants = [
            {
                "iri": row["entity"],
                "generated_at": row["generated_at"],
                "subject": row["subject"],
            }
            for row in store.query(
                "SELECT ?entity ?generated_at ?subject WHERE { "
                f"?entity {iri_term(PROV_WAS_GENERATED_BY)} {term} ; "
                f"{iri_term(PROV_GENERATED_AT_TIME)} ?generated_at . "
                f"OPTIONAL {{ ?entity {iri_term(AISTACK_STABLE_SUBJECT)} ?subject }} "
                "} ORDER BY DESC(?generated_at)"
            )
        ]

    referenced_by = []
    for row in store.query(f"SELECT ?s ?p WHERE {{ ?s ?p {term} }}"):
        if is_activity and row["p"] == PROV_WAS_GENERATED_BY:
            continue  # shown, time-sorted, as `instants`
        predicate = str(row["p"])
        referenced_by.append(
            {
                "iri": str(row["s"]),
                "predicate": predicate,
                "predicate_label_key": PREDICATE_LABELS.get(predicate, (None, False))[0],
            }
        )

    type_label_key = next(
        (
            TYPE_LABELS[str(fact["object"])]
            for fact in facts
            if fact["predicate"] == RDF_TYPE and fact["object"] in TYPE_LABELS
        ),
        None,
    )

    return NodeView(facts, referenced_by, instants, type_label_key)


def node_instant(facts: list[Fact]) -> str | None:
    """The node's own instant: `aistack:occurredAt` when the stream
    states one, `prov:generatedAtTime` otherwise — the same priority
    that places an entry on the ribbon. `None` for an Activity/Agent."""

    for predicate in (AISTACK_OCCURRED_AT, PROV_GENERATED_AT_TIME):
        for fact in facts:
            if fact["predicate"] == predicate:
                return str(fact["object"])
    return None


def node_stable_subject(facts: list[Fact]) -> str | None:
    """The `aistack:stableSubject` the node asserts, if any."""

    for fact in facts:
        if fact["predicate"] == AISTACK_STABLE_SUBJECT:
            return str(fact["object"])
    return None


def provenance_neighbors(
    view: NodeView, t: Translate, node_href: NodeHref
) -> tuple[ProvenanceNeighbor, ...]:
    """The node's real neighbours, for the provenance diagram: a literal
    or a type badge names nothing to draw an edge to."""

    neighbors: list[ProvenanceNeighbor] = []

    for fact in view.facts:
        object_iri = fact["object_iri"]
        if object_iri is None or fact["object_type_label_key"] is not None:
            continue
        label_key = fact["predicate_label_key"]
        neighbors.append(
            ProvenanceNeighbor(
                href=node_href(str(object_iri)),
                label=short_label(str(object_iri)),
                predicate_label=t(label_key) if label_key else str(fact["predicate"]),
                direction="out",
            )
        )

    for ref in view.referenced_by:
        label_key = ref["predicate_label_key"]
        neighbors.append(
            ProvenanceNeighbor(
                href=node_href(ref["iri"]),
                label=short_label(ref["iri"]),
                predicate_label=t(label_key) if label_key else ref["predicate"],
                direction="in",
            )
        )

    return tuple(neighbors)


def mermaid_script() -> str:
    """The vendored mermaid bundle, refused if it would end the
    `<script>` element it is embedded in."""

    script = load_vendored_mermaid_js()
    if SCRIPT_TERMINATOR in script.lower():
        raise ValueError(
            f"The vendored mermaid.js bundle contains {SCRIPT_TERMINATOR!r}, which "
            "would truncate the <script> tag it is embedded in — see "
            "src/aistack/renderers/architecture/vendor/PROVENANCE.md"
        )
    return script


# --------------------------------------------------------------------
# The network tree
# --------------------------------------------------------------------


def last_remote_hosts(generated_dir: Path) -> tuple[RemoteHost, ...]:
    """The remote hosts the last `network_docker_discover` run found,
    from its last stored snapshot — never a live scan. `()` when the
    scan has never run."""

    instants = available_instants(generated_dir, NETWORK_DOCKER_OBSERVATION_STEM)
    if not instants:
        return ()

    historical = observation_at(generated_dir, NETWORK_DOCKER_OBSERVATION_STEM, instants[-1])
    if historical is None:
        return ()

    return parse_remote_hosts(json.loads(historical.read()))


def filter_tree(nodes: list[NetworkTreeNode], query: str) -> list[NetworkTreeNode]:
    """`nodes` narrowed to every node whose label contains `query`
    (case-insensitive) and every ancestor of one, in their order. A
    blank query keeps every node."""

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


_HISTORY_KINDS = ("host", "stack", "container")


def historique_links(store: GraphStore | None, nodes: list[NetworkTreeNode]) -> dict[str, str | None]:
    """Each node label with history in the graph, to the entity it
    links to. `{}` without a graph."""

    if store is None:
        return {}

    candidates = frozenset(node.label for node in nodes if node.kind in _HISTORY_KINDS)
    return {name: historique_entity_iri(store, name) for name in historique_names(store, candidates)}


def tree_context(
    nodes: list[NetworkTreeNode], store: GraphStore | None, query: str
) -> dict[str, Any]:
    """The nested, filtered tree a template renders recursively."""

    links = historique_links(store, nodes)
    filtered = filter_tree(nodes, query)
    children: dict[str, list[NetworkTreeNode]] = {}
    for node in filtered:
        if node.parent_id is not None:
            children.setdefault(node.parent_id, []).append(node)

    def nested(node: NetworkTreeNode) -> dict[str, Any]:
        has_historique = node.kind in _HISTORY_KINDS and node.label in links
        return {
            "id": node.id,
            "label": node.label,
            "kind": node.kind,
            "kind_label_key": TREE_KIND_LABELS[node.kind],
            "depth": node.depth,
            "has_historique": has_historique,
            "historique_iri": links.get(node.label) if has_historique else None,
            "children": [nested(child) for child in children.get(node.id, [])],
        }

    root_node = next((node for node in filtered if node.id == "network"), None)
    root = nested(root_node) if root_node is not None else None

    return {"root": root, "query": query, "search_empty": bool(query.strip()) and root is None}


@dataclass
class ExpiringValue:
    """A value recomputed at most once per `ttl_seconds` — the tree is
    built from live Docker discovery, measured "très longue" per
    request; the owner chose a ~45 s staleness over it (2026-09-30)."""

    compute: Callable[[], Any]
    ttl_seconds: float = 45.0
    clock: Callable[[], float] = time.monotonic
    _cached: tuple[float, Any] | None = field(default=None, init=False, repr=False)

    def get(self) -> Any:
        now = self.clock()
        if self._cached is not None and now - self._cached[0] < self.ttl_seconds:
            return self._cached[1]
        value = self.compute()
        self._cached = (now, value)
        return value


# --------------------------------------------------------------------
# The ribbon
# --------------------------------------------------------------------


def ribbon_entries(store: GraphStore) -> list[Entry]:
    """
    Every entity a stream generated, oldest first. `aistack:occurredAt`
    places an entry when the stream states it, `prov:generatedAtTime`
    otherwise (`is_occurred_at` says which). A collection gap (R11)
    states an absence, so it is marked as one (`is_gap`).
    """

    rows = store.query(
        "SELECT ?activity ?entity ?generated_at ?occurred_at ?subject WHERE { "
        f"?entity {iri_term(PROV_WAS_GENERATED_BY)} ?activity ; "
        f"{iri_term(PROV_GENERATED_AT_TIME)} ?generated_at . "
        f"OPTIONAL {{ ?entity {iri_term(AISTACK_OCCURRED_AT)} ?occurred_at }} "
        f"OPTIONAL {{ ?entity {iri_term(AISTACK_STABLE_SUBJECT)} ?subject }} "
        "}"
    )
    gaps = {
        row["gap"]
        for row in store.query(
            f"SELECT ?gap WHERE {{ ?activity {iri_term(AISTACK_COLLECTION_GAP)} ?gap }}"
        )
    }

    entries: list[Entry] = []
    for row in rows:
        occurred_at = row["occurred_at"]
        entries.append(
            {
                "iri": row["entity"],
                "stream": stream_stem(str(row["activity"])) or row["activity"],
                "instant": occurred_at if occurred_at is not None else row["generated_at"],
                "is_occurred_at": occurred_at is not None,
                "is_gap": row["entity"] in gaps,
                "subject": row["subject"],
            }
        )

    entries.sort(key=lambda entry: (str(entry["instant"]), str(entry["stream"])))
    return entries


@dataclass
class RibbonEntries:
    """`ribbon_entries`, computed once per graph rebuild: the graph only
    changes when a rebuild writes it (`graph_version`), so this cache
    never serves a stale answer."""

    generated_dir: Path
    _cached: tuple[float, list[Entry]] | None = field(default=None, init=False, repr=False)

    def get(self, store: GraphStore) -> list[Entry]:
        version = graph_version(self.generated_dir)
        if self._cached is not None and self._cached[0] == version:
            return self._cached[1]
        entries = ribbon_entries(store)
        self._cached = (version, entries)
        return entries


def ribbon_badges(entries: Iterable[Entry]) -> dict[str, dict[str, str]]:
    """One badge per stream, assigned over every stream the graph holds,
    so a stream keeps its badge whatever a filter hides."""

    streams = sorted({str(entry["stream"]) for entry in entries})
    return {
        stream: RIBBON_PALETTE[index % len(RIBBON_PALETTE)]
        for index, stream in enumerate(streams)
    }


def _mark(entry: Entry, badge: dict[str, str], href: str) -> RibbonMark:
    return RibbonMark(
        href=href,
        stream=str(entry["stream"]),
        instant=str(entry["instant"]),
        subject=str(entry["subject"]) if entry["subject"] is not None else None,
        is_gap=bool(entry["is_gap"]),
        is_occurred_at=bool(entry["is_occurred_at"]),
        color=badge["color"],
        shape=badge["shape"],
    )


def ribbon_group(stream: str) -> str:
    """`docker`, `hosts` or `observation` — the ribbon's three groups."""

    if stream in DOCKER_COLLECTOR_STREAMS:
        return "docker"
    if stream.startswith(HOST_STEM_PREFIX):
        return "hosts"
    return "observation"


def ribbon_svgs(marks: list[RibbonMark], lane_streams: list[str]) -> tuple[RibbonSvg, RibbonSvg, RibbonSvg]:
    """The Docker-collector ribbon, the hosts' ribbon (1.11, `ADR-0020`)
    and the observation ribbon, each with its own time axis
    (`ADR-0011` § 26)."""

    return tuple(  # type: ignore[return-value]
        render_ribbon_svg(
            tuple(m for m in marks if ribbon_group(m.stream) == group),
            tuple(s for s in lane_streams if ribbon_group(s) == group),
        )
        for group in ("docker", "hosts", "observation")
    )


def _about(entry: Entry, subject: str) -> bool:
    return entry["subject"] is not None and str(entry["subject"]) == subject


def ribbon_page(
    entries: list[Entry],
    *,
    streams: list[str],
    submitted: bool,
    subject: str,
    page: int,
    node_href: NodeHref,
) -> dict[str, Any]:
    """
    The `/ribbon` page: every entry of the visible streams (all of them
    without a submitted filter — an empty `streams` from a submitted
    form shows nothing), narrowed to `subject` when one is given.

    Without a subject, every stream keeps its lane, so a hidden one
    leaves an empty row rather than shifting the others; with one, only
    the streams carrying it are drawn. The graphic shows every match;
    the flat list below it is paginated (`RIBBON_PAGE_SIZE`), and a page
    past the end shows the last one.
    """

    all_streams = sorted({str(entry["stream"]) for entry in entries})
    badges = ribbon_badges(entries)
    visible = set(streams) if submitted else set(all_streams)

    filtered: list[Entry] = []
    marks: list[RibbonMark] = []
    for entry in entries:
        if entry["stream"] not in visible or (subject and not _about(entry, subject)):
            continue
        badge = badges[str(entry["stream"])]
        href = node_href(str(entry["iri"]))
        filtered.append({**entry, "badge": badge, "href": href})
        marks.append(_mark(entry, badge, href))

    lane_streams = sorted({m.stream for m in marks}) if subject else all_streams
    docker_svg, hosts_svg, observation_svg = ribbon_svgs(marks, lane_streams)

    total_pages = max(1, -(-len(filtered) // RIBBON_PAGE_SIZE))
    current_page = min(page, total_pages)
    start = (current_page - 1) * RIBBON_PAGE_SIZE

    return {
        "entries": filtered[start : start + RIBBON_PAGE_SIZE],
        "ribbon_svg_docker": docker_svg.markup,
        "ribbon_svg_docker_mark_count": docker_svg.mark_count,
        "ribbon_svg_hosts": hosts_svg.markup,
        "ribbon_svg_hosts_mark_count": hosts_svg.mark_count,
        "ribbon_svg_observation": observation_svg.markup,
        "ribbon_svg_observation_mark_count": observation_svg.mark_count,
        "filter_streams": [
            {"stream": stream, "badge": badges[stream], "checked": stream in visible}
            for stream in all_streams
        ],
        "submitted": submitted,
        "subject": subject,
        "page": current_page,
        "total_pages": total_pages,
        "total_entries": len(filtered),
        "page_size": RIBBON_PAGE_SIZE,
    }


def node_ribbon_panel(entries: list[Entry], subject: str | None, node_href: NodeHref) -> dict[str, Any]:
    """The chronology `/node` embeds for the node's own subject — the
    same marks and badges `/ribbon?subject=` draws, without its filter
    form, pagination or script. Nothing without a subject."""

    if subject is None:
        return {"has_subject": False}

    badges = ribbon_badges(entries)
    marks = [
        _mark(entry, badges[str(entry["stream"])], node_href(str(entry["iri"])))
        for entry in entries
        if _about(entry, subject)
    ]
    docker_svg, hosts_svg, observation_svg = ribbon_svgs(marks, sorted({m.stream for m in marks}))

    return {
        "has_subject": True,
        "subject": subject,
        "has_marks": bool(marks),
        "ribbon_svg_docker": docker_svg.markup,
        "ribbon_svg_docker_mark_count": docker_svg.mark_count,
        "ribbon_svg_hosts": hosts_svg.markup,
        "ribbon_svg_hosts_mark_count": hosts_svg.mark_count,
        "ribbon_svg_observation": observation_svg.markup,
        "ribbon_svg_observation_mark_count": observation_svg.mark_count,
    }


def reconstitution(
    store: GraphStore,
    entries: list[Entry],
    subject: str,
    as_of: str,
    node_href: NodeHref,
) -> dict[str, Any]:
    """
    What was known about `subject` at `as_of`: for each stream carrying
    it, the latest entry at or before that instant, with its facts —
    or, honestly, that the stream had none yet (`has_observation`). A
    collection gap is shown as the gap it is, never with its facts as
    if it answered "what was true then". Instants compare as strings:
    every one is the same ISO-8601 `Z` shape.

    Read-only and one subject (owner's cadrage, 2026-10-02): no
    then/now comparison, no restore into a sandbox — a write this
    screen may not make (`ADR-0011` § *Decision* 10).
    """

    about = [entry for entry in entries if _about(entry, subject)]
    badges = ribbon_badges(entries)
    rows: list[dict[str, Any]] = []

    for stream in sorted({str(entry["stream"]) for entry in about}):
        candidates = [
            entry
            for entry in about
            if entry["stream"] == stream and str(entry["instant"]) <= as_of
        ]
        if not candidates:
            rows.append({"stream": stream, "badge": badges[stream], "has_observation": False})
            continue

        latest = max(candidates, key=lambda entry: str(entry["instant"]))
        iri = str(latest["iri"])
        rows.append(
            {
                "stream": stream,
                "badge": badges[stream],
                "has_observation": True,
                "href": node_href(iri),
                "instant": str(latest["instant"]),
                "is_occurred_at": bool(latest["is_occurred_at"]),
                "is_gap": bool(latest["is_gap"]),
                "facts": [] if latest["is_gap"] else entity_facts(store, iri),
            }
        )

    return {"subject": subject, "as_of": as_of, "has_streams": bool(rows), "rows": rows}


# --------------------------------------------------------------------
# Explications
# --------------------------------------------------------------------


def explication_panel(subject: str, generated_dir: Path) -> dict[str, Any]:
    """
    Every recorded version of `subject`'s Explication, oldest first,
    read from the Explications store (the graph holds only that one
    exists, not its text), with what an administrator may do next
    (`ADR-0015`): `expected` is the number of versions the forms are
    drawn from.
    """

    history = versions(subject, generated_dir / EXPLICATIONS_DIR)
    if not history:
        return {"subject": subject, "has_explication": False, "expected": 0, "current_text": ""}

    current = history[-1].artifact
    current_status = status_of(current)

    return {
        "subject": subject,
        "has_explication": True,
        "expected": len(history),
        "current_text": "" if current_status == DISCARDED else current.content,
        "can_validate": current_status not in (VALIDATED, DISCARDED),
        "current_author": current.source,
        "can_discard": current_status != DISCARDED,
        "versions": [
            {
                "content": version.artifact.content,
                "confidence": version.artifact.confidence,
                "explication_status": version.artifact.metadata.get("explication_status"),
                "source": version.artifact.metadata.get("author_name") or version.artifact.source,
                "validated_by": version.artifact.metadata.get("validated_by_name"),
                "discarded_by": version.artifact.metadata.get("discarded_by_name"),
                "discard_reason": version.artifact.metadata.get("discard_reason"),
                "created_at": version.artifact.created_at.isoformat(),
                "is_current": index == len(history) - 1,
            }
            for index, version in enumerate(history)
        ],
    }


EXPLICATION_STATUSES = (PROPOSED, VALIDATED, DISCARDED)


def explication_list(generated_dir: Path, status: str = "", query: str = "") -> dict[str, Any]:
    """
    Every subject that has an Explication, with its current version's
    status, confidence, author and date (`ADR-0015`): the way in to the
    Explication pages, filtered by status and by a word of the subject.
    Read from the Explications store, so it answers without a graph.
    """

    explications_dir = generated_dir / EXPLICATIONS_DIR
    status = status if status in EXPLICATION_STATUSES else ""
    query = query.strip()

    rows: list[dict[str, Any]] = []
    counts = {name: 0 for name in EXPLICATION_STATUSES}
    for stem in available_stems(explications_dir):
        subject = subject_for_stem(stem)
        history = versions(subject, explications_dir)
        if not history:
            continue
        current = history[-1].artifact
        current_status = status_of(current)
        if current_status in counts:
            counts[current_status] += 1
        if status and current_status != status:
            continue
        if query and query.lower() not in subject.lower():
            continue
        rows.append(
            {
                "subject": subject,
                "status": current_status,
                "confidence": current.confidence,
                "author": current.metadata.get("author_name") or current.source,
                "validated_by": current.metadata.get("validated_by_name"),
                "recorded": current.created_at.strftime("%Y-%m-%d %H:%M"),
                "versions": len(history),
            }
        )

    rows.sort(key=lambda row: row["subject"].lower())
    return {
        "rows": rows,
        "status": status,
        "query": query,
        "counts": counts,
        "total": sum(counts.values()),
    }


def live_network_tree(
    kernel: Any, generated_dir: Path, topology: Path, network_discovery: Path
) -> list[NetworkTreeNode]:
    """
    Réseau ⊃ Hôte ⊃ Stack ⊃ Conteneur, from the live Docker and Compose
    catalogs (`ADR-0011` § 18) — not from the graph, which does not hold
    this structure — the local host named by the topology's first
    hardware entry, and the remote hosts of the last network scan.
    """

    from aistack.architecture.yaml import load_infrastructure_topology_yaml
    from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
    from aistack.catalog.docker import DockerRuntimeCatalogBuilder
    from aistack.network_discovery.yaml import load_network_discovery_yaml
    from aistack.timemachine.tree import build_network_tree

    providers = kernel.registries.providers
    hardware = load_infrastructure_topology_yaml(topology).hardware

    return build_network_tree(
        cidr=load_network_discovery_yaml(network_discovery).cidr,
        local_host_label=hardware[0].name if hardware else "",
        docker_catalog=DockerRuntimeCatalogBuilder().build(providers.get("docker").collect()),
        compose_catalog=ComposeRuntimeCatalogBuilder().build(providers.get("compose").collect()),
        remote_hosts=last_remote_hosts(generated_dir),
    )

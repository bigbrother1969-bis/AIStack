"""
`aistack.timemachine.screen` — what the Time Machine shows, against a
real graph built by the production projections
(`tests/unit/timemachine_sample.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.timemachine.screen import (
    RIBBON_PAGE_SIZE,
    ExpiringValue,
    RibbonEntries,
    explication_panel,
    filter_tree,
    graph_version,
    iri_term,
    node_instant,
    node_ribbon_panel,
    node_stable_subject,
    node_view,
    open_graph,
    provenance_neighbors,
    reconstitution,
    ribbon_badges,
    ribbon_entries,
    ribbon_page,
    stream_list,
    tree_context,
)
from aistack.timemachine.vocabulary import AISTACK_OCCURRED_AT, PROV_GENERATED_AT_TIME
from tests.unit.timemachine_sample import SUBJECT, build_sample_graph, sample_tree

DECISIONS = "urn:aistack:stream:priority-decision"
FIRST_DECISION = "urn:aistack:observation:priority-decision:2026-10-01T10-00-00Z"


def href(iri: str) -> str:
    return f"/node/{iri}"


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_sample_graph(tmp_path_factory.mktemp("generated"))


@pytest.fixture
def store(generated: Path):
    graph = open_graph(generated)
    assert graph is not None
    return graph


def test_no_graph_yet_is_none_not_an_error(tmp_path: Path):
    assert open_graph(tmp_path) is None
    assert graph_version(tmp_path) == 0.0


def test_the_streams_are_listed_by_name(store):
    assert [s["label"] for s in stream_list(store)] == ["docker-observation", "priority-decision"]


@pytest.mark.parametrize("iri", ["", "urn:x>", "urn:<x", "urn:x\n"])
def test_an_iri_that_could_break_out_of_the_query_is_refused(iri: str):
    with pytest.raises(ValueError):
        iri_term(iri)


def test_a_stream_lists_its_instants_newest_first(store):
    view = node_view(store, DECISIONS)

    assert view.type_label_key == "timemachine.type_label.activity"
    assert [i["iri"].rsplit(":", 1)[1] for i in view.instants or []] == [
        "2026-10-02T10-00-00Z",
        "2026-10-01T10-00-00Z",
    ]
    # The instants are not repeated among what points at the stream.
    assert all(ref["predicate_label_key"] != "timemachine.predicate.generated_by" for ref in view.referenced_by)


def test_an_entity_shows_its_facts_subject_and_instant(store):
    view = node_view(store, FIRST_DECISION)

    assert view.instants is None
    assert node_stable_subject(view.facts) == SUBJECT
    assert node_instant(view.facts) == "2026-10-01T10:00:00Z"
    assert any(fact["object_iri"] == DECISIONS for fact in view.facts)


def test_an_occurrence_instant_wins_over_the_recording_instant():
    facts = [
        {"predicate": PROV_GENERATED_AT_TIME, "object": "2026-10-02T00:00:00Z"},
        {"predicate": AISTACK_OCCURRED_AT, "object": "2026-10-01T23:59:00Z"},
    ]

    assert node_instant(facts) == "2026-10-01T23:59:00Z"
    assert node_instant([]) is None


def test_the_provenance_diagram_draws_real_neighbours_only(store):
    neighbors = provenance_neighbors(node_view(store, FIRST_DECISION), lambda key, **_: key, href)

    assert {(n.direction, n.href) for n in neighbors} >= {("out", href(DECISIONS))}
    # The type badge (prov:Entity) is a label, never an edge.
    assert all("prov#Entity" not in n.href for n in neighbors)


def test_the_tree_keeps_a_match_and_its_ancestors():
    kept = [node.label for node in filter_tree(sample_tree(), "BOOK")]

    assert kept == ["192.168.1.0/24", "GIGABYTE", "booklore", SUBJECT]
    assert filter_tree(sample_tree(), "  ") == sample_tree()


def test_the_tree_links_a_node_with_history_and_says_when_a_search_finds_nothing(store):
    context = tree_context(sample_tree(), store, "")
    container = context["root"]["children"][0]["children"][0]["children"][0]

    assert container["label"] == SUBJECT
    assert container["has_historique"] is True
    assert container["kind_label_key"] == "timemachine.tree.kind_label.container"

    empty = tree_context(sample_tree(), store, "nothing-like-this")
    assert empty["root"] is None and empty["search_empty"] is True
    assert tree_context(sample_tree(), None, "")["root"]["children"][0]["has_historique"] is False


def test_the_tree_is_rebuilt_only_once_its_time_is_up():
    now = [0.0]
    builds: list[int] = []
    cached = ExpiringValue(lambda: builds.append(1) or len(builds), ttl_seconds=45, clock=lambda: now[0])

    assert cached.get() == 1
    now[0] = 44.9
    assert cached.get() == 1
    now[0] = 45.0
    assert cached.get() == 2


def test_the_ribbon_entries_are_read_again_only_after_a_rebuild(generated: Path, store):
    calls: list[int] = []

    class Counting:
        def query(self, sparql: str):
            calls.append(1)
            return store.query(sparql)

    cache = RibbonEntries(generated)
    first = cache.get(Counting())  # type: ignore[arg-type]
    assert cache.get(Counting()) is first  # type: ignore[arg-type]
    assert len(calls) == 2  # the entries and the gaps, once


def test_a_stream_keeps_its_badge_whatever_is_filtered(store):
    entries = ribbon_entries(store)
    badges = ribbon_badges(entries)

    page = ribbon_page(entries, streams=["priority-decision"], submitted=True, subject="", page=1, node_href=href)

    assert {row["stream"] for row in page["entries"]} == {"priority-decision"}
    assert page["filter_streams"][0]["badge"] == badges["docker-observation"]
    assert page["filter_streams"][0]["checked"] is False


def test_a_submitted_form_with_nothing_checked_shows_nothing_a_bare_link_shows_all(store):
    entries = ribbon_entries(store)

    assert ribbon_page(entries, streams=[], submitted=True, subject="", page=1, node_href=href)["total_entries"] == 0
    assert ribbon_page(entries, streams=[], submitted=False, subject="", page=1, node_href=href)["total_entries"] == 3


def test_a_subject_narrows_the_ribbon_to_its_own_instants(store):
    page = ribbon_page(ribbon_entries(store), streams=[], submitted=False, subject=SUBJECT, page=1, node_href=href)

    assert page["total_entries"] == 2
    assert all(row["href"].startswith("/node/") for row in page["entries"])


def test_the_list_is_paginated_and_a_page_past_the_end_shows_the_last(store):
    entry = ribbon_entries(store)[0]
    many = [{**entry, "iri": f"urn:x:{n}"} for n in range(RIBBON_PAGE_SIZE + 5)]

    last = ribbon_page(many, streams=[], submitted=False, subject="", page=9, node_href=href)

    assert (last["page"], last["total_pages"], len(last["entries"])) == (2, 2, 5)


def test_a_node_without_a_subject_embeds_no_chronology(store):
    entries = ribbon_entries(store)

    assert node_ribbon_panel(entries, None, href) == {"has_subject": False}
    panel = node_ribbon_panel(entries, SUBJECT, href)
    assert panel["has_marks"] is True
    assert panel["ribbon_svg_observation_mark_count"] >= 1


def test_reconstitution_takes_the_latest_entry_at_or_before_the_instant(store):
    entries = ribbon_entries(store)

    (row,) = reconstitution(store, entries, SUBJECT, "2026-10-01T23:00:00Z", href)["rows"]
    assert row["has_observation"] is True
    assert row["instant"] == "2026-10-01T10:00:00Z"
    assert any(fact["predicate_label_key"] == "timemachine.predicate.stable_subject" for fact in row["facts"])

    (before,) = reconstitution(store, entries, SUBJECT, "2026-09-30T00:00:00Z", href)["rows"]
    assert before == {"stream": "priority-decision", "badge": before["badge"], "has_observation": False}

    assert reconstitution(store, entries, "unknown", "2026-10-02T00:00:00Z", href)["has_streams"] is False


def test_the_explications_of_a_subject_are_read_from_their_store(generated: Path):
    panel = explication_panel(SUBJECT, generated)

    assert panel["has_explication"] is True
    (version,) = panel["versions"]
    assert version["is_current"] is True
    assert "nightly scan" in version["content"]
    assert explication_panel("unknown", generated) == {
        "subject": "unknown",
        "has_explication": False,
        "expected": 0,
        "current_text": "",
    }

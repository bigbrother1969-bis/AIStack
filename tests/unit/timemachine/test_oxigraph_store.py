from __future__ import annotations

import pytest

from aistack.timemachine.graph import Literal
from aistack.timemachine.oxigraph_store import OxigraphGraphStore


def test_a_fact_added_with_an_iri_object_is_read_back_as_two_plain_iris():
    """
    `GraphStore.add`'s common case — `subject`/`predicate`/`obj` all
    IRIs (a bare `str`) — exercised against a real, in-memory
    `pyoxigraph.Store`, the same "a real engine, not a mock"
    convention `tests/integration/scripts/test_sync_mirrors.py` holds
    for git. `query` must hand back a plain string, not the RDF term's
    own syntax (`<...>`) that `str(term)` would carry.
    """
    store = OxigraphGraphStore()

    store.add(
        "https://example/container-a",
        "http://www.w3.org/ns/prov#wasGeneratedBy",
        "https://example/collector-run-1",
    )

    rows = list(
        store.query(
            "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
        )
    )

    assert rows == [
        {
            "s": "https://example/container-a",
            "p": "http://www.w3.org/ns/prov#wasGeneratedBy",
            "o": "https://example/collector-run-1",
        }
    ]


def test_a_fact_added_with_a_literal_object_keeps_its_plain_value():
    """
    `Literal` states a value rather than a reference — a timestamp,
    here — and `query` must read it back as the bare string
    `GraphStore`'s contract promises, not `pyoxigraph.Literal`'s own
    `"2026-09-27T10:00:00Z"^^<...>` syntax.
    """
    store = OxigraphGraphStore()

    store.add(
        "https://example/fact-1",
        "http://www.w3.org/ns/prov#generatedAtTime",
        Literal(
            "2026-09-27T10:00:00Z",
            datatype="http://www.w3.org/2001/XMLSchema#dateTime",
        ),
    )

    rows = list(store.query("SELECT ?o WHERE { ?s ?p ?o }"))

    assert rows == [{"o": "2026-09-27T10:00:00Z"}]


def test_a_literal_added_with_no_datatype_is_a_plain_string():
    store = OxigraphGraphStore()

    store.add(
        "https://example/host-gigabyte",
        "https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack/vocab#clockSource",
        Literal("GIGABYTE:systemd-timesyncd"),
    )

    rows = list(store.query("SELECT ?o WHERE { ?s ?p ?o }"))

    assert rows == [{"o": "GIGABYTE:systemd-timesyncd"}]


def test_an_unbound_optional_variable_comes_back_as_none():
    """
    § *Decision* 9's `aistack:collectionGap` is exactly this case in
    practice: a query asking whether a fact exists must be able to
    tell "absent" (`None`) from "present and empty," which a stripped
    RDF term string alone could not distinguish if unbound rows were
    silently dropped instead of reported.
    """
    store = OxigraphGraphStore()

    store.add(
        "https://example/container-a",
        "http://www.w3.org/ns/prov#wasGeneratedBy",
        "https://example/collector-run-1",
    )

    rows = list(
        store.query(
            "SELECT ?s ?gap WHERE { "
            "?s <http://www.w3.org/ns/prov#wasGeneratedBy> ?g "
            "OPTIONAL { ?s <https://example/vocab#collectionGap> ?gap } "
            "}"
        )
    )

    assert rows == [{"s": "https://example/container-a", "gap": None}]


def test_clear_empties_the_store_for_a_full_rebuild():
    """
    § *Decision* 10 — reconstruction complète à la demande: a rebuild
    starts from nothing, never from a partial prior state.
    """
    store = OxigraphGraphStore()
    store.add("https://example/s", "https://example/p", "https://example/o")

    assert list(store.query("SELECT ?s WHERE { ?s ?p ?o }")) != []

    store.clear()

    assert list(store.query("SELECT ?s WHERE { ?s ?p ?o }")) == []


def test_query_refuses_ask_and_construct_forms():
    """
    `GraphStore`'s contract is `SELECT` only (`ADR-0011` § *Decision*
    1 names one `query` method, not three query forms) —
    `pyoxigraph.Store.query` answers `ASK`/`CONSTRUCT` with a
    `QueryBoolean`/`QueryTriples` result this adapter's row shape
    cannot express, so both are refused rather than silently
    misread.
    """
    store = OxigraphGraphStore()
    store.add("https://example/s", "https://example/p", "https://example/o")

    with pytest.raises(ValueError, match="SELECT"):
        list(store.query("ASK { ?s ?p ?o }"))

    with pytest.raises(ValueError, match="SELECT"):
        list(
            store.query(
                "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
            )
        )


def test_two_facts_about_the_same_subject_both_read_back():
    store = OxigraphGraphStore()

    store.add(
        "https://example/container-a",
        "https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack/vocab#stableSubject",
        Literal("aistack-core"),
    )
    store.add(
        "https://example/container-a",
        "http://www.w3.org/ns/prov#wasAttributedTo",
        "https://example/agent-collector",
    )

    rows = list(
        store.query(
            "SELECT ?p ?o WHERE { <https://example/container-a> ?p ?o }"
        )
    )

    assert len(rows) == 2
    assert {"aistack-core", "https://example/agent-collector"} == {
        row["o"] for row in rows
    }

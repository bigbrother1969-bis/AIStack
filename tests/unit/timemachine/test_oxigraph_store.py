from __future__ import annotations

import pytest

from aistack.timemachine.graph import Literal
from aistack.timemachine.oxigraph_store import OxigraphGraphStore


def test_read_only_reads_back_what_a_prior_read_write_handle_wrote(tmp_path):
    """
    `timemachine_ui`'s own shape: build the store once (as
    `aistack.cli.timemachine_rebuild` does), close that handle, then
    open a fresh read-only one and query it — the same round trip a
    request to the mini-app performs.
    """
    store_path = tmp_path / "graph"
    writer = OxigraphGraphStore(store_path)
    writer.add("https://example/s", "https://example/p", "https://example/o")
    del writer

    reader = OxigraphGraphStore.read_only(store_path)

    assert list(reader.query("SELECT ?o WHERE { ?s ?p ?o }")) == [
        {"o": "https://example/o"}
    ]


def test_read_only_on_a_missing_path_raises_file_not_found(tmp_path):
    """
    A real signal (`aistack.cli.timemachine_rebuild` has never run
    against this `generated_dir`), not this adapter's own error — it
    propagates unwrapped so a caller can tell "no store yet" from any
    other failure.
    """
    with pytest.raises(FileNotFoundError):
        OxigraphGraphStore.read_only(tmp_path / "never-built")


def test_read_only_does_not_conflict_with_a_concurrent_read_write_handle(tmp_path):
    """
    `pyoxigraph.Store(path)`'s own exclusive lock (regression-tested
    below by its absence here) is what makes reopening a plain
    read-write handle on a live path fail — `read_only` measured
    2026-09-27 not to hit it, which is what lets `timemachine_ui`
    open a fresh handle per request without coordinating with
    whichever process last ran the rebuild command.
    """
    store_path = tmp_path / "graph"
    writer = OxigraphGraphStore(store_path)
    writer.add("https://example/s", "https://example/p", "https://example/o")

    reader = OxigraphGraphStore.read_only(store_path)

    assert list(reader.query("SELECT ?o WHERE { ?s ?p ?o }")) == [
        {"o": "https://example/o"}
    ]


def test_read_only_add_raises_runtime_error(tmp_path):
    """
    Not disabled by this adapter — `pyoxigraph` itself refuses a
    transaction on a read-only handle, which is exactly the
    fail-loud behaviour a caller that mixed up `read_only` and the
    constructor should see, rather than a silent no-op.
    """
    store_path = tmp_path / "graph"
    OxigraphGraphStore(store_path).add(
        "https://example/s", "https://example/p", "https://example/o"
    )

    reader = OxigraphGraphStore.read_only(store_path)

    with pytest.raises(RuntimeError):
        reader.add("https://example/s2", "https://example/p", "https://example/o")

    with pytest.raises(RuntimeError):
        reader.clear()


def test_a_real_path_persists_and_creates_only_its_own_leaf_directory(tmp_path):
    """
    `pyoxigraph.Store`'s own documented behaviour creates the
    directory its `path` names when missing — measured here to cover
    only that leaf, never its parents: a caller wanting the whole
    chain created still calls `Path.mkdir(parents=True,
    exist_ok=True)` itself first, as `aistack.cli.timemachine_rebuild`
    does.
    """
    leaf = tmp_path / "graph"
    store = OxigraphGraphStore(leaf)
    store.add("https://example/s", "https://example/p", "https://example/o")

    assert leaf.is_dir()

    # `pyoxigraph.Store` holds an exclusive lock on `path` for as long
    # as this object is alive (RocksDB's own `LOCK` file) — dropped
    # before reopening the same path, the same discipline a real
    # second process would need to observe too.
    del store

    reopened = OxigraphGraphStore(leaf)
    assert list(reopened.query("SELECT ?s WHERE { ?s ?p ?o }")) == [
        {"s": "https://example/s"}
    ]


def test_a_real_path_with_a_missing_parent_raises(tmp_path):
    missing_parent = tmp_path / "a" / "b" / "graph"

    with pytest.raises(OSError):
        OxigraphGraphStore(missing_parent)


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

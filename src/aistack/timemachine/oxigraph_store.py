from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pyoxigraph

from aistack.timemachine.graph import Literal


class OxigraphGraphStore:
    """
    `aistack.timemachine.graph.GraphStore`'s only implementation today
    (`ADR-0011` § *Decision* 1) — a thin adapter over
    `pyoxigraph.Store`. Every RDF term crosses the boundary in exactly
    one direction: a plain `str`/`Literal` goes in as a real term on
    `add`, and every term `query` reads back comes out as the plain
    string `GraphStore`'s own contract promises — no caller of
    `GraphStore` ever needs to import `pyoxigraph` itself.

    `path=None` keeps the store in memory, entirely disposable —
    every test of this class uses exactly that, the same "a real
    engine, never a mock" convention
    `tests/integration/scripts/test_sync_mirrors.py` already holds for
    git (real bare repositories under `tmp_path`, not a stubbed git
    client). A real `path` persists to disk under that directory,
    created if it does not exist yet (`pyoxigraph.Store`'s own
    documented behaviour) — **only that leaf directory, never its
    parents**, measured 2026-09-27 (`Store(".../a/b/graph")` raises
    `FileNotFoundError` when `.../a/b` does not already exist): a
    caller that wants the whole path created, not only the last
    segment, still calls `Path.mkdir(parents=True, exist_ok=True)`
    itself first (`aistack.cli.timemachine_rebuild` does exactly
    this). `ADR-0011` § *Decision* 1's own addendum names where the
    real store lives on disk (`<generated_dir>/timemachine/graph`)
    and its container volume.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._store = (
            pyoxigraph.Store(path) if path is not None else pyoxigraph.Store()
        )

    def add(self, subject: str, predicate: str, obj: str | Literal) -> None:
        object_term: pyoxigraph.NamedNode | pyoxigraph.Literal

        if isinstance(obj, Literal):
            object_term = (
                pyoxigraph.Literal(
                    obj.value, datatype=pyoxigraph.NamedNode(obj.datatype)
                )
                if obj.datatype is not None
                else pyoxigraph.Literal(obj.value)
            )
        else:
            object_term = pyoxigraph.NamedNode(obj)

        self._store.add(
            pyoxigraph.Quad(
                pyoxigraph.NamedNode(subject),
                pyoxigraph.NamedNode(predicate),
                object_term,
            )
        )

    def query(self, sparql: str) -> Iterator[dict[str, str | None]]:
        solutions = self._store.query(sparql)

        if not isinstance(solutions, pyoxigraph.QuerySolutions):
            # `GraphStore`'s contract is `SELECT` only (§ *Decision* 1
            # names `query`, not three query forms) — `pyoxigraph`
            # itself answers `ASK`/`CONSTRUCT` with a different result
            # shape (`QueryBoolean`/`QueryTriples`), neither of which
            # this adapter's caller-facing row shape can express.
            raise ValueError(
                "GraphStore.query only supports SPARQL SELECT; "
                f"got a {type(solutions).__name__} result"
            )

        variable_names = [variable.value for variable in solutions.variables]

        for row in solutions:
            yield {
                name: (row[name].value if row[name] is not None else None)
                for name in variable_names
            }

    def clear(self) -> None:
        self._store.clear()

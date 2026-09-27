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

    @classmethod
    def read_only(cls, path: str | Path) -> "OxigraphGraphStore":
        """
        Open an existing on-disk store for reading only — the shape
        `timemachine_ui` needs (`ADR-0011` § R1: a browsing screen,
        never a writer) without reaching for `pyoxigraph` itself.

        Two measured facts this method exists to encode rather than
        leave to each caller: `pyoxigraph.Store.read_only` on a path
        that has never been built raises `FileNotFoundError` — a real
        signal (the rebuild command has not run yet), not this
        adapter's own error, so it is left to propagate rather than
        swallowed. And a read-only handle never holds the exclusive
        read-write lock a plain `Store(path)` does — opening one
        alongside `aistack.cli.timemachine_rebuild`'s own read-write
        handle on the same path does not raise, measured 2026-09-27 —
        so a long-running screen is free to open a fresh one per
        request rather than share a single handle across the
        rebuild's own `store.clear()` (`pyoxigraph` itself documents
        reading concurrently with a *write in progress* as undefined,
        which a full rebuild — rare, and the owner's own deliberate
        action — is; reading between rebuilds is not).

        The returned instance's own `add`/`clear` are not disabled
        here — `pyoxigraph` itself refuses them (`RuntimeError:
        "Transaction are only possible on read-write instances"`),
        which is exactly the fail-loud behaviour a caller that mixed
        up `read_only` and the constructor should see.
        """

        instance = cls.__new__(cls)
        instance._store = pyoxigraph.Store.read_only(str(path))
        return instance

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

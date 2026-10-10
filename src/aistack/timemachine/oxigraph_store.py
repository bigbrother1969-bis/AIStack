from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pyoxigraph

from aistack.timemachine.graph import Literal


class OxigraphGraphStore:
    """
    `GraphStore` over `pyoxigraph.Store` (`ADR-0011` § 1).

    `path=None` keeps the store in memory. A `path` persists to disk;
    pyoxigraph creates only the leaf directory, so a caller creates the
    parents first (as `aistack.cli.timemachine_rebuild` does). The real
    store lives at `<generated_dir>/timemachine/graph`.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._store = (
            pyoxigraph.Store(path) if path is not None else pyoxigraph.Store()
        )

    @classmethod
    def read_only(cls, path: str | Path) -> "OxigraphGraphStore":
        """
        Open an existing on-disk store for reading only (the Time
        Machine screen never writes).

        Raises `FileNotFoundError` when the store was never built. A
        read-only handle does not take the read-write lock, so the
        screen can open one per request while the rebuild holds its
        own; reading during a rebuild's write is undefined in
        pyoxigraph. `add`/`clear` on the result raise `RuntimeError`
        from pyoxigraph.
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
            # `GraphStore.query` is `SELECT` only: `ASK`/`CONSTRUCT`
            # results have no row shape.
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

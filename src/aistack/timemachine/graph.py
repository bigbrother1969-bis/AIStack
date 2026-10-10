from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass(frozen=True)
class Literal:
    """
    A literal value for `GraphStore.add`'s object position.

    A bare `str` object is always read as an IRI; a value (a timestamp,
    a plain string) is wrapped in `Literal`. `datatype` is an XSD IRI
    (e.g. `"http://www.w3.org/2001/XMLSchema#dateTime"`), or `None` for
    a plain string.
    """

    value: str
    datatype: str | None = None


class GraphStore(Protocol):
    """
    What the Time Machine's projection asks of a graph engine
    (`ADR-0011` § 1), so an engine swap touches one adapter.
    `OxigraphGraphStore` is the implementation.

    `add` writes one fact, `query` reads with SPARQL, `clear` empties
    the store for a full rebuild (§ 10). No library type crosses this
    surface: objects are a `str` (IRI) or a `Literal`, and query rows
    are plain strings (`http://example/s`, not `<http://example/s>`).
    """

    def add(self, subject: str, predicate: str, obj: str | Literal) -> None:
        """
        State one fact: `subject` and `predicate` are IRIs; `obj` is
        an IRI (a bare `str`) or a value (a `Literal`).
        """
        ...

    def query(self, sparql: str) -> Iterator[dict[str, str | None]]:
        """
        Run a SPARQL `SELECT` query and yield one `dict` per row,
        mapping each of its variables' names (without the leading
        `?`) to its plain string value, or `None` for a variable that
        row leaves unbound.
        """
        ...

    def clear(self) -> None:
        """Empty the store before a full rebuild (`ADR-0011` § 10)."""
        ...

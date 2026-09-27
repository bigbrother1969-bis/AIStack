from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass(frozen=True)
class Literal:
    """
    A literal value for `GraphStore.add`'s object position.

    A bare `str` passed as `obj` is always read as an IRI — the common
    case, since most PROV-O predicates this heritage uses relate two
    named things (`prov:wasGeneratedBy`, `aistack:partOf`, ...). A fact
    whose object is a *value* rather than a reference
    (`prov:generatedAtTime`'s timestamp, an `aistack:clockSource`
    string) states that explicitly through this wrapper, rather than
    through a second, easy-to-forget argument every caller would have
    to remember to pass.

    `datatype` is an XSD IRI
    (`"http://www.w3.org/2001/XMLSchema#dateTime"` for a timestamp),
    left `None` for a plain string — typing a literal is RDF's own
    job, not an `aistack:` extension, so nothing here invents a
    vocabulary for it.
    """

    value: str
    datatype: str | None = None


class GraphStore(Protocol):
    """
    What the Time Machine's projection asks of any graph engine that
    stores its facts — `ADR-0011` § *Decision* 1: "a future engine
    swap (R9 of ADR-0009's own kind of caution, not yet a real need)
    touches one adapter, not every caller." `pyoxigraph`
    (`aistack.timemachine.oxigraph_store.OxigraphGraphStore`) is the
    only implementation today; this contract is not speculative
    plumbing for engines nobody has chosen (`ARC-P-006`) — it is the
    same "neutral interface in front of one real implementation"
    `ADR-0005`'s Context Bundle Engine already established for a
    comparable reason.

    **Three methods, matching § *Decision* 1 exactly.** `add` writes
    one fact, `query` reads with SPARQL, `clear` empties the store for
    a full rebuild (§ *Decision* 10 — reconstruction complète à la
    demande, never incremental, never partial). Nothing in this
    surface names Oxigraph, an RDF term, or any library type: `add`'s
    object position is either a plain `str` (an IRI) or a `Literal` (a
    value), so a caller never imports `pyoxigraph` just to state a
    fact.

    **Rows come back as plain strings, not RDF terms.** A term's own
    string form carries RDF's own syntax (`<http://example/s>`,
    `"hello"@en`) — converting that back to a bare value is the
    store's job, not every caller's; `query` resolves each bound
    variable to its plain string (`http://example/s`, `hello`) so a
    caller can compare or store it without first parsing that syntax
    back out.
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
        """Empty the store — § *Decision* 10's full rebuild starts here."""
        ...

"""
Shared IRI construction for the Time Machine graph (`ADR-0011`).

One place names how a stream, an observation, an agent or a request
becomes an IRI — the same reasoning `aistack.history.format_instant`/
`parse_instant` already holds for the one filename-safe rendering of
an instant, shared by writer and reader so the two can never silently
disagree.

`aistack.timemachine.projection` is the only writer today (it built
these four functions inline before this module existed, 2026-09-27).
`timemachine_ui`, a browsing screen over the graph, is the first
reader — it only ever needs `stream_stem` (to show a stream's own
name, not its full URN, once a query has already handed it the IRI)
and never constructs an IRI itself; every IRI it links to comes
straight out of a SPARQL result, never rebuilt from parts. The three
builders below exist for the writer, and for round-trip tests.
"""

from __future__ import annotations

_STREAM_PREFIX = "urn:aistack:stream:"
_OBSERVATION_PREFIX = "urn:aistack:observation:"
_AGENT_PREFIX = "urn:aistack:agent:"
_REQUEST_PREFIX = "urn:aistack:request:"


def stream_iri(stem: str) -> str:
    """The IRI of `stem`'s own collection activity (`prov:Activity`)."""

    return f"{_STREAM_PREFIX}{stem}"


def stream_stem(iri: str) -> str | None:
    """
    The stem `stream_iri` built `iri` from, or `None` when `iri` is
    not one of this module's own stream IRIs.

    A defensive read, not an assertion: a screen showing whatever the
    graph actually holds should degrade to the raw IRI on anything
    unexpected rather than raise — the graph is a projection someone
    else's SPARQL query, or a future stream this module does not know
    about yet, could also have written to.
    """

    if not iri.startswith(_STREAM_PREFIX):
        return None
    return iri[len(_STREAM_PREFIX) :]


def observation_iri(stem: str, instant_label: str) -> str:
    """The IRI of one historicised observation (`prov:Entity`)."""

    return f"{_OBSERVATION_PREFIX}{stem}:{instant_label}"


def agent_iri(origin: str) -> str:
    """The IRI of the `prov:Agent` a `provenance.origin` names."""

    return f"{_AGENT_PREFIX}{origin}"


def request_iri(causality: str) -> str:
    """The IRI of the causal request a `provenance.causality` names."""

    return f"{_REQUEST_PREFIX}{causality}"

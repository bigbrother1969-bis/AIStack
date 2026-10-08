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
and, since 1.4's provenance graph view (`ADR-0011` § 19),
`short_label` for the same reason across every other IRI shape this
module builds — it never constructs an IRI itself; every IRI it links
to comes straight out of a SPARQL result, never rebuilt from parts.
The eleven builders below exist for the writer, and for round-trip
tests.
"""

from __future__ import annotations

_STREAM_PREFIX = "urn:aistack:stream:"
_OBSERVATION_PREFIX = "urn:aistack:observation:"
_AGENT_PREFIX = "urn:aistack:agent:"
_REQUEST_PREFIX = "urn:aistack:request:"
_EXPLICATION_PREFIX = "urn:aistack:explication:"
_SUBJECT_PREFIX = "urn:aistack:subject:"
_DOCKER_EVENT_PREFIX = "urn:aistack:docker-event:"
_COLLECTION_GAP_PREFIX = "urn:aistack:collection-gap:"
_DOCKER_DIFF_PREFIX = "urn:aistack:docker-diff:"
_DOCKER_DIGEST_PREFIX = "urn:aistack:docker-digest:"
_DOCKER_PACKAGES_PREFIX = "urn:aistack:docker-packages:"
_DOCK_CHANGE_PREFIX = "urn:aistack:dock-change:"
_HOST_EVENT_PREFIX = "urn:aistack:host-event:"


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


def explication_iri(subject: str, instant_label: str) -> str:
    """
    The IRI of one Explication's own `prov:Entity` — `ADR-0011` § 7.
    Keyed by subject *and* instant, the same shape `observation_iri`
    already uses: a subject can gain more than one Explication over
    time (two different `explain` answers, a correction), and each is
    its own graph node, not a value overwriting the last.
    """

    return f"{_EXPLICATION_PREFIX}{subject}:{instant_label}"


def subject_iri(name: str) -> str:
    """
    The IRI of a bare subject an Explication explains (`aistack:
    explains`'s object) — `ADR-0011` § 7's own wording, "`id` names the
    subject explained". Not `stream_iri`: a Explication's subject (a
    `RuntimeFinding.subject` such as `"booklore_db"`, the thing a
    finding is *about*) is not the same kind of thing as a collection
    stream (`"architecture"`, `"console"`, the thing a *collector*
    produces) — the graph has no other node for most subjects yet,
    and minting one under `stream_iri` would claim a kinship with
    "this is a collector's own activity" that is not real.
    """

    return f"{_SUBJECT_PREFIX}{name}"


def docker_event_iri(instant_label: str, index: int) -> str:
    """
    The IRI of one Docker event's own `prov:Entity` — 1.5,
    `aistack.timemachine.projection.docker_events`. Keyed by the
    historicised batch's own instant *and* the event's position within
    it, the same reasoning `observation_iri` already holds for
    `stem:instant_label`: one poll cycle can (and typically does)
    record several events at once, so `instant_label` alone would
    collide. `index` is the event's own position in that batch's
    `events` list — stable for as long as the batch file itself is
    never rewritten, which `write_artifact_with_history` already
    guarantees (a new write is a new history file, never an edit of
    one already on disk).
    """

    return f"{_DOCKER_EVENT_PREFIX}{instant_label}:{index}"


def collection_gap_iri(stream_stem: str, instant_label: str) -> str:
    """
    The IRI of one recorded collection gap's own `prov:Entity` —
    `ADR-0011` § 9 (R11), `aistack.timemachine.projection
    .collection_gaps`. Keyed by the stream it belongs to *and* the
    instant it was recorded, the same reasoning `docker_event_iri`
    already holds for `instant_label:index`: one stream can gap and
    resume more than once over its lifetime, so `stream_stem` alone
    would collide across separate gaps.
    """

    return f"{_COLLECTION_GAP_PREFIX}{stream_stem}:{instant_label}"


def docker_diff_iri(subject: str, instant_label: str) -> str:
    """
    The IRI of one `docker diff` snapshot's own `prov:Entity` — 1.5's
    second collector, `aistack.timemachine.projection.docker_diff`.
    Keyed by `subject` (§ 3's stable identity, which may itself embed
    a `/` for a Compose `project/service` pair — the same raw,
    unescaped embedding `explication_iri` already holds for a bare
    subject string) *and* the recording instant, the same reasoning
    `explication_iri` already holds: one subject gains a new snapshot
    on every write-on-change, so `subject` alone would collide across
    them.
    """

    return f"{_DOCKER_DIFF_PREFIX}{subject}:{instant_label}"


def docker_digest_iri(subject: str, instant_label: str) -> str:
    """
    The IRI of one image-digest observation's own `prov:Entity` —
    1.5's third collector, `aistack.timemachine.projection
    .docker_digest`. Keyed by `subject` and the recording instant, the
    same reasoning `docker_diff_iri` already holds: one subject gains
    a new observation on every write-on-change, so `subject` alone
    would collide across them.
    """

    return f"{_DOCKER_DIGEST_PREFIX}{subject}:{instant_label}"


def docker_packages_iri(subject: str, instant_label: str) -> str:
    """
    The IRI of one package-inventory snapshot's own `prov:Entity` —
    1.5's fourth and last named collector, `aistack.timemachine
    .projection.docker_packages`. Keyed by `subject` and the recording
    instant, the same reasoning `docker_digest_iri` already holds: one
    subject gains a new snapshot on every write-on-change, so
    `subject` alone would collide across them.
    """

    return f"{_DOCKER_PACKAGES_PREFIX}{subject}:{instant_label}"


def dock_change_iri(proposal_id: str, container: str = "") -> str:
    """
    The IRI of one governed change (1.10, `ADR-0019` § 6): the dock's
    `prov:Activity`, keyed by its proposal — unique, and the name the
    Quai page and `python -m aistack.cli.dock show` already give it —
    or, with `container`, the `prov:Entity` of one image it changed.
    """

    return f"{_DOCK_CHANGE_PREFIX}{proposal_id}" + (f":{container}" if container else "")


def host_event_iri(host: str, line: int) -> str:
    """
    The IRI of one event a host collector recorded (1.11, `ADR-0020`):
    keyed by the host and the event's line in its `events.jsonl`,
    which is only ever appended to — the same line is the same event at
    every rebuild.
    """

    return f"{_HOST_EVENT_PREFIX}{host}:{line}"


_ALL_PREFIXES = (
    _STREAM_PREFIX,
    _OBSERVATION_PREFIX,
    _AGENT_PREFIX,
    _REQUEST_PREFIX,
    _EXPLICATION_PREFIX,
    _SUBJECT_PREFIX,
    _DOCKER_EVENT_PREFIX,
    _COLLECTION_GAP_PREFIX,
    _DOCKER_DIFF_PREFIX,
    _DOCKER_DIGEST_PREFIX,
    _DOCKER_PACKAGES_PREFIX,
    _DOCK_CHANGE_PREFIX,
    _HOST_EVENT_PREFIX,
)


def short_label(iri: str) -> str:
    """
    A short, human-readable label for any IRI this module builds —
    `stream_stem` generalised across all nine prefixes, added for 1.4's
    provenance graph view (`ADR-0011` § 19): a diagram centred on one
    node needs a real label for every neighbour it draws, not only a
    stream's own name.

    Defensive, like `stream_stem`: an IRI matching none of this
    module's own prefixes (a raw predicate IRI, something a future
    stream or a different SPARQL query wrote) returns unchanged rather
    than raising — the graph is a projection other code can also
    write to, and a screen showing whatever it actually holds should
    degrade to the full IRI rather than fail on one it does not
    recognise.
    """

    for prefix in _ALL_PREFIXES:
        if iri.startswith(prefix):
            return iri[len(prefix) :]
    return iri

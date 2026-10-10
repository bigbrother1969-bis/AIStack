"""
IRI construction for the Time Machine graph (`ADR-0011`), shared by
writer and reader so they cannot disagree.

The builders serve the projection. The screen never builds an IRI: it
takes them from SPARQL results and uses `stream_stem` and
`short_label` to display them.
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
    The stem `stream_iri` built `iri` from, or `None` (never raises)
    when `iri` is not a stream IRI.
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
    The IRI of one Explication version (`ADR-0011` § 7), keyed by
    subject and instant: each version is its own node.
    """

    return f"{_EXPLICATION_PREFIX}{subject}:{instant_label}"


def subject_iri(name: str) -> str:
    """
    The IRI of a subject an Explication explains (the object of
    `aistack:explains`), e.g. `"booklore_db"`. Distinct from
    `stream_iri`: a subject is not a collection stream.
    """

    return f"{_SUBJECT_PREFIX}{name}"


def docker_event_iri(instant_label: str, index: int) -> str:
    """
    The IRI of one Docker event, keyed by its batch's instant and its
    position in the batch (a batch holds several events). Stable,
    since history files are never rewritten.
    """

    return f"{_DOCKER_EVENT_PREFIX}{instant_label}:{index}"


def collection_gap_iri(stream_stem: str, instant_label: str) -> str:
    """
    The IRI of one collection gap (`ADR-0011` § 9), keyed by stream
    and recording instant, since a stream can gap more than once.
    """

    return f"{_COLLECTION_GAP_PREFIX}{stream_stem}:{instant_label}"


def docker_diff_iri(subject: str, instant_label: str) -> str:
    """
    The IRI of one `docker diff` snapshot, keyed by subject (which may
    contain an unescaped `/`) and recording instant.
    """

    return f"{_DOCKER_DIFF_PREFIX}{subject}:{instant_label}"


def docker_digest_iri(subject: str, instant_label: str) -> str:
    """The IRI of one image-digest observation, keyed by subject and instant."""

    return f"{_DOCKER_DIGEST_PREFIX}{subject}:{instant_label}"


def docker_packages_iri(subject: str, instant_label: str) -> str:
    """The IRI of one package-inventory snapshot, keyed by subject and instant."""

    return f"{_DOCKER_PACKAGES_PREFIX}{subject}:{instant_label}"


def dock_change_iri(proposal_id: str, container: str = "") -> str:
    """
    The IRI of one governed change (`ADR-0019` § 6): the dock's
    `prov:Activity`, keyed by its proposal — unique, and the name the
    Quai page and `python -m aistack.cli.dock show` already give it —
    or, with `container`, the `prov:Entity` of one image it changed.
    """

    return f"{_DOCK_CHANGE_PREFIX}{proposal_id}" + (f":{container}" if container else "")


def host_event_iri(host: str, line: int) -> str:
    """
    The IRI of one event a host collector recorded (`ADR-0020`):
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
    A short label for any IRI this module builds (its prefix removed),
    used by the provenance graph view (`ADR-0011` § 19). An unknown IRI
    is returned unchanged.
    """

    for prefix in _ALL_PREFIXES:
        if iri.startswith(prefix):
            return iri[len(prefix) :]
    return iri

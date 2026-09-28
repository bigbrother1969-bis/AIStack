from __future__ import annotations

from aistack.timemachine.iri import (
    agent_iri,
    collection_gap_iri,
    docker_diff_iri,
    docker_digest_iri,
    docker_event_iri,
    docker_packages_iri,
    explication_iri,
    observation_iri,
    request_iri,
    short_label,
    stream_iri,
    stream_stem,
    subject_iri,
)


def test_stream_stem_reads_back_what_stream_iri_built():
    assert stream_stem(stream_iri("observations")) == "observations"


def test_stream_stem_is_none_for_an_unrelated_iri():
    """
    A defensive read, not an assertion — a screen browsing whatever
    the graph actually holds should degrade to the raw IRI rather
    than raise on something that never came from `stream_iri`.
    """
    assert stream_stem("https://example/not-a-stream") is None
    assert stream_stem("urn:aistack:observation:traces:2026-09-27T10-00-00Z") is None


def test_observation_iri_embeds_both_the_stem_and_the_instant_label():
    iri = observation_iri("traces", "2026-09-27T10-00-00Z")
    assert iri == "urn:aistack:observation:traces:2026-09-27T10-00-00Z"


def test_agent_iri_embeds_the_origin():
    assert agent_iri("aistack.cli.ai_reason") == "urn:aistack:agent:aistack.cli.ai_reason"


def test_request_iri_embeds_the_causality():
    assert request_iri("req-42") == "urn:aistack:request:req-42"


def test_explication_iri_embeds_both_the_subject_and_the_instant_label():
    iri = explication_iri("booklore_db", "2026-09-27T10-00-00Z")
    assert iri == "urn:aistack:explication:booklore_db:2026-09-27T10-00-00Z"


def test_subject_iri_embeds_the_name():
    assert subject_iri("booklore_db") == "urn:aistack:subject:booklore_db"


def test_docker_event_iri_embeds_both_the_instant_label_and_the_index():
    iri = docker_event_iri("2026-09-28T10-00-00Z", 3)
    assert iri == "urn:aistack:docker-event:2026-09-28T10-00-00Z:3"


def test_collection_gap_iri_embeds_both_the_stream_and_the_instant_label():
    iri = collection_gap_iri("docker-events", "2026-09-28T10-05-00Z")
    assert iri == "urn:aistack:collection-gap:docker-events:2026-09-28T10-05-00Z"


def test_docker_diff_iri_embeds_both_the_subject_and_the_instant_label():
    iri = docker_diff_iri("arrstack/gluetun", "2026-09-28T10-00-00Z")
    assert iri == "urn:aistack:docker-diff:arrstack/gluetun:2026-09-28T10-00-00Z"


def test_docker_digest_iri_embeds_both_the_subject_and_the_instant_label():
    iri = docker_digest_iri("arrstack/gluetun", "2026-09-28T10-00-00Z")
    assert iri == "urn:aistack:docker-digest:arrstack/gluetun:2026-09-28T10-00-00Z"


def test_docker_packages_iri_embeds_both_the_subject_and_the_instant_label():
    iri = docker_packages_iri("arrstack/gluetun", "2026-09-28T10-00-00Z")
    assert iri == "urn:aistack:docker-packages:arrstack/gluetun:2026-09-28T10-00-00Z"


def test_short_label_strips_each_of_the_eleven_prefixes():
    assert short_label(stream_iri("observations")) == "observations"
    assert short_label(observation_iri("traces", "2026-09-27T10-00-00Z")) == (
        "traces:2026-09-27T10-00-00Z"
    )
    assert short_label(agent_iri("aistack.cli.ai_reason")) == "aistack.cli.ai_reason"
    assert short_label(request_iri("req-42")) == "req-42"
    assert short_label(explication_iri("booklore_db", "2026-09-27T10-00-00Z")) == (
        "booklore_db:2026-09-27T10-00-00Z"
    )
    assert short_label(subject_iri("booklore_db")) == "booklore_db"
    assert short_label(docker_event_iri("2026-09-28T10-00-00Z", 3)) == (
        "2026-09-28T10-00-00Z:3"
    )
    assert short_label(collection_gap_iri("docker-events", "2026-09-28T10-05-00Z")) == (
        "docker-events:2026-09-28T10-05-00Z"
    )
    assert short_label(docker_diff_iri("arrstack/gluetun", "2026-09-28T10-00-00Z")) == (
        "arrstack/gluetun:2026-09-28T10-00-00Z"
    )
    assert short_label(docker_digest_iri("arrstack/gluetun", "2026-09-28T10-00-00Z")) == (
        "arrstack/gluetun:2026-09-28T10-00-00Z"
    )
    assert short_label(docker_packages_iri("arrstack/gluetun", "2026-09-28T10-00-00Z")) == (
        "arrstack/gluetun:2026-09-28T10-00-00Z"
    )


def test_short_label_returns_an_unrecognised_iri_unchanged():
    assert short_label("https://example/not-ours") == "https://example/not-ours"
    assert short_label("urn:prov:something-else") == "urn:prov:something-else"


def test_the_eleven_builders_use_distinct_prefixes():
    """
    § *Decision* 1's own contract distinguishes an Entity, an
    Activity, an Agent and a request by IRI alone — two builders
    sharing a prefix could collide on the same identifier for two
    unrelated real-world things. Explications (§ 7) add two more:
    an Explication is its own Entity, distinct from the subject it
    explains. 1.5 (cadrage 2026-09-28) adds a seventh, one Docker
    event, and an eighth (R11, same day): one recorded collection
    gap is its own Entity too. A ninth, same day: one `docker diff`
    snapshot. A tenth, same day: one image-digest observation. An
    eleventh, 1.5.1 (cadrage 2026-09-28): one package-inventory
    snapshot, distinct from every other kind of Entity this module
    builds.
    """
    prefixes = {
        stream_iri("x").rsplit("x", 1)[0],
        observation_iri("x", "y").rsplit("x:y", 1)[0],
        agent_iri("x").rsplit("x", 1)[0],
        request_iri("x").rsplit("x", 1)[0],
        explication_iri("x", "y").rsplit("x:y", 1)[0],
        subject_iri("x").rsplit("x", 1)[0],
        docker_event_iri("x", 1).rsplit("x:1", 1)[0],
        collection_gap_iri("x", "y").rsplit("x:y", 1)[0],
        docker_diff_iri("x", "y").rsplit("x:y", 1)[0],
        docker_digest_iri("x", "y").rsplit("x:y", 1)[0],
        docker_packages_iri("x", "y").rsplit("x:y", 1)[0],
    }
    assert len(prefixes) == 11

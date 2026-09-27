from __future__ import annotations

from aistack.timemachine.iri import (
    agent_iri,
    observation_iri,
    request_iri,
    stream_iri,
    stream_stem,
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


def test_the_four_builders_use_distinct_prefixes():
    """
    § *Decision* 1's own contract distinguishes an Entity, an
    Activity, an Agent and a request by IRI alone — two builders
    sharing a prefix could collide on the same identifier for two
    unrelated real-world things.
    """
    prefixes = {
        stream_iri("x").rsplit("x", 1)[0],
        observation_iri("x", "y").rsplit("x:y", 1)[0],
        agent_iri("x").rsplit("x", 1)[0],
        request_iri("x").rsplit("x", 1)[0],
    }
    assert len(prefixes) == 4

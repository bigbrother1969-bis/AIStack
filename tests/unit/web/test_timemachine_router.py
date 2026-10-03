"""
*Time Machine* inside AIStack's single web application (`ADR-0012`).

A real graph, built by the production projections
(`tests/unit/timemachine_sample.py`); the live network tree is the only
collaborator replaced.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from aistack.i18n import Language, Languages
from aistack.web.app import create_app
from aistack.web.exposure import Listeners
from tests.unit.timemachine_sample import SUBJECT, build_sample_graph, sample_tree

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)

DECISIONS = "urn:aistack:stream:priority-decision"
FIRST_DECISION = "urn:aistack:observation:priority-decision:2026-10-01T10-00-00Z"


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_sample_graph(tmp_path_factory.mktemp("generated"))


def client(generated: Path, port: int = LAN_PORT) -> TestClient:
    app = create_app(generated, LISTENERS, LANGUAGES, network_tree=sample_tree)

    return TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False)


def node(iri: str) -> str:
    return f"/timemachine/node?iri={quote(iri, safe='')}"


@pytest.mark.parametrize("path", ["/timemachine", "/timemachine/"])
def test_the_streams_page_lists_every_stream(generated: Path, path: str):
    reply = client(generated).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert "priority-decision" in reply.text and "docker-observation" in reply.text
    assert f'href="{node(DECISIONS)}&amp;lang=en"' in reply.text
    assert 'href="/timemachine/tree?lang=en"' in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


def test_without_a_graph_every_graph_page_says_how_to_build_it(tmp_path: Path):
    web = client(tmp_path)

    for path in ("/timemachine/", node(DECISIONS), "/timemachine/ribbon", "/timemachine/explication"):
        reply = web.get(path + ("&" if "?" in path else "?") + "lang=en")
        assert reply.status_code == 200
        assert "timemachine_rebuild" in reply.text


def test_a_node_shows_its_three_columns(generated: Path):
    reply = client(generated).get(node(FIRST_DECISION) + "&lang=en")

    assert reply.status_code == 200
    # Left: the network tree, its node with history linked.
    assert f'href="/timemachine/ribbon?subject={SUBJECT}&amp;lang=en"' in reply.text
    # Centre: this subject's chronology, and the ways to go further.
    assert 'href="/timemachine/reconstitute?subject=booklore_db&amp;as_of=2026-10-01T10%3A00%3A00Z&amp;lang=en"' in reply.text
    assert 'href="/timemachine/explication?subject=booklore_db&amp;lang=en"' in reply.text
    # Right: the facts, and the provenance diagram with its script.
    assert f'href="{node(DECISIONS)}&amp;lang=en"' in reply.text
    assert 'id="provenance-graph"' in reply.text and "mermaid" in reply.text
    # The language switch keeps the node being read.
    assert f'href="?lang=fr&iri={quote(FIRST_DECISION)}"' in reply.text


def test_a_node_iri_that_could_break_the_query_is_a_bad_request(generated: Path):
    assert client(generated).get("/timemachine/node?iri=urn%3Ax%3E").status_code == 400


def test_the_tree_is_searchable(generated: Path):
    reply = client(generated).get("/timemachine/tree?q=frig&lang=en")

    assert reply.status_code == 200
    assert "frigate" in reply.text and ">booklore<" not in reply.text
    assert 'action="/timemachine/tree"' in reply.text
    assert 'href="?lang=fr&q=frig"' in reply.text


def test_the_tree_answers_without_a_graph(tmp_path: Path):
    reply = client(tmp_path).get("/timemachine/tree?lang=en")

    assert reply.status_code == 200
    assert SUBJECT in reply.text


def test_the_ribbon_filters_by_stream_and_keeps_the_filter_across_pages(generated: Path):
    reply = client(generated).get(
        "/timemachine/ribbon?streams=priority-decision&submitted=1&lang=en"
    )

    assert reply.status_code == 200
    assert 'action="/timemachine/ribbon"' in reply.text
    assert 'value="docker-observation"' in reply.text
    assert 'href="?lang=fr&streams=priority-decision&submitted=1"' in reply.text
    assert f'href="{node(FIRST_DECISION)}&amp;lang=en"' in reply.text


def test_reconstitution_and_explication_answer_for_a_subject(generated: Path):
    web = client(generated)

    rebuilt = web.get(
        "/timemachine/reconstitute?subject=booklore_db&as_of=2026-10-01T23:00:00Z&lang=en"
    )
    assert rebuilt.status_code == 200
    assert "2026-10-01T10:00:00Z" in rebuilt.text

    explained = web.get("/timemachine/explication?subject=booklore_db&lang=en")
    assert explained.status_code == 200
    assert "nightly scan" in explained.text

    assert web.get("/timemachine/reconstitute?lang=en").status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/timemachine", "/timemachine/", "/timemachine/tree", "/timemachine/ribbon", node(DECISIONS)],
)
def test_nothing_is_served_on_the_public_port(generated: Path, path: str):
    assert client(generated, PUBLIC_PORT).get(path).status_code == 404

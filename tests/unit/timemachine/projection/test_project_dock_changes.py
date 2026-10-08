"""
`project_dock_changes` — against a change the dock really executed
(fake Docker and sandbox, real proposal and explication stores).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from aistack.dock import proposals as store
from aistack.explications.human import versions
from aistack.timemachine.iri import agent_iri, dock_change_iri, explication_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_dock_changes
from aistack.timemachine.vocabulary import (
    AISTACK_CHANGE_OUTCOME,
    AISTACK_IMAGE_DIGEST,
    AISTACK_PREVIOUS_DIGEST,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_USED,
    PROV_WAS_ASSOCIATED_WITH,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)
from tests.unit.dock.test_dock_executor import NEW_DIGEST, NOW, FakeDocker, FakeRestorer, _dock, _proposal, _report


def _values(graph: OxigraphGraphStore, subject: str, predicate: str) -> set[str | None]:
    return {row["o"] for row in graph.query(f"SELECT ?o WHERE {{ <{subject}> <{predicate}> ?o }}")}


def test_an_executed_change_is_an_activity_with_its_people_images_and_why(tmp_path: Path):
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=1))
    (done,) = _dock(tmp_path, FakeDocker(), FakeRestorer()).run_all()

    graph = OxigraphGraphStore(tmp_path / "graph")
    summary = project_dock_changes(graph, generated_dir=tmp_path)

    activity = dock_change_iri(done.id)
    image = dock_change_iri(done.id, "wp_app")
    assert summary.changes_seen == 1
    assert _values(graph, activity, RDF_TYPE) == {PROV_ACTIVITY}
    assert _values(graph, activity, AISTACK_CHANGE_OUTCOME) == {"applied"}
    assert _values(graph, activity, PROV_WAS_ASSOCIATED_WITH) == {agent_iri("person:alice"), agent_iri("dock")}
    assert _values(graph, image, PROV_WAS_GENERATED_BY) == {activity}
    assert _values(graph, image, AISTACK_STABLE_SUBJECT) == {"wordpress/wordpress"}
    assert _values(graph, image, AISTACK_IMAGE_DIGEST) == {NEW_DIGEST}
    assert _values(graph, image, AISTACK_PREVIOUS_DIGEST) == {"sha256:" + "a" * 64}
    (why,) = versions("wordpress/wordpress", tmp_path / "explications")
    assert _values(graph, activity, PROV_USED) == {explication_iri("wordpress/wordpress", why.instant)}


def test_a_proposal_never_executed_is_not_an_activity(tmp_path: Path):
    _proposal(tmp_path)

    graph = OxigraphGraphStore(tmp_path / "graph")
    summary = project_dock_changes(graph, generated_dir=tmp_path)

    assert summary.changes_seen == 0 and summary.facts_written == 0
    assert store.all_proposals(tmp_path)[0].status == store.VALIDATED

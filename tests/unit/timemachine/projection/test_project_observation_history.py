from __future__ import annotations

import json
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.kernel.resolution import ResolutionResult
from aistack.kernel.tracing import ExecutionPhase, ExecutionTrace, ExecutionTraceEvent
from aistack.kernel.tracing.event import ExecutionTraceEventType
from aistack.kernel.tracing.repository.file import FileTraceRepository
from aistack.priority.apply import ApplyReport
from aistack.priority.decision_history import record_decision
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_observation_history
from aistack.timemachine.vocabulary import (
    AISTACK_STABLE_SUBJECT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_USED,
    PROV_WAS_ATTRIBUTED_TO,
)

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class _FakeTask:
    task_id = "task.fake"
    task_name = "Fake Task"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def _write_a_trace(generated_dir: Path) -> None:
    """
    A real Traces stream entry — `FileTraceRepository`, the exact
    class production uses, not a hand-typed JSON stand-in.
    """
    repository = FileTraceRepository(
        output_path=generated_dir / "execution-trace.json"
    )
    request = Request(request_id="request-001", task_id="task.fake")

    repository.save(
        ExecutionTrace(
            request=request,
            resolution=ResolutionResult(
                task=_FakeTask(), resolver="TaskResolver", reason="resolved"
            ),
            observation=Observation(
                context=ObservationContext(
                    request_id="request-001",
                    component_type="task",
                    component_id="task.fake",
                    operation="execute",
                ),
                data={"n": 1},
            ),
            events=(
                ExecutionTraceEvent(
                    phase=ExecutionPhase.REQUEST,
                    event_type=ExecutionTraceEventType.REQUEST_RECEIVED,
                    component="KernelRuntime",
                    message="Runtime received request",
                ),
            ),
        )
    )


def _write_a_decision(generated_dir: Path) -> None:
    """A real Décisions CPU stream entry — `record_decision` itself."""
    record_decision(
        boosted={"jellyfin": True},
        report=ApplyReport(applied=("jellyfin",)),
        output_path=generated_dir / "resource-priority-decision.json",
    )


def _write_a_raw_observation(generated_dir: Path) -> None:
    """
    A raw Observation History entry, shaped exactly like
    `DockerObservationArtifactGenerator`'s own output — no `version`/
    `provenance` envelope, since none of the twelve provider
    generators write one.
    """
    content = json.dumps(
        {
            "provider": {"id": "aistack.provider.docker", "name": "Docker Provider"},
            "collected_at": "2026-09-27T10:00:00+00:00",
            "containers": [],
        },
        indent=2,
    )
    write_artifact_with_history(content, generated_dir / "docker-observation.json")


def _write_a_plain_text_explanation(generated_dir: Path) -> None:
    """
    Shaped like `DockerExplanationArtifactGenerator`'s own output —
    not JSON at all.
    """
    write_artifact_with_history(
        "jellyfin: pinned to CPU 0-1.\n",
        generated_dir / "docker-runtime-explanation.txt",
    )


def test_every_stream_produces_at_least_one_generic_entity(tmp_path: Path):
    _write_a_trace(tmp_path)
    _write_a_decision(tmp_path)
    _write_a_raw_observation(tmp_path)
    _write_a_plain_text_explanation(tmp_path)

    store = OxigraphGraphStore()
    summary = project_observation_history(store, generated_dir=tmp_path)

    assert summary.streams_seen == 4
    assert summary.observations_seen == 4

    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    # One observation entity per stream, plus the Traces stream's own
    # `causality`-derived request entity (§ below) — five in total.
    assert len(entities) == 5

    generated_at = list(store.query(f"SELECT ?o WHERE {{ ?s <{PROV_GENERATED_AT_TIME}> ?o }}"))
    assert len(generated_at) == 4


def test_an_envelope_stream_carries_its_real_stable_subject(tmp_path: Path):
    _write_a_decision(tmp_path)

    store = OxigraphGraphStore()
    project_observation_history(store, generated_dir=tmp_path)

    rows = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert rows == [{"o": "resource-priority-decision"}]


def test_an_envelope_stream_is_attributed_to_its_real_origin(tmp_path: Path):
    _write_a_decision(tmp_path)

    store = OxigraphGraphStore()
    project_observation_history(store, generated_dir=tmp_path)

    rows = list(store.query(f"SELECT ?agent WHERE {{ ?s <{PROV_WAS_ATTRIBUTED_TO}> ?agent }}"))
    assert rows == [{"agent": "urn:aistack:agent:aistack.priority.resource_priority_monitor"}]


def test_a_traces_entry_records_its_real_causality_as_prov_used(tmp_path: Path):
    """
    `FileTraceRepository` is the one real producer that sets
    `causality` (`trace.request.request_id`) — mapped to `prov:used`,
    an Activity using the Entity that triggered it, not an invented
    predicate.
    """
    _write_a_trace(tmp_path)

    store = OxigraphGraphStore()
    project_observation_history(store, generated_dir=tmp_path)

    rows = list(store.query(f"SELECT ?request WHERE {{ ?activity <{PROV_USED}> ?request }}"))
    assert rows == [{"request": "urn:aistack:request:request-001"}]


def test_a_raw_observation_carries_no_stable_subject_or_attribution(tmp_path: Path):
    """
    The twelve raw Observation History streams have no `version`/
    `provenance` envelope — nothing here should be invented for them.
    """
    _write_a_raw_observation(tmp_path)

    store = OxigraphGraphStore()
    project_observation_history(store, generated_dir=tmp_path)

    assert list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}")) == []
    assert list(store.query(f"SELECT ?o WHERE {{ ?s <{PROV_WAS_ATTRIBUTED_TO}> ?o }}")) == []


def test_a_plain_text_stream_still_gets_the_generic_baseline(tmp_path: Path):
    """
    Not JSON at all — `_parse_envelope` must fail closed, not raise,
    and the generic entity/generatedAtTime facts still get written.
    """
    _write_a_plain_text_explanation(tmp_path)

    store = OxigraphGraphStore()
    summary = project_observation_history(store, generated_dir=tmp_path)

    assert summary.observations_seen == 1
    assert (
        list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}")) != []
    )


def test_project_observation_history_clears_the_store_first(tmp_path: Path):
    """§ *Decision* 10 — a full rebuild, never additive to what a prior run left."""
    _write_a_decision(tmp_path)

    store = OxigraphGraphStore()
    store.add("https://example/stale", "https://example/p", "https://example/o")

    project_observation_history(store, generated_dir=tmp_path)

    assert (
        list(store.query("SELECT ?s WHERE { <https://example/stale> ?p ?o }")) == []
    )


def test_an_empty_generated_dir_produces_nothing(tmp_path: Path):
    store = OxigraphGraphStore()
    summary = project_observation_history(store, generated_dir=tmp_path)

    assert summary.streams_seen == 0
    assert summary.observations_seen == 0
    assert summary.facts_written == 0

"""
A small, real Time Machine graph for the screen's tests: built by the
same projections `aistack.cli.timemachine_rebuild` runs, from history
files written in the shapes production writes — never hand-typed
triples.

- `priority-decision`: two observations of `booklore_db`, on
  2026-10-01 and 2026-10-02, each carrying the J3 envelope (so a stable
  subject and an agent).
- `docker-observation`: one raw observation, no envelope, so no subject.
- One Explication of `booklore_db`, imported from an AI Reasoning
  `explain` answer.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.explications.from_ai_reasoning import import_explain_answers
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_explications, project_observation_history
from aistack.timemachine.screen import GRAPH_DIR
from aistack.timemachine.tree import NetworkTreeNode

SUBJECT = "booklore_db"
FIRST = "2026-10-01T10-00-00Z"
SECOND = "2026-10-02T10-00-00Z"


def _history(generated: Path, stem: str, stamp: str, content: object) -> None:
    directory = generated / "history" / stem
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stamp}.json").write_text(json.dumps(content), encoding="utf-8")


def _decision(n: int) -> dict[str, object]:
    return {
        "version": {"subject": SUBJECT, "number": n},
        "provenance": {"origin": "aistack.cli.resource_priority_monitor", "causality": None},
        "boosted": {SUBJECT: n == 2},
    }


def build_sample_graph(generated: Path) -> Path:
    _history(generated, "priority-decision", FIRST, _decision(1))
    _history(generated, "priority-decision", SECOND, _decision(2))
    _history(generated, "docker-observation", FIRST, {"containers": []})

    reasoning = generated / "ai-reasoning"
    record_ai_reasoning(
        RuntimeFinding(
            subject=SUBJECT,
            signature="OPS-0001/S-003",
            interpretation="unexplained CPU consumption",
            remediation="declare booklore_db in resource_priority.yml",
            confidence="high",
            grounding="OPS-0003/booklore_db",
            evidence=(
                CitedReading(
                    provider="aistack.provider.docker",
                    reading=ContainerCpuReading(container=SUBJECT, cpu_percent=12.2),
                ),
            ),
        ),
        (
            AIRuntimeAnswer(
                operation="explain",
                subject=SUBJECT,
                model="mistral",
                prompt="explain prompt",
                response="booklore_db runs hot because of its nightly scan.",
                reachable=True,
            ),
        ),
        output_dir=reasoning,
    )
    import_explain_answers(reasoning, generated / "explications")

    (generated / GRAPH_DIR).parent.mkdir(parents=True, exist_ok=True)
    store = OxigraphGraphStore(generated / GRAPH_DIR)
    project_observation_history(store, generated)
    project_explications(store, generated)
    del store
    gc.collect()

    return generated


def sample_tree() -> list[NetworkTreeNode]:
    return [
        NetworkTreeNode("network", "192.168.1.0/24", "network", None, 0, True),
        NetworkTreeNode("host:GIGABYTE", "GIGABYTE", "host", "network", 1, True),
        NetworkTreeNode("stack:booklore", "booklore", "stack", "host:GIGABYTE", 2, True),
        NetworkTreeNode("container:booklore_db", SUBJECT, "container", "stack:booklore", 3, False),
        NetworkTreeNode("container:frigate", "frigate", "container", "host:GIGABYTE", 2, False),
    ]

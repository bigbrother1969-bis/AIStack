"""
AI Reasoning History — `aistack.ai_runtime.reasoning_history`, J7
(`claude/PLAN-TRAJECTOIRE-2026-09-04.md`), scoped with the owner
2026-09-18 against three decisions:

- **One entry per finding**, combining `reason`/`explain`/
  `recommend` together, not three independently-versioned entries.
- **One stream per finding subject**
  (`reports/generated/ai-reasoning/<subject>.json`), not one shared
  stream for every subject.
- **Traced unconditionally**, including when every `AIRuntimeAnswer`
  is `reachable=False` — no cadence gate like `decision_history`'s
  own "only on change".

`serialize_ai_reasoning`/`record_ai_reasoning` are pure and
file-writing, not host-touching (no Ollama, no Docker) — fully
covered here rather than verified live.
"""

from __future__ import annotations

import json
from pathlib import Path

from aistack.ai_runtime.reasoning_history import (
    DEFAULT_OUTPUT_DIR,
    record_ai_reasoning,
    reasoning_history_path,
    serialize_ai_reasoning,
)
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.kernel.time import Provenance, VersionId


_VERSION = VersionId(subject="booklore_db", sequence=1)
_PROVENANCE = Provenance(origin="aistack.cli.ai_reason")


def _finding(**overrides) -> RuntimeFinding:
    defaults = dict(
        subject="booklore_db",
        signature="OPS-0001/S-003",
        interpretation="unexplained CPU consumption correlates with a hot sensor",
        remediation="declare booklore_db in resource_priority.yml",
        confidence="high",
        grounding="OPS-0003/booklore_db",
        evidence=(
            CitedReading(
                provider="aistack.provider.docker",
                reading=ContainerCpuReading(
                    container="booklore_db", cpu_percent=12.2
                ),
            ),
        ),
        qualifications=("OPS-0004/sustainability-anomaly",),
    )
    defaults.update(overrides)
    return RuntimeFinding(**defaults)


def _answer(operation: str, *, reachable: bool = True, **overrides) -> AIRuntimeAnswer:
    defaults = dict(
        operation=operation,
        subject="booklore_db",
        model="qwen2.5:0.5b",
        prompt=f"prompt for {operation}",
        response="a response" if reachable else "",
        reachable=reachable,
        unreachable_reason="" if reachable else "engine unreachable",
    )
    defaults.update(overrides)
    return AIRuntimeAnswer(**defaults)


def _answers(reachable: bool = True) -> tuple[AIRuntimeAnswer, ...]:
    return (
        _answer("reason", reachable=reachable),
        _answer("explain", reachable=reachable),
        _answer("recommend", reachable=reachable),
    )


# --------------------------------------------------------------------
# serialize_ai_reasoning
# --------------------------------------------------------------------


def test_serialize_carries_the_finding_and_every_answer():
    serialized = serialize_ai_reasoning(
        _finding(), _answers(), version=_VERSION, provenance=_PROVENANCE
    )

    assert serialized["finding"]["subject"] == "booklore_db"
    assert serialized["finding"]["signature"] == "OPS-0001/S-003"
    assert serialized["finding"]["qualifications"] == [
        "OPS-0004/sustainability-anomaly"
    ]
    assert [a["operation"] for a in serialized["answers"]] == [
        "reason",
        "explain",
        "recommend",
    ]
    assert all(a["response"] == "a response" for a in serialized["answers"])


def test_serialize_carries_version_and_provenance():
    serialized = serialize_ai_reasoning(
        _finding(), _answers(), version=_VERSION, provenance=_PROVENANCE
    )

    assert serialized["version"] == {"subject": "booklore_db", "sequence": 1}
    assert serialized["provenance"] == {
        "origin": "aistack.cli.ai_reason",
        "causality": None,
    }


def test_serialize_carries_unreachable_answers_unchanged():
    serialized = serialize_ai_reasoning(
        _finding(),
        _answers(reachable=False),
        version=_VERSION,
        provenance=_PROVENANCE,
    )

    assert all(a["reachable"] is False for a in serialized["answers"])
    assert all(a["unreachable_reason"] == "engine unreachable" for a in serialized["answers"])


def test_the_result_is_actually_json_serializable():
    serialized = serialize_ai_reasoning(
        _finding(), _answers(), version=_VERSION, provenance=_PROVENANCE
    )

    json.dumps(serialized)


# --------------------------------------------------------------------
# reasoning_history_path
# --------------------------------------------------------------------


def test_reasoning_history_path_is_scoped_by_subject(tmp_path: Path):
    path = reasoning_history_path("booklore_db", tmp_path)

    assert path == tmp_path / "booklore_db.json"


# --------------------------------------------------------------------
# record_ai_reasoning
# --------------------------------------------------------------------


def test_record_ai_reasoning_writes_to_the_subject_s_own_file(tmp_path: Path):
    written = record_ai_reasoning(_finding(), _answers(), output_dir=tmp_path)

    assert written == tmp_path / "booklore_db.json"
    content = json.loads(written.read_text(encoding="utf-8"))
    assert content["finding"]["subject"] == "booklore_db"


def test_record_ai_reasoning_keeps_two_subjects_independent(tmp_path: Path):
    record_ai_reasoning(_finding(subject="booklore_db"), _answers(), output_dir=tmp_path)
    record_ai_reasoning(
        _finding(subject="frigate"),
        _answers(),
        output_dir=tmp_path,
    )

    booklore = json.loads((tmp_path / "booklore_db.json").read_text(encoding="utf-8"))
    frigate = json.loads((tmp_path / "frigate.json").read_text(encoding="utf-8"))
    assert booklore["version"] == {"subject": "booklore_db", "sequence": 1}
    assert frigate["version"] == {"subject": "frigate", "sequence": 1}


def test_record_ai_reasoning_advances_the_version_sequence_per_subject(
    tmp_path: Path,
):
    record_ai_reasoning(_finding(), _answers(), output_dir=tmp_path)
    record_ai_reasoning(_finding(), _answers(), output_dir=tmp_path)

    content = json.loads((tmp_path / "booklore_db.json").read_text(encoding="utf-8"))
    assert content["version"] == {"subject": "booklore_db", "sequence": 2}


def test_record_ai_reasoning_writes_even_when_every_answer_is_unreachable(
    tmp_path: Path,
):
    written = record_ai_reasoning(
        _finding(), _answers(reachable=False), output_dir=tmp_path
    )

    assert written.exists()
    content = json.loads(written.read_text(encoding="utf-8"))
    assert all(a["reachable"] is False for a in content["answers"])


def test_record_ai_reasoning_keeps_history_like_every_other_historicised_artifact(
    tmp_path: Path,
):
    record_ai_reasoning(_finding(), _answers(), output_dir=tmp_path)
    record_ai_reasoning(_finding(), _answers(), output_dir=tmp_path)

    history_dir = tmp_path / "history" / "booklore_db"
    assert len(list(history_dir.glob("*.json"))) == 2


def test_default_output_dir_is_under_reports_generated():
    assert DEFAULT_OUTPUT_DIR == Path("reports/generated/ai-reasoning")

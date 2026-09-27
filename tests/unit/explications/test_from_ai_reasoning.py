"""
`aistack.explications.from_ai_reasoning` — the first real Explications
importer (`ADR-0011` § 8), against a real AI Reasoning History entry
(`aistack.ai_runtime.reasoning_history.record_ai_reasoning`), not a
hand-typed JSON stand-in — the same discipline
`tests/unit/timemachine/projection/test_project_observation_history.py`
already holds for the other three streams.
"""

from __future__ import annotations

from pathlib import Path

from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.explications import read_explication_history
from aistack.explications.from_ai_reasoning import import_explain_answers


def _finding(**overrides: object) -> RuntimeFinding:
    defaults: dict[str, object] = dict(
        subject="booklore_db",
        signature="OPS-0001/S-003",
        interpretation="unexplained CPU consumption correlates with a hot sensor",
        remediation="declare booklore_db in resource_priority.yml",
        confidence="high",
        grounding="OPS-0003/booklore_db",
        evidence=(
            CitedReading(
                provider="aistack.provider.docker",
                reading=ContainerCpuReading(container="booklore_db", cpu_percent=12.2),
            ),
        ),
    )
    defaults.update(overrides)
    return RuntimeFinding(**defaults)  # type: ignore[arg-type]


def _answers(explain_response: str = "booklore_db runs hot because of X.") -> tuple:
    return (
        AIRuntimeAnswer(
            operation="reason",
            subject="booklore_db",
            model="mistral",
            prompt="reason prompt",
            response="reason response",
            reachable=True,
        ),
        AIRuntimeAnswer(
            operation="explain",
            subject="booklore_db",
            model="mistral",
            prompt="explain prompt",
            response=explain_response,
            reachable=True,
        ),
        AIRuntimeAnswer(
            operation="recommend",
            subject="booklore_db",
            model="mistral",
            prompt="recommend prompt",
            response="recommend response",
            reachable=True,
        ),
    )


def test_import_records_one_explication_per_explain_answer(tmp_path: Path):
    ai_reasoning_dir = tmp_path / "ai-reasoning"
    output_dir = tmp_path / "explications"

    record_ai_reasoning(_finding(), _answers(), output_dir=ai_reasoning_dir)

    summary = import_explain_answers(ai_reasoning_dir, output_dir)

    assert summary.subjects_seen == 1
    assert summary.explain_answers_seen == 1
    assert summary.explications_recorded == 1
    assert summary.explications_already_imported == 0

    history = read_explication_history("booklore_db", output_dir)
    assert len(history) == 1
    artifact = history[0]
    assert artifact.id == "booklore_db"
    assert artifact.confidence == "Proposed"
    assert artifact.source == "model:mistral"
    assert artifact.content == "booklore_db runs hot because of X."
    assert artifact.metadata["source_stream"] == "ai-reasoning"
    assert artifact.metadata["explication_status"] == "Proposed"


def test_import_is_idempotent_against_unchanged_ai_reasoning_history(tmp_path: Path):
    ai_reasoning_dir = tmp_path / "ai-reasoning"
    output_dir = tmp_path / "explications"

    record_ai_reasoning(_finding(), _answers(), output_dir=ai_reasoning_dir)
    import_explain_answers(ai_reasoning_dir, output_dir)

    second = import_explain_answers(ai_reasoning_dir, output_dir)

    assert second.explications_recorded == 0
    assert second.explications_already_imported == 1
    assert len(read_explication_history("booklore_db", output_dir)) == 1


def test_import_records_a_new_explication_for_a_later_instant(tmp_path: Path, monkeypatch):
    """
    A later, real AI Reasoning History entry for the same subject is a
    new event, not a correction of the last — it gets its own new
    Explication version, never collapsed into the first. Two real
    writes a second apart, not two in the same process tick —
    `available_instants` deliberately collapses same-second writes to
    one historical moment (`aistack.history.query`'s own docstring),
    so the clock is controlled here the same way
    `tests/unit/generators/test_history.py
    ::test_two_writes_in_the_same_second_both_survive` controls it to
    test the opposite case.
    """
    from datetime import UTC, datetime

    import aistack.generators.history as history_module

    class FrozenDatetime(history_module.datetime):
        _instant = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls._instant

    monkeypatch.setattr(history_module, "datetime", FrozenDatetime)

    ai_reasoning_dir = tmp_path / "ai-reasoning"
    output_dir = tmp_path / "explications"

    FrozenDatetime._instant = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)
    record_ai_reasoning(_finding(), _answers("first explanation"), output_dir=ai_reasoning_dir)
    import_explain_answers(ai_reasoning_dir, output_dir)

    FrozenDatetime._instant = datetime(2026, 9, 27, 12, 0, 1, tzinfo=UTC)
    record_ai_reasoning(_finding(), _answers("second explanation"), output_dir=ai_reasoning_dir)
    summary = import_explain_answers(ai_reasoning_dir, output_dir)

    assert summary.explications_recorded == 1
    assert summary.explications_already_imported == 1
    history = read_explication_history("booklore_db", output_dir)
    assert len(history) == 2
    assert history[-1].content == "second explanation"


def test_import_skips_subjects_with_no_explain_answer(tmp_path: Path):
    ai_reasoning_dir = tmp_path / "ai-reasoning"
    output_dir = tmp_path / "explications"

    answers_without_explain = tuple(
        answer for answer in _answers() if answer.operation != "explain"
    )
    record_ai_reasoning(_finding(), answers_without_explain, output_dir=ai_reasoning_dir)

    summary = import_explain_answers(ai_reasoning_dir, output_dir)

    assert summary.explain_answers_seen == 0
    assert summary.explications_recorded == 0
    assert read_explication_history("booklore_db", output_dir) == []


def test_import_on_an_empty_ai_reasoning_dir_does_nothing(tmp_path: Path):
    summary = import_explain_answers(tmp_path / "ai-reasoning", tmp_path / "explications")

    assert summary.subjects_seen == 0
    assert summary.explications_recorded == 0

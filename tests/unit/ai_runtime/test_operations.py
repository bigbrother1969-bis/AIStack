from __future__ import annotations

from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding


class FakeEngine:
    """A hand-controlled `AIEngine` — no real model, no network."""

    def __init__(self, text: str = "", reason_: str = ""):
        self.text = text
        self.reason_ = reason_
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> tuple[str, str]:
        self.prompts.append(prompt)
        return self.text, self.reason_


def _finding() -> RuntimeFinding:
    return RuntimeFinding(
        subject="booklore_db",
        signature="OPS-0004",
        interpretation="booklore_db used 12.2% CPU, undeclared.",
        remediation="Classify booklore_db in resource_priority.yml.",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="aistack.provider.docker",
                reading=ContainerCpuReading(
                    container="booklore_db", cpu_percent=12.2
                ),
            ),
        ),
        qualifications=("OPS-0004/energy-inefficiency",),
    )


# --------------------------------------------------------------------
# No model configured — the finding is never sent anywhere.
# --------------------------------------------------------------------


def test_no_model_configured_never_calls_the_engine():
    engine = FakeEngine(text="should never be seen")

    answer = reason(_finding(), engine, None)

    assert answer.reachable is False
    assert "no model is configured" in answer.unreachable_reason
    assert engine.prompts == []


def test_no_model_configured_applies_to_explain_and_recommend_too():
    engine = FakeEngine(text="should never be seen")

    for operation in (explain, recommend):
        answer = operation(_finding(), engine, None)
        assert answer.reachable is False
        assert engine.prompts == []


# --------------------------------------------------------------------
# A configured model, a reachable engine.
# --------------------------------------------------------------------


def test_reason_sends_the_findings_own_fields_in_the_prompt():
    engine = FakeEngine(text="a reasoned sentence")

    answer = reason(_finding(), engine, "llama3.1:8b")

    assert answer.reachable is True
    assert answer.response == "a reasoned sentence"
    assert answer.model == "llama3.1:8b"
    assert "booklore_db" in answer.prompt
    assert "OPS-0004/energy-inefficiency" in answer.prompt
    assert "12.2% CPU" in answer.prompt


def test_explain_and_recommend_use_different_prompts_than_reason():
    engine = FakeEngine(text="an answer")
    finding = _finding()

    reason_answer = reason(finding, engine, "llama3.1:8b")
    explain_answer = explain(finding, engine, "llama3.1:8b")
    recommend_answer = recommend(finding, engine, "llama3.1:8b")

    prompts = {reason_answer.prompt, explain_answer.prompt, recommend_answer.prompt}
    assert len(prompts) == 3


def test_recommend_states_it_is_a_suggestion_not_an_instruction():
    engine = FakeEngine(text="an answer")

    answer = recommend(_finding(), engine, "llama3.1:8b")

    assert "suggestion" in answer.prompt.lower()


def test_an_unreachable_engine_is_reported_without_raising():
    engine = FakeEngine(text="", reason_="Ollama at GIGABYTE:11434 could not be reached")

    answer = reason(_finding(), engine, "llama3.1:8b")

    assert answer.reachable is False
    assert answer.unreachable_reason == (
        "Ollama at GIGABYTE:11434 could not be reached"
    )

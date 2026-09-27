from __future__ import annotations

import pytest

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


# --------------------------------------------------------------------
# `target_language` / `translator` — 2026-09-27, the owner's own fix
# for the AI Runtime answering in English regardless of the display
# language a caller asked for.
# --------------------------------------------------------------------


def test_default_target_language_is_french_and_names_itself_on_the_answer():
    engine = FakeEngine(text="une réponse")

    answer = reason(_finding(), engine, "llama3.1:8b")

    assert answer.language == "fr"
    assert "français" in answer.prompt


def test_english_target_asks_for_no_language_directive_at_all():
    engine = FakeEngine(text="an answer")

    answer = reason(_finding(), engine, "llama3.1:8b", target_language="en")

    assert answer.language == "en"
    assert "français" not in answer.prompt


def test_an_undeclared_target_language_is_refused():
    engine = FakeEngine(text="an answer")

    with pytest.raises(ValueError, match="no language directive declared"):
        reason(_finding(), engine, "llama3.1:8b", target_language="de")


def test_a_configured_translator_translates_a_non_english_target():
    engine = FakeEngine(text="here is the reasoning, in English")
    translator = FakeEngine(text="voici le raisonnement, en français")

    answer = reason(
        _finding(), engine, "llama3.1:8b",
        target_language="fr", translator=translator,
    )

    assert answer.response == "voici le raisonnement, en français"
    assert answer.language == "fr"
    assert "here is the reasoning" in translator.prompts[0]
    assert "French" in translator.prompts[0]


def test_a_configured_translator_is_never_asked_for_an_english_target():
    engine = FakeEngine(text="an answer")
    translator = FakeEngine(text="should never be seen")

    answer = reason(
        _finding(), engine, "llama3.1:8b",
        target_language="en", translator=translator,
    )

    assert answer.response == "an answer"
    assert translator.prompts == []


def test_no_translator_configured_leaves_the_raw_answer_untranslated():
    engine = FakeEngine(text="here is the reasoning, in English")

    answer = reason(
        _finding(), engine, "llama3.1:8b", target_language="fr", translator=None
    )

    assert answer.response == "here is the reasoning, in English"
    assert answer.language == "fr"


def test_a_translator_that_fails_leaves_the_raw_answer_in_place():
    engine = FakeEngine(text="here is the reasoning, in English")
    translator = FakeEngine(text="", reason_="Ollama could not be reached")

    answer = reason(
        _finding(), engine, "llama3.1:8b",
        target_language="fr", translator=translator,
    )

    assert answer.response == "here is the reasoning, in English"
    assert answer.reachable is True


def test_a_translator_is_never_asked_when_the_engine_gave_no_text():
    engine = FakeEngine(text="", reason_="Ollama down")
    translator = FakeEngine(text="should never be seen")

    answer = reason(
        _finding(), engine, "llama3.1:8b",
        target_language="fr", translator=translator,
    )

    assert answer.reachable is False
    assert translator.prompts == []

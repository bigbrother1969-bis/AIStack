"""
The AI half of a guided diagnosis (`ADR-0012` § 4): `reason`, `explain` and
`recommend` over one finding, in the reader's language.

A local model can take minutes per call, so the screen runs the operations
in a background worker and shows each answer as it arrives; the three are
recorded together as one reasoning history entry. Engines are built with
the declared `timeout`, otherwise a slow model would read as unreachable.
"""

from __future__ import annotations

from aistack.config import configured

import os
import re
from collections.abc import Callable, MutableMapping
from pathlib import Path
from dataclasses import replace
from typing import Any

from aistack.ai_runtime.definition import AIRuntimeDefinition, LocalEngineDefinition
from aistack.ai_runtime.engine import AIEngine
from aistack.ai_runtime.openai_chat_engine import OpenAIChatEngine
from aistack.ai_runtime.gemini_engine import GeminiEngine
from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding

AI_RUNTIME = configured(Path(__file__).resolve().parents[1] / "ai_runtime" / "definitions" / "ai_runtime.yml")

OPERATIONS = ("reason", "explain", "recommend")
# Steps 1-3 (the finding, the facts, what to do) come from AIStack at once;
# step 4, the AI's opinion, is asked on the user's click.
STEP_COUNT = 4
AI_STEP = 4

# (finding, operation, target language, facts) -> one answer.
AskAI = Callable[..., AIRuntimeAnswer]
Record = Callable[[RuntimeFinding, tuple[AIRuntimeAnswer, ...]], Any]

_CALLS = {"reason": reason, "explain": explain, "recommend": recommend}


def _gemini(definition: AIRuntimeDefinition) -> GeminiEngine | None:
    """Gemini, when declared and its key is in the environment."""

    declared = definition.gemini
    if declared is None:
        return None
    key = os.environ.get(declared.api_key_env, "")
    if not key:
        return None
    return GeminiEngine(declared.model, key, declared.timeout)


def ai_destination() -> tuple[str, str]:
    """Where the next question goes: ("gemini", model) or ("ollama", model)."""

    definition = load_ai_runtime_yaml(AI_RUNTIME)
    if _gemini(definition) is not None and definition.gemini is not None:
        return "gemini", definition.gemini.model
    engines = definition.local_engines()
    return "ollama", engines[0].model if engines else (definition.model or "")


def ask_ai_runtime(
    finding: RuntimeFinding, operation: str, target_language: str, context: str = ""
) -> AIRuntimeAnswer:
    """
    One answer: from Gemini when declared and its key is set, with the
    collected facts; otherwise, or when Gemini does not answer, from the
    declared Ollama model. An Ollama answer given in Gemini's place says why
    in its `model`.
    """

    definition = load_ai_runtime_yaml(AI_RUNTIME)
    gemini = _gemini(definition)
    first = None
    if gemini is not None:
        first = _CALLS[operation](
            finding, gemini, f"gemini:{gemini.model}", target_language=target_language, context=context
        )
        if first.reachable:
            return first

    answer = ask_local(finding, operation, target_language, context, definition)
    if first is None:
        return answer
    if answer.reachable:
        return replace(answer, model=f"{answer.model} (Gemini: {first.unreachable_reason})")
    return replace(answer, unreachable_reason=f"{first.unreachable_reason} ; {answer.unreachable_reason}")


def ask_ollama(
    finding: RuntimeFinding,
    operation: str,
    target_language: str,
    context: str = "",
    definition: AIRuntimeDefinition | None = None,
) -> AIRuntimeAnswer:
    """
    One answer from the declared Ollama model, within the declared
    `timeout`. When `translator_model` is declared, a non-English answer is
    translated (see `aistack.ai_runtime.operations`).
    """

    definition = definition or load_ai_runtime_yaml(AI_RUNTIME)
    engine = OllamaEngine(
        host=definition.host,
        port=definition.port,
        model=definition.model or "",
        timeout=definition.timeout,
    )
    translator = (
        OllamaEngine(
            host=definition.host,
            port=definition.port,
            model=definition.translator_model,
            timeout=definition.timeout,
        )
        if definition.translator_model
        else None
    )

    return _CALLS[operation](
        finding,
        engine,
        definition.model,
        target_language=target_language,
        translator=translator,
        context=context,
    )


def _engine_of(declared: LocalEngineDefinition) -> AIEngine:
    if declared.kind == "openai_chat":
        return OpenAIChatEngine(
            declared.host, declared.port, declared.model, declared.timeout, declared.reasoning_effort, declared.label
        )
    return OllamaEngine(host=declared.host, port=declared.port, model=declared.model, timeout=declared.timeout)


def ask_one(
    engine: LocalEngineDefinition,
    finding: RuntimeFinding,
    operation: str,
    target_language: str,
    context: str = "",
    translator: AIEngine | None = None,
) -> AIRuntimeAnswer:
    """One answer from one declared engine, with no hand-over to another."""

    return _CALLS[operation](
        finding,
        _engine_of(engine),
        engine.label or engine.model,
        target_language=target_language,
        translator=translator,
        context=context,
    )


def ask_local(
    finding: RuntimeFinding,
    operation: str,
    target_language: str,
    context: str = "",
    definition: AIRuntimeDefinition | None = None,
) -> AIRuntimeAnswer:
    """
    One answer from the local engines, in the order declared: the first that
    answers wins, and an answer given in another's place says so in its
    `model`. The reader asks one question and never picks an engine; every
    answer names the model that gave it. Without `engines:` this is exactly
    `ask_ollama` (the one declared Ollama).
    """

    definition = definition or load_ai_runtime_yaml(AI_RUNTIME)
    declared = definition.local_engines()
    if not declared:
        return ask_ollama(finding, operation, target_language, context, definition)

    translator = (
        OllamaEngine(
            host=definition.host,
            port=definition.port,
            model=definition.translator_model,
            timeout=definition.timeout,
        )
        if definition.translator_model
        else None
    )

    def ask(engine: LocalEngineDefinition) -> AIRuntimeAnswer:
        return ask_one(engine, finding, operation, target_language, context, translator)

    if len(declared) == 1:
        return ask(declared[0])

    failures: list[str] = []
    answer: AIRuntimeAnswer | None = None
    for engine in declared:
        answer = ask(engine)
        if answer.reachable:
            if failures:
                return replace(answer, model=f"{answer.model} ({'; '.join(failures)})")
            return answer
        failures.append(f"{engine.label or engine.model}: {answer.unreachable_reason}")

    assert answer is not None
    return replace(answer, unreachable_reason=" ; ".join(failures))


def run_diagnosis(
    finding: RuntimeFinding,
    target_language: str,
    answers: MutableMapping[str, AIRuntimeAnswer],
    ask: AskAI,
    record: Record,
    on_answer: Callable[[str], Any] = lambda operation: None,
    context: str = "",
) -> None:
    """
    Ask the three operations in order, storing each answer in `answers` as
    it arrives and calling `on_answer`, then record the three together.
    """

    for operation in OPERATIONS:
        answers[operation] = ask(finding, operation, target_language, context) if context else ask(
            finding, operation, target_language
        )
        on_answer(operation)

    record(finding, tuple(answers[operation] for operation in OPERATIONS))


# Engine failure messages mapped to catalog keys, so the screen words them
# in the reader's language. Unrecognised messages are shown as written.
_TIMEOUT = re.compile(r"did not answer within (?P<seconds>[\d.]+) seconds")
_REFUSED = re.compile(r"refused the request with status (?P<status>\d+)")
_UNREACHABLE = re.compile(r"could not be reached: (?P<detail>.*)")


def describe_unreachable(reason_text: str) -> tuple[str, dict[str, str]]:
    """The catalog key and parameters for why the AI engine gave no answer."""

    if match := _TIMEOUT.search(reason_text):
        seconds = float(match["seconds"])
        return "troubleshooting.unreachable.timeout", {"seconds": f"{seconds:g}"}

    if match := _REFUSED.search(reason_text):
        return "troubleshooting.unreachable.refused", {"status": match["status"]}

    if match := _UNREACHABLE.search(reason_text):
        return "troubleshooting.unreachable.unreachable", {"detail": match["detail"]}

    if reason_text.startswith("no model is configured"):
        return "troubleshooting.unreachable.no_model", {}

    return "troubleshooting.unreachable.other", {"detail": reason_text}

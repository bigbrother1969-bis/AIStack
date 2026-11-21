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

from aistack.ai_runtime.definition import AIRuntimeDefinition, GeminiDefinition, HostedDefinition, LocalEngineDefinition
from aistack.ai_runtime.answer_guard import GuardedEngine
from aistack.ai_runtime.choice import Step, plan, route_of
from aistack.ai_runtime.engine import AIEngine
from aistack.ai_runtime.engine_switch import EngineSwitch, SwitchedEngine
from aistack.ai_runtime.openai_chat_engine import OpenAIChatEngine
from aistack.ai_runtime.policy import EXTERNAL, AIPolicy, current_policy
from aistack.ai_runtime.gemini_engine import GeminiEngine
from aistack.ai_runtime.hosted_engines import AnthropicEngine, OpenAIEngine
from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend, system_directive
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


def _gemini_is_set(definition: AIRuntimeDefinition) -> bool:
    """Gemini is declared and its key is in the environment: asked first by a caller that may go outside."""

    declared = definition.gemini
    return declared is not None and bool(os.environ.get(declared.api_key_env, ""))


def _key_of(declared: GeminiDefinition | HostedDefinition | None) -> str:
    return os.environ.get(declared.api_key_env, "") if declared is not None else ""


def _openai(definition: AIRuntimeDefinition) -> OpenAIEngine | None:
    """ChatGPT, when declared and its key is in the environment."""

    declared = definition.openai
    key = _key_of(declared)
    if declared is None or not key:
        return None
    return OpenAIEngine(declared.model, key, declared.timeout)


def _anthropic(definition: AIRuntimeDefinition) -> AnthropicEngine | None:
    """Claude, when declared and its key is in the environment."""

    declared = definition.anthropic
    key = _key_of(declared)
    if declared is None or not key:
        return None
    return AnthropicEngine(declared.model, key, declared.timeout, declared.max_tokens)


# What an answer and a page call each outside engine.
HOSTED_NAMES = {"gemini": "Gemini", "openai": "ChatGPT", "anthropic": "Claude"}


def hosted_names_set(definition: AIRuntimeDefinition) -> list[str]:
    """The outside engines declared whose key is in the environment, in the order they are asked (no engine is built)."""

    declared = (("gemini", definition.gemini), ("openai", definition.openai), ("anthropic", definition.anthropic))
    return [name for name, one in declared if one is not None and _key_of(one)]


def hosted_engines(definition: AIRuntimeDefinition) -> list[tuple[str, Any]]:
    """
    The outside engines that can be asked now, as `(name, engine)`: declared, and their key in the
    environment. `name` is `gemini`, `openai` (ChatGPT) or `anthropic` (Claude), in that order.
    """

    built = (("gemini", _gemini(definition)), ("openai", _openai(definition)), ("anthropic", _anthropic(definition)))
    return [(name, engine) for name, engine in built if engine is not None]


def _plan_for(
    policy: AIPolicy, caller: str, operation: str, definition: AIRuntimeDefinition
) -> tuple[str, tuple[Step, ...], tuple[str, ...]]:
    """The kind of this call and the steps and left-out engines `choice.plan` gives it, from what is declared and set."""

    declared = tuple(
        name for name, one in (("gemini", definition.gemini), ("openai", definition.openai), ("anthropic", definition.anthropic))
        if one is not None
    )
    kind = policy.kind_of(caller, operation)
    steps, passed_over = plan(policy, caller, kind, declared, tuple(hosted_names_set(definition)), definition.local_engines())
    return kind, steps, passed_over


def ai_destination(caller: str = "troubleshooting", policy: AIPolicy | None = None) -> tuple[str, str]:
    """
    Where the next questions of `caller` go: ("gemini" | "openai" | "anthropic", model) or
    ("ollama", model). It follows `ai_policy.yml` as the routing does. The three operations may go to
    different engines; the page must say when the facts leave the house, so the first outside engine
    any of them asks is named, and the local model otherwise.
    """

    policy = policy or current_policy()
    definition = load_ai_runtime_yaml(AI_RUNTIME)
    models = {
        "gemini": definition.gemini.model if definition.gemini else "",
        "openai": definition.openai.model if definition.openai else "",
        "anthropic": definition.anthropic.model if definition.anthropic else "",
    }
    first_local = ""
    for operation in OPERATIONS:
        _, steps, _ = _plan_for(policy, caller, operation, definition)
        for step in steps:
            if step.outside:
                return step.engine, models[step.engine]
        if not first_local and steps and steps[0].local:
            first_local = steps[0].local[0].model
    return "ollama", first_local or (definition.model or "")


def _reachable_by(policy: AIPolicy, caller: str, engines: tuple[LocalEngineDefinition, ...]) -> tuple[LocalEngineDefinition, ...]:
    """The engines a caller may ask: all of them when it may go outside, else the internal ones only."""

    if policy.allows_external(caller):
        return engines
    return tuple(engine for engine in engines if policy.kind_of_host(engine.host) != EXTERNAL)


def ask_managed(
    caller: str,
    finding: RuntimeFinding,
    operation: str,
    target_language: str,
    context: str = "",
    definition: AIRuntimeDefinition | None = None,
) -> AIRuntimeAnswer:
    """
    One answer, by `ai_policy.yml` (`ADR-0029` § 4 and § 10). The policy gives the call a kind, the
    table gives the kind its engines best first, and the class of the caller is a ceiling: an
    `internal_only` caller never reaches an outside engine and never crosses its class to find an
    answer, so when every engine its class allows is silent the answer says so and the hand-written
    text stays. The answer carries what was decided and why in `route`.
    """

    policy = current_policy()
    declared_class = policy.class_of(caller)
    definition = definition or load_ai_runtime_yaml(AI_RUNTIME)
    kind, steps, passed_over = _plan_for(policy, caller, operation, definition)
    declared_local = definition.local_engines()
    silent: list[tuple[str, str]] = []
    went_outside = False
    models = {
        "gemini": definition.gemini.model if definition.gemini else "",
        "openai": definition.openai.model if definition.openai else "",
        "anthropic": definition.anthropic.model if definition.anthropic else "",
    }

    if not steps and declared_local:
        return AIRuntimeAnswer(
            operation=operation,
            subject=finding.subject,
            model="",
            prompt="",
            response="",
            reachable=False,
            unreachable_reason=(
                f"no internal engine is declared for {caller}, which is {declared_class} "
                f"(an engine on a public address or an unlisted host name is outside: see internal_hosts in ai_policy.yml)"
            ),
            language=target_language,
            route=route_of(declared_class, kind, None, (), passed_over),
            kind=kind,
        )

    answer = None
    for step in steps:
        if step.outside:
            engine = dict(hosted_engines(definition))[step.engine]
            answer = _CALLS[operation](
                finding, engine, f"{step.engine}:{models[step.engine]}", target_language=target_language, context=context
            )
            went_outside = True
        else:
            narrowed = replace(definition, engines=step.local) if step.local else definition
            answer = ask_local(finding, operation, target_language, context, narrowed)
        if answer.reachable:
            said = " ; ".join(f"{HOSTED_NAMES.get(name, name)}: {why}" for name, why in silent)
            return replace(
                answer,
                model=f"{answer.model} ({said})" if said else answer.model,
                external=went_outside,
                route=route_of(declared_class, kind, step, tuple(silent), passed_over),
                kind=kind,
            )
        silent.append((step.engine, answer.unreachable_reason))

    reason = " ; ".join(why for _, why in silent)
    last = answer if answer is not None else ask_local(finding, operation, target_language, context, definition)
    return replace(
        last,
        unreachable_reason=reason or last.unreachable_reason,
        external=went_outside,
        route=route_of(declared_class, kind, None, tuple(silent), passed_over),
        kind=kind,
    )


def ask_ai_runtime(
    finding: RuntimeFinding, operation: str, target_language: str, context: str = ""
) -> AIRuntimeAnswer:
    """
    One answer: from an outside engine when one is declared and its key is set (Gemini, then ChatGPT,
    then Claude, the first that answers), with the collected facts; otherwise, or when none answers,
    from the declared local engines. A local answer given in an outside engine's place says why in its
    `model`.
    """

    definition = load_ai_runtime_yaml(AI_RUNTIME)
    refusals: list[tuple[str, str]] = []
    for name, engine in hosted_engines(definition):
        first = _CALLS[operation](
            finding, engine, f"{name}:{engine.model}", target_language=target_language, context=context
        )
        if first.reachable:
            return replace(first, external=True)
        refusals.append((name, first.unreachable_reason))

    answer = ask_local(finding, operation, target_language, context, definition)
    if not refusals:
        return answer
    said = " ; ".join(f"{HOSTED_NAMES[name]}: {reason}" for name, reason in refusals)
    if answer.reachable:
        return replace(answer, model=f"{answer.model} ({said})", external=True)
    return replace(answer, unreachable_reason=f"{said} ; {answer.unreachable_reason}", external=True)


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


def _engine_of(declared: LocalEngineDefinition, target_language: str = "en", guarded: bool = False) -> AIEngine:
    """The engine as declared; `guarded` sets aside an answer that breaks the rules, to hand it on."""

    if declared.kind == "openai_chat":
        engine = OpenAIChatEngine(
            declared.host, declared.port, declared.model, declared.timeout, declared.reasoning_effort, declared.label,
            declared.temperature,
            declared.max_tokens,
            system_directive(target_language),
        )
        return _dressed(engine, declared, target_language, guarded, engine.label)
    plain = OllamaEngine(host=declared.host, port=declared.port, model=declared.model, timeout=declared.timeout)
    return _dressed(plain, declared, target_language, guarded, declared.label or declared.model)


def _dressed(
    engine: AIEngine, declared: LocalEngineDefinition, target_language: str, guarded: bool, label: str
) -> AIEngine:
    """Started on demand when the engine declares a switch, then held to the rules when another can answer."""

    if declared.switch is not None:
        engine = SwitchedEngine(engine, EngineSwitch(declared.switch, label))
    return GuardedEngine(engine, target_language, label) if guarded else engine


def ask_one(
    engine: LocalEngineDefinition,
    finding: RuntimeFinding,
    operation: str,
    target_language: str,
    context: str = "",
    translator: AIEngine | None = None,
    guarded: bool = False,
) -> AIRuntimeAnswer:
    """One answer from one declared engine, with no hand-over to another."""

    return _CALLS[operation](
        finding,
        _engine_of(engine, target_language, guarded),
        engine.label or engine.model,
        target_language=target_language,
        translator=translator,
        context=context,
    )


def _failure(label: str, reason: str) -> str:
    """`<engine>: <reason>`, without saying the engine twice when the reason is a sentence that already starts with its name."""

    own = (f"{label} answer set aside".lower(), f"{label} could not be started".lower())
    return reason if reason.lower().startswith(own) else f"{label}: {reason}"


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
        # An answer that breaks the rules is set aside only when another engine can still answer.
        return ask_one(
            engine, finding, operation, target_language, context, translator, guarded=engine is not declared[-1]
        )

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
        failures.append(_failure(engine.label or engine.model, answer.unreachable_reason))

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

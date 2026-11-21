"""Gemini, ChatGPT and Claude beside each other: which is asked, in which order, and what is said when none answers."""

from __future__ import annotations

import pytest

from aistack.ai_runtime.definition import AIRuntimeDefinition, GeminiDefinition, HostedDefinition
from aistack.ai_runtime.policy import AIPolicy
from aistack.contracts.runtime_finding import MatchedLine, RuntimeFinding
from aistack.contracts.runtime_observation import LogEntry
from aistack.troubleshooting import guide

INTERNAL = AIPolicy({"troubleshooting": "internal_only"})
ALLOWED = AIPolicy({"troubleshooting": "external_allowed"})
KEYS = ("AISTACK_GEMINI_API_KEY", "AISTACK_OPENAI_API_KEY", "AISTACK_ANTHROPIC_API_KEY")


def finding() -> RuntimeFinding:
    return RuntimeFinding(
        subject="host.disk", signature="ADR-0028/other", interpretation="i", remediation="r",
        confidence="watch", grounding="test", evidence=(MatchedLine(LogEntry(offset=0, text="a line")),),
    )


class Engine:
    def __init__(self, model: str, text: str = "", reason: str = "") -> None:
        self.model, self.text, self.reason, self.asked = model, text, reason, 0

    def complete(self, prompt: str) -> tuple[str, str]:
        self.asked += 1
        return self.text, self.reason


@pytest.fixture
def world(monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    definition = AIRuntimeDefinition(
        host="127.0.0.1", port=11434, model="qwen",
        gemini=GeminiDefinition("g-model"),
        openai=HostedDefinition("o-model", "AISTACK_OPENAI_API_KEY"),
        anthropic=HostedDefinition("c-model", "AISTACK_ANTHROPIC_API_KEY"),
    )
    monkeypatch.setattr(guide, "current_policy", lambda: ALLOWED)
    monkeypatch.setattr(guide, "load_ai_runtime_yaml", lambda path: definition)
    engines = {
        "gemini": Engine("g-model", "Vu par Gemini."),
        "openai": Engine("o-model", "Vu par ChatGPT."),
        "anthropic": Engine("c-model", "Vu par Claude."),
    }
    monkeypatch.setattr(guide, "GeminiEngine", lambda model, key, timeout: engines["gemini"])
    monkeypatch.setattr(guide, "OpenAIEngine", lambda model, key, timeout: engines["openai"])
    monkeypatch.setattr(guide, "AnthropicEngine", lambda model, key, timeout, max_tokens: engines["anthropic"])
    monkeypatch.setattr(guide, "OllamaEngine", lambda **kwargs: Engine("qwen", "Vu en local."))
    return engines


def test_only_the_engines_whose_key_is_set_are_asked(monkeypatch, world):
    monkeypatch.setenv("AISTACK_ANTHROPIC_API_KEY", "k")

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr", "- fait")

    assert answer.response == "Vu par Claude." and answer.model.startswith("anthropic:c-model")
    assert answer.external is True and answer.route == "external_allowed"
    assert world["gemini"].asked == 0 and world["openai"].asked == 0


def test_the_next_outside_engine_answers_when_the_first_is_silent(monkeypatch, world):
    monkeypatch.setenv("AISTACK_GEMINI_API_KEY", "k")
    monkeypatch.setenv("AISTACK_OPENAI_API_KEY", "k")
    world["gemini"].text, world["gemini"].reason = "", "Gemini refused the request with status 429"

    answer = guide.ask_ai_runtime(finding(), "reason", "fr", "- fait")

    assert answer.response == "Vu par ChatGPT." and answer.model.startswith("openai:o-model")
    assert world["gemini"].asked == 1 and world["anthropic"].asked == 0


def test_local_answers_when_every_outside_engine_is_silent_and_says_why(monkeypatch, world):
    for env, name in zip(KEYS, ("gemini", "openai", "anthropic"), strict=True):
        monkeypatch.setenv(env, "k")
        world[name].text, world[name].reason = "", f"{name} down"

    answer = guide.ask_ai_runtime(finding(), "reason", "fr", "- fait")

    assert answer.response == "Vu en local." and answer.external is True
    assert "Gemini: " in answer.model and "ChatGPT: " in answer.model and "Claude: " in answer.model


def test_an_internal_caller_reaches_none_of_them_and_the_route_names_them(monkeypatch, world):
    for env in KEYS:
        monkeypatch.setenv(env, "k")
    monkeypatch.setattr(guide, "current_policy", lambda: INTERNAL)

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr", "- fait")

    assert answer.response == "Vu en local." and answer.external is False
    assert answer.route == "internal_only; not asked: gemini, openai, anthropic"
    assert all(engine.asked == 0 for engine in world.values())


def test_the_destination_names_the_first_outside_engine_set(monkeypatch, world):
    monkeypatch.setenv("AISTACK_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AISTACK_ANTHROPIC_API_KEY", "k")

    assert guide.ai_destination("troubleshooting", ALLOWED) == ("openai", "o-model")
    assert guide.ai_destination("troubleshooting", INTERNAL) == ("ollama", "qwen")


def test_a_declared_engine_without_its_key_is_not_asked(world):
    assert guide.hosted_names_set(guide.load_ai_runtime_yaml(None)) == []
    assert guide.hosted_engines(guide.load_ai_runtime_yaml(None)) == []

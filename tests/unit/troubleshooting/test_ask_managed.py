from __future__ import annotations

from dataclasses import replace

import pytest

from aistack.ai_runtime import call_journal
from aistack.ai_runtime.definition import AIRuntimeDefinition, GeminiDefinition, LocalEngineDefinition
from aistack.ai_runtime.policy import AIPolicy
from aistack.contracts.runtime_finding import MatchedLine, RuntimeFinding
from aistack.contracts.runtime_observation import LogEntry
from aistack.troubleshooting import guide

INTERNAL = AIPolicy({"troubleshooting": "internal_only"})
ALLOWED = AIPolicy({"troubleshooting": "external_allowed"})


def finding() -> RuntimeFinding:
    return RuntimeFinding(
        subject="host.disk", signature="ADR-0028/other", interpretation="i", remediation="r",
        confidence="watch", grounding="test", evidence=(MatchedLine(LogEntry(offset=0, text="a line")),),
    )


class Engine:
    def __init__(self, text: str, reason: str = "") -> None:
        self.text, self.reason, self.prompts = text, reason, []
        self.model = "g"

    def complete(self, prompt: str) -> tuple[str, str]:
        self.prompts.append(prompt)
        return self.text, self.reason


def declare(monkeypatch, *, policy: AIPolicy, engines=(), gemini_key=True, ollama=None, gemini=None):
    definition = AIRuntimeDefinition(
        host="127.0.0.1", port=11434, model="qwen", gemini=GeminiDefinition("g"), engines=tuple(engines)
    )
    monkeypatch.setattr(guide, "current_policy", lambda: policy)
    monkeypatch.setattr(guide, "load_ai_runtime_yaml", lambda path: definition)
    if gemini_key:
        monkeypatch.setenv("AISTACK_GEMINI_API_KEY", "k")
    else:
        monkeypatch.delenv("AISTACK_GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        guide, "GeminiEngine",
        (lambda model, key, timeout: gemini) if gemini is not None else (lambda *a: pytest.fail("Gemini asked")),
    )
    monkeypatch.setattr(guide, "OllamaEngine", lambda **kwargs: ollama or Engine("local"))
    return definition


def test_an_internal_caller_never_asks_gemini_even_with_its_key(monkeypatch):
    declare(monkeypatch, policy=INTERNAL, ollama=Engine("Réponse locale."))

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr", "- fait")

    assert answer.reachable and answer.response == "Réponse locale."
    assert answer.external is False
    assert answer.route == "internal_only; not asked: gemini"


def test_a_caller_declared_external_allowed_is_asked_as_before(monkeypatch):
    declare(monkeypatch, policy=ALLOWED, gemini=Engine("Vu par Gemini."), ollama=Engine("never asked"))

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr", "- fait")

    assert answer.response == "Vu par Gemini." and answer.model.startswith("gemini:")
    assert answer.external is True
    assert answer.route == "external_allowed"


def test_an_internal_caller_does_not_cross_its_class_when_the_local_engine_is_silent(monkeypatch):
    declare(monkeypatch, policy=INTERNAL, ollama=Engine("", "Ollama at 127.0.0.1:11434 could not be reached: down"))

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr")

    assert not answer.reachable
    assert "could not be reached" in answer.unreachable_reason
    assert answer.external is False


def test_an_engine_outside_is_kept_out_of_an_internal_call(monkeypatch):
    outside = LocalEngineDefinition("openai_chat", "api.example.com", 443, "big", label="Big")
    inside = LocalEngineDefinition("ollama", "192.168.1.10", 11434, "qwen")
    declare(monkeypatch, policy=INTERNAL, engines=(outside, inside), gemini_key=False, ollama=Engine("Réponse locale."))

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr")

    assert answer.reachable and answer.response == "Réponse locale."
    assert answer.route == "internal_only; not asked: Big"


def test_when_no_internal_engine_is_declared_the_answer_says_so_and_asks_nothing(monkeypatch):
    outside = LocalEngineDefinition("openai_chat", "api.example.com", 443, "big", label="Big")
    declare(monkeypatch, policy=INTERNAL, engines=(outside,), gemini_key=False, ollama=Engine("never asked"))

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr")

    assert not answer.reachable
    assert "no internal engine is declared for troubleshooting" in answer.unreachable_reason
    assert "internal_hosts" in answer.unreachable_reason
    assert answer.route == "internal_only; not asked: Big"


def test_a_host_the_owner_lists_is_inside(monkeypatch):
    named = AIPolicy({"troubleshooting": "internal_only"}, internal_hosts=("msi.lan",))
    engine = LocalEngineDefinition("ollama", "msi.lan", 11434, "qwen")
    declare(monkeypatch, policy=named, engines=(engine,), gemini_key=False, ollama=Engine("Réponse."))

    assert guide.ask_managed("troubleshooting", finding(), "reason", "fr").reachable


def test_no_model_at_all_is_still_said_as_before(monkeypatch):
    definition = AIRuntimeDefinition(host="127.0.0.1", port=1)
    monkeypatch.setattr(guide, "current_policy", lambda: INTERNAL)
    monkeypatch.setattr(guide, "load_ai_runtime_yaml", lambda path: definition)
    monkeypatch.delenv("AISTACK_GEMINI_API_KEY", raising=False)

    answer = guide.ask_managed("troubleshooting", finding(), "reason", "fr")

    assert not answer.reachable and answer.unreachable_reason.startswith("no model is configured")


def test_the_destination_follows_the_policy(monkeypatch):
    declare(monkeypatch, policy=INTERNAL, gemini=Engine("unused"))

    assert guide.ai_destination("troubleshooting", INTERNAL) == ("ollama", "qwen")
    assert guide.ai_destination("troubleshooting", ALLOWED) == ("gemini", "g")
    assert guide.ai_destination("troubleshooting", AIPolicy()) == ("ollama", "qwen")


def test_the_destination_names_an_internal_engine_for_an_internal_caller(monkeypatch):
    outside = LocalEngineDefinition("openai_chat", "api.example.com", 443, "big")
    inside = LocalEngineDefinition("ollama", "192.168.1.10", 11434, "qwen-lan")
    declare(monkeypatch, policy=INTERNAL, engines=(outside, inside))

    assert guide.ai_destination("troubleshooting", INTERNAL) == ("ollama", "qwen-lan")


def test_the_journal_keeps_the_decision(monkeypatch, tmp_path):
    declare(monkeypatch, policy=INTERNAL, ollama=Engine("Réponse locale."))
    asked = call_journal.journaled(
        lambda *a, **k: guide.ask_managed("troubleshooting", *a, **k), "troubleshooting", tmp_path
    )

    asked(finding(), "reason", "fr")

    (line,) = call_journal.read(tmp_path)
    assert line.route == "internal_only; not asked: gemini"
    assert line.reached_external is False and line.policy_differs is False


def test_a_line_without_a_route_still_reads(tmp_path):
    answer = replace(
        __import__("aistack.contracts.ai_runtime_answer", fromlist=["x"]).AIRuntimeAnswer(
            operation="reason", subject="s", model="m", prompt="p", response="r", reachable=True
        ),
        route="",
    )
    call_journal.append(tmp_path, call_journal.call_of("a", answer, 1.0, policy=INTERNAL))

    assert call_journal.read(tmp_path)[0].route == ""

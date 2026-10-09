"""`aistack.troubleshooting.guide` — the declared timeout, the order, the engine's silences."""

from __future__ import annotations

from typing import Any

import pytest

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.i18n import translator_for
from aistack.troubleshooting import guide
from aistack.troubleshooting.guide import OPERATIONS, describe_unreachable, run_diagnosis


def test_the_engines_receive_the_declared_timeout(monkeypatch: pytest.MonkeyPatch):
    built: list[dict[str, Any]] = []

    class Recording(OllamaEngine):
        def __init__(self, **kwargs: Any) -> None:
            built.append(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(guide, "OllamaEngine", Recording)
    monkeypatch.delenv("AISTACK_GEMINI_API_KEY", raising=False)
    monkeypatch.setitem(guide._CALLS, "reason", lambda *args, **kwargs: "answered")

    assert guide.ask_ai_runtime(object(), "reason", "fr") == "answered"  # type: ignore[arg-type]

    declared = guide.load_ai_runtime_yaml(guide.AI_RUNTIME).timeout
    assert built and all(kwargs["timeout"] == declared for kwargs in built)


def test_the_answers_arrive_in_order_and_are_recorded_together():
    answers: dict[str, Any] = {}
    seen: list[tuple[str, dict[str, Any]]] = []
    recorded: list[tuple[Any, ...]] = []

    def ask(finding: Any, operation: str, language: str) -> str:
        seen.append((operation, dict(answers)))
        return f"{operation}:{language}"

    run_diagnosis("finding", "fr", answers, ask, lambda f, done: recorded.append(done))  # type: ignore[arg-type]

    assert [operation for operation, _ in seen] == list(OPERATIONS)
    assert seen[1][1] == {"reason": "reason:fr"}
    assert recorded == [("reason:fr", "explain:fr", "recommend:fr")]


@pytest.mark.parametrize(
    ("reason", "key", "parameters"),
    [
        (
            "Ollama at 127.0.0.1:11434 did not answer within 900.0 seconds",
            "troubleshooting.unreachable.timeout",
            {"seconds": "900"},
        ),
        (
            "Ollama refused the request with status 404 (Not Found): model not found",
            "troubleshooting.unreachable.refused",
            {"status": "404"},
        ),
        (
            "Ollama at 127.0.0.1:11434 could not be reached: [Errno 111] Connection refused",
            "troubleshooting.unreachable.unreachable",
            {"detail": "[Errno 111] Connection refused"},
        ),
        (
            "no model is configured (aistack.ai_runtime.definitions.ai_runtime.yml has no model:)",
            "troubleshooting.unreachable.no_model",
            {},
        ),
        ("something new", "troubleshooting.unreachable.other", {"detail": "something new"}),
    ],
)
def test_each_silence_of_the_engine_has_its_message(reason: str, key: str, parameters: dict[str, str]):
    assert describe_unreachable(reason) == (key, parameters)

    for lang in ("fr", "en"):
        assert translator_for(lang)(key, **parameters)


def _finding() -> Any:
    from datetime import datetime, timezone

    from aistack.contracts.pra_test_reading import PraTestReading
    from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding

    return RuntimeFinding(
        subject="gigabyte", signature="OPS-0004", interpretation="never tested",
        remediation="test it", confidence="Measured", grounding="OPS-0009",
        evidence=(CitedReading(provider="pra", reading=PraTestReading(service="gigabyte", observed_at=datetime.now(timezone.utc))),),
        qualifications=("OPS-0004/technical-debt",),
    )


class Engine:
    def __init__(self, text: str, reason: str = "") -> None:
        self.text, self.reason, self.prompts, self.model = text, reason, [], "m"

    def complete(self, prompt: str) -> tuple[str, str]:
        self.prompts.append(prompt)
        return self.text, self.reason


def test_gemini_answers_first_with_the_facts(monkeypatch: pytest.MonkeyPatch):
    gemini = Engine("Vérifie l'image.")
    ollama = Engine("never asked")
    monkeypatch.setenv("AISTACK_GEMINI_API_KEY", "k")
    monkeypatch.setattr(guide, "GeminiEngine", lambda model, key, timeout: gemini)
    monkeypatch.setattr(guide, "OllamaEngine", lambda **kwargs: ollama)

    answer = guide.ask_ai_runtime(_finding(), "recommend", "fr", "- Dernier test: jamais")

    assert answer.reachable and answer.response == "Vérifie l'image."
    assert answer.model.startswith("gemini:")
    assert "- Dernier test: jamais" in gemini.prompts[0]
    assert ollama.prompts == []
    assert guide.ai_destination()[0] == "gemini"


def test_ollama_answers_when_gemini_does_not_and_says_why(monkeypatch: pytest.MonkeyPatch):
    gemini = Engine("", "Gemini refused the request with status 429")
    ollama = Engine("Réponse locale.")
    monkeypatch.setenv("AISTACK_GEMINI_API_KEY", "k")
    monkeypatch.setattr(guide, "GeminiEngine", lambda model, key, timeout: gemini)
    monkeypatch.setattr(guide, "OllamaEngine", lambda **kwargs: ollama)

    answer = guide.ask_ai_runtime(_finding(), "reason", "fr", "- fait")

    assert answer.response == "Réponse locale."
    assert "429" in answer.model
    assert "- fait" in ollama.prompts[0]


def test_without_a_key_nothing_leaves_the_host(monkeypatch: pytest.MonkeyPatch):
    ollama = Engine("Réponse locale.")
    monkeypatch.delenv("AISTACK_GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(guide, "GeminiEngine", lambda *a: pytest.fail("Gemini asked without a key"))
    monkeypatch.setattr(guide, "OllamaEngine", lambda **kwargs: ollama)

    assert guide.ask_ai_runtime(_finding(), "explain", "fr").response == "Réponse locale."
    assert guide.ai_destination()[0] == "ollama"

from __future__ import annotations

from dataclasses import dataclass

from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class LocalEngineDefinition:
    """
    One local engine, asked in the order declared (`engines:` in `ai_runtime.yml`).

    `kind` is `ollama` (`POST /api/generate`) or `openai_chat` (`POST
    /v1/chat/completions`, the `llama-server` of the Olala fork among others).
    `label` is what an answer says when this engine stands in for another.
    """

    kind: str
    host: str
    port: int
    model: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    reasoning_effort: str | None = None
    label: str = ""


@dataclass(frozen=True)
class AIRuntimeDefinition:
    """
    Where the AI Runtime's engines are reached, loaded from `ai_runtime.yml`.

    `model` and `translator_model` stay `None` until the user names a model
    actually installed (`ollama list`); with no `model`, no question is sent,
    and with no `translator_model`, answers skip the translation pass (see
    `aistack.ai_runtime.operations`). `timeout` matters because small local
    models can take minutes per answer on modest hardware.
    """

    host: str
    port: int
    model: str | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    translator_model: str | None = None
    # Google Gemini, asked first when declared and its API key is in the
    # environment; Ollama answers when it is not.
    gemini: "GeminiDefinition | None" = None
    # Local engines in the order they are asked, the first that answers wins.
    # Empty: the one Ollama above (`host`, `port`, `model`), as before.
    engines: tuple[LocalEngineDefinition, ...] = ()

    def local_engines(self) -> tuple[LocalEngineDefinition, ...]:
        """The local engines to ask, in order; none when no model is named at all."""

        if self.engines:
            return self.engines
        if self.model:
            return (LocalEngineDefinition("ollama", self.host, self.port, self.model, self.timeout),)
        return ()


@dataclass(frozen=True)
class GeminiDefinition:
    model: str
    # The environment variable holding the API key (`.env.web`); the
    # key itself is never written in a declaration.
    api_key_env: str = "AISTACK_GEMINI_API_KEY"
    timeout: float = 60.0

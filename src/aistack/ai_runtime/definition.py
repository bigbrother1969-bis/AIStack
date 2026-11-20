from __future__ import annotations

from dataclasses import dataclass

from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class SwitchDefinition:
    """
    The actuator that starts and stops an engine on demand (`switch:` on an engine).

    `url` is the actuator's address on this host (loopback only), `token_file` the file that holds its
    secret, `start_timeout` how long a call waits for the engine to be ready. The idle delay after which
    the engine is stopped belongs to the actuator, not to this declaration.
    """

    url: str
    token_file: str
    start_timeout: float = 90.0


@dataclass(frozen=True)
class LocalEngineDefinition:
    """
    One local engine, asked in the order declared (`engines:` in `ai_runtime.yml`).

    `kind` is `ollama` (`POST /api/generate`) or `openai_chat` (`POST
    /v1/chat/completions`, the `llama-server` of the Olala fork among others).
    `label` is what an answer says when this engine stands in for another.
    `temperature` (0 to 2, `openai_chat` only) replaces the sampling default of the
    model card, which is lively; a lower one gives steadier, calmer answers.
    `max_tokens` (`openai_chat` only) bounds an answer: without it, an engine with no
    reasoning is bounded by `DEFAULT_MAX_TOKENS`, one that reasons by its timeout only.
    `switch` names the actuator that starts this engine when a question comes and stops it after a
    quiet delay; without it the engine is expected to be running.
    """

    kind: str
    host: str
    port: int
    model: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    reasoning_effort: str | None = None
    label: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    switch: SwitchDefinition | None = None


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

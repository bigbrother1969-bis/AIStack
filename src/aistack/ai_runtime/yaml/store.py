from __future__ import annotations

from pathlib import Path

import yaml

from aistack.ai_runtime.definition import AIRuntimeDefinition, GeminiDefinition, LocalEngineDefinition
from aistack.ai_runtime.openai_chat_engine import REASONING_EFFORTS
from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS

_REQUIRED_FIELDS = ("host", "port")


ENGINE_KINDS = ("ollama", "openai_chat")


def _engines(raw: object, path: Path, default_timeout: float) -> tuple[LocalEngineDefinition, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"AI Runtime definition {path}: engines must be a list")

    found: list[LocalEngineDefinition] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"AI Runtime definition {path}: engine {index} must be a mapping")
        missing = [field for field in ("host", "port", "model") if not item.get(field)]
        if missing:
            raise ValueError(f"AI Runtime definition {path}: engine {index} is missing: {', '.join(missing)}")
        kind = str(item.get("kind") or "ollama")
        if kind not in ENGINE_KINDS:
            raise ValueError(f"AI Runtime definition {path}: engine {index} has an unknown kind {kind!r} (one of {', '.join(ENGINE_KINDS)})")
        effort = item.get("reasoning_effort")
        if effort is not None and str(effort) not in REASONING_EFFORTS:
            raise ValueError(f"AI Runtime definition {path}: engine {index} has an unknown reasoning_effort {effort!r} (one of {', '.join(REASONING_EFFORTS)})")
        temperature = item.get("temperature")
        if temperature is not None:
            if kind != "openai_chat":
                raise ValueError(f"AI Runtime definition {path}: engine {index}: temperature is only for the openai_chat kind")
            if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
                raise ValueError(f"AI Runtime definition {path}: engine {index} has a temperature {temperature!r} that is not a number from 0 to 2")
        found.append(
            LocalEngineDefinition(
                kind=kind,
                host=str(item["host"]),
                port=int(item["port"]),
                model=str(item["model"]),
                timeout=float(item.get("timeout") or default_timeout),
                reasoning_effort=str(effort) if effort is not None else None,
                label=str(item.get("label") or ""),
                temperature=float(temperature) if temperature is not None else None,
            )
        )
    return tuple(found)


def load_ai_runtime_yaml(path: Path) -> AIRuntimeDefinition:
    """
    Load the AI Runtime definition from YAML.

    `host` and `port` are required; a missing key raises a `ValueError`
    naming it. `model`, `translator_model` and `timeout` are optional:
    an absent model means "not configured", never a guessed name. A
    `gemini:` block must name a `model`.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(
            f"AI Runtime definition must contain a mapping: {path}"
        )

    missing = [field for field in _REQUIRED_FIELDS if field not in data]

    if missing:
        raise ValueError(
            f"AI Runtime definition {path} is missing: "
            f"{', '.join(missing)}"
        )

    model = data.get("model")
    timeout = data.get("timeout")
    translator_model = data.get("translator_model")

    gemini = None
    raw = data.get("gemini")
    if raw is not None:
        if not isinstance(raw, dict) or not raw.get("model"):
            raise ValueError(f"AI Runtime definition {path}: gemini names no model")
        gemini = GeminiDefinition(
            model=str(raw["model"]),
            api_key_env=str(raw.get("api_key_env") or "AISTACK_GEMINI_API_KEY"),
            timeout=float(raw.get("timeout") or 60),
        )

    engines = _engines(data.get("engines"), path, float(timeout) if timeout is not None else DEFAULT_TIMEOUT_SECONDS)

    if timeout is None:
        return AIRuntimeDefinition(
            host=str(data["host"]),
            port=int(data["port"]),
            model=str(model) if model else None,
            translator_model=str(translator_model) if translator_model else None,
            gemini=gemini,
            engines=engines,
        )

    return AIRuntimeDefinition(
        host=str(data["host"]),
        port=int(data["port"]),
        model=str(model) if model else None,
        timeout=float(timeout),
        translator_model=str(translator_model) if translator_model else None,
        gemini=gemini,
        engines=engines,
    )

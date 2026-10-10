from __future__ import annotations

from pathlib import Path

import yaml

from aistack.ai_runtime.definition import AIRuntimeDefinition, GeminiDefinition

_REQUIRED_FIELDS = ("host", "port")


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

    if timeout is None:
        return AIRuntimeDefinition(
            host=str(data["host"]),
            port=int(data["port"]),
            model=str(model) if model else None,
            translator_model=str(translator_model) if translator_model else None,
            gemini=gemini,
        )

    return AIRuntimeDefinition(
        host=str(data["host"]),
        port=int(data["port"]),
        model=str(model) if model else None,
        timeout=float(timeout),
        translator_model=str(translator_model) if translator_model else None,
        gemini=gemini,
    )

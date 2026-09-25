from __future__ import annotations

from pathlib import Path

import yaml

from aistack.ai_runtime.definition import AIRuntimeDefinition

_REQUIRED_FIELDS = ("host", "port")


def load_ai_runtime_yaml(path: Path) -> AIRuntimeDefinition:
    """
    Load the governed AI Runtime definition from YAML.

    **Written by hand, not generated** — same reasoning as
    `load_resource_priority_yaml`: this file is typed by the owner,
    so a missing key here is a typo, and the error names which one
    and where.

    **`model` is optional and defaults to `None`, never to a guessed
    string.** A file that has not yet had its `model:` line filled in
    (or spells it `model: null`/omits it) loads exactly as "no model
    configured" — `aistack.ai_runtime.definition.AIRuntimeDefinition`'s
    own docstring explains why that is a real state, not a gap this
    loader papers over.

    **`timeout` is optional and defaults to
    `AIRuntimeDefinition.timeout`'s own default** (`OllamaEngine`'s
    120s) when absent — a file written before 2026-09-25 has no
    `timeout:` line at all, and that means "use the ordinary default,"
    the same backward-compatible reading `model`'s own absence already
    gets, not an error.
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

    if timeout is None:
        return AIRuntimeDefinition(
            host=str(data["host"]),
            port=int(data["port"]),
            model=str(model) if model else None,
        )

    return AIRuntimeDefinition(
        host=str(data["host"]),
        port=int(data["port"]),
        model=str(model) if model else None,
        timeout=float(timeout),
    )

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.ai_runtime.definition import AIRuntimeDefinition
from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.cli.ai_reason import DEFAULT_AI_RUNTIME


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "ai_runtime.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_host_and_port(tmp_path: Path):
    path = write(tmp_path, "host: GIGABYTE\nport: 11434\n")

    definition = load_ai_runtime_yaml(path)

    assert definition == AIRuntimeDefinition(
        host="GIGABYTE", port=11434, model=None
    )
    assert definition.timeout == DEFAULT_TIMEOUT_SECONDS


def test_a_declared_model_loads(tmp_path: Path):
    path = write(tmp_path, "host: GIGABYTE\nport: 11434\nmodel: llama3.1:8b\n")

    definition = load_ai_runtime_yaml(path)

    assert definition.model == "llama3.1:8b"


def test_model_null_loads_as_none(tmp_path: Path):
    path = write(tmp_path, "host: GIGABYTE\nport: 11434\nmodel: null\n")

    definition = load_ai_runtime_yaml(path)

    assert definition.model is None


def test_a_declared_timeout_loads(tmp_path: Path):
    path = write(
        tmp_path,
        "host: GIGABYTE\nport: 11434\nmodel: deepseek-r1:1.5b\ntimeout: 900\n",
    )

    definition = load_ai_runtime_yaml(path)

    assert definition.timeout == 900.0


def test_timeout_absent_defaults_to_the_engines_own_default(tmp_path: Path):
    path = write(tmp_path, "host: GIGABYTE\nport: 11434\nmodel: llama3.1:8b\n")

    definition = load_ai_runtime_yaml(path)

    assert definition.timeout == DEFAULT_TIMEOUT_SECONDS


def test_a_missing_field_names_it(tmp_path: Path):
    path = write(tmp_path, "host: GIGABYTE\n")

    with pytest.raises(ValueError, match="port"):
        load_ai_runtime_yaml(path)


def test_not_a_mapping_is_rejected(tmp_path: Path):
    path = write(tmp_path, "- GIGABYTE\n")

    with pytest.raises(ValueError, match="mapping"):
        load_ai_runtime_yaml(path)


# --------------------------------------------------------------------
# The real, declared file — GOV-P-001: a governed definition is
# exercised against what is actually on disk, not only against a
# fixture built for the test.
# --------------------------------------------------------------------


def test_the_real_ai_runtime_definition_loads():
    definition = load_ai_runtime_yaml(DEFAULT_AI_RUNTIME)

    # 127.0.0.1, not the hostname "GIGABYTE" — corrected 2026-09-18
    # against a real defect found scoping J8: `GIGABYTE` resolves
    # only to IPv6 addresses Ollama's own systemd service never
    # binds to (`ss -tlnp` showed `127.0.0.1:11434` only).
    assert definition.host == "127.0.0.1"
    assert definition.port == 11434

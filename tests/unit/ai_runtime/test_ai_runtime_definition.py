from __future__ import annotations

from pathlib import Path

import pytest

from aistack.ai_runtime.definition import AIRuntimeDefinition
from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.tasks.ai_reason import DEFAULT_AI_RUNTIME


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


def test_translator_model_absent_loads_as_none(tmp_path: Path):
    path = write(tmp_path, "host: GIGABYTE\nport: 11434\nmodel: llama3.1:8b\n")

    definition = load_ai_runtime_yaml(path)

    assert definition.translator_model is None


def test_a_declared_translator_model_loads(tmp_path: Path):
    path = write(
        tmp_path,
        "host: GIGABYTE\nport: 11434\nmodel: deepseek-r1:1.5b\n"
        "translator_model: qwen2.5:0.5b\n",
    )

    definition = load_ai_runtime_yaml(path)

    assert definition.translator_model == "qwen2.5:0.5b"


def test_translator_model_null_loads_as_none(tmp_path: Path):
    path = write(
        tmp_path,
        "host: GIGABYTE\nport: 11434\ntranslator_model: null\n",
    )

    definition = load_ai_runtime_yaml(path)

    assert definition.translator_model is None


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


def test_the_real_ai_runtime_definition_asks_qwen_in_french_without_a_translator():
    # 2026-10-09, UAT of 2.0: the owner chose `qwen2.5:3b`, which
    # writes French itself, over `deepseek-r1:1.5b` translated by
    # `qwen2.5:0.5b` (broken French, 25 to 34 minutes). This test only
    # locks in what the file declares; `ollama list` on the host says
    # whether the model is pulled there.
    definition = load_ai_runtime_yaml(DEFAULT_AI_RUNTIME)

    assert definition.model == "qwen2.5:3b"
    assert definition.translator_model is None


def test_engines_load_in_order_with_their_defaults(tmp_path: Path):
    path = write(
        tmp_path,
        "host: h\nport: 11434\nmodel: qwen\ntimeout: 300\nengines:\n"
        "  - {kind: openai_chat, host: 127.0.0.1, port: 8080, model: olala-mini, reasoning_effort: low, label: Olala}\n"
        "  - {host: h, port: 11434, model: qwen, timeout: 60}\n",
    )

    first, second = load_ai_runtime_yaml(path).engines

    assert (first.kind, first.port, first.model, first.reasoning_effort, first.label, first.timeout) == ("openai_chat", 8080, "olala-mini", "low", "Olala", 300.0)
    assert (second.kind, second.reasoning_effort, second.timeout) == ("ollama", None, 60.0)


def test_without_engines_the_one_declared_ollama_is_the_local_engine(tmp_path: Path):
    definition = load_ai_runtime_yaml(write(tmp_path, "host: h\nport: 11434\nmodel: qwen\n"))

    assert definition.engines == ()
    assert [(e.kind, e.host, e.model) for e in definition.local_engines()] == [("ollama", "h", "qwen")]
    assert load_ai_runtime_yaml(write(tmp_path, "host: h\nport: 1\n")).local_engines() == ()


@pytest.mark.parametrize(
    "engines, message",
    [
        ("engines: nope\n", "must be a list"),
        ("engines:\n  - nope\n", "must be a mapping"),
        ("engines:\n  - {host: h, port: 1}\n", "missing: model"),
        ("engines:\n  - {kind: grpc, host: h, port: 1, model: m}\n", "unknown kind"),
        ("engines:\n  - {host: h, port: 1, model: m, reasoning_effort: extreme}\n", "unknown reasoning_effort"),
        ("engines:\n  - {kind: openai_chat, host: h, port: 1, model: m, temperature: 3}\n", "not a number from 0 to 2"),
        ("engines:\n  - {kind: openai_chat, host: h, port: 1, model: m, temperature: hot}\n", "not a number from 0 to 2"),
        ("engines:\n  - {kind: ollama, host: h, port: 1, model: m, temperature: 0.3}\n", "only for the openai_chat kind"),
    ],
)
def test_a_wrong_engine_is_refused_by_name(tmp_path: Path, engines: str, message: str):
    with pytest.raises(ValueError, match=message):
        load_ai_runtime_yaml(write(tmp_path, "host: h\nport: 1\n" + engines))


def test_a_declared_temperature_loads_and_is_optional(tmp_path: Path):
    definition = load_ai_runtime_yaml(
        write(
            tmp_path,
            "host: h\nport: 1\nengines:\n"
            "  - {kind: openai_chat, host: h, port: 2, model: m, temperature: 0.3}\n"
            "  - {kind: openai_chat, host: h, port: 3, model: m, temperature: 0}\n"
            "  - {kind: openai_chat, host: h, port: 4, model: m}\n",
        )
    )

    assert [engine.temperature for engine in definition.local_engines()] == [0.3, 0.0, None]

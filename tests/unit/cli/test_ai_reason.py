from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.cli import ai_reason as cli
from aistack.cli import runtime_diagnose
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.temperature_reading import TemperatureReading


class FakeDockerProvider:
    def __init__(self, readings):
        self._readings = readings

    def collect_cpu_readings(self):
        return tuple(self._readings)


class FakeHostProvider:
    def __init__(self, temperatures=()):
        self._temperatures = temperatures

    def collect_temperatures(self):
        return tuple(self._temperatures)


RESOURCE_PRIORITY_YAML = """\
priority: []
background:
  default_throttled_cpus: 0.1
  containers: []
unlimited_cpus: 4.0
"""


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------
# qualified_findings — the collection this command owns
# --------------------------------------------------------------------


def test_no_resource_priority_definition_reports_a_note(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", tmp_path / "absent.yml")

    findings, note = cli.qualified_findings()

    assert findings == ()
    assert "no resource-priority definition" in note


def test_unexplained_consumption_and_a_hot_sensor_produce_a_finding(
    monkeypatch, tmp_path
):
    path = tmp_path / "resource_priority.yml"
    path.write_text(RESOURCE_PRIORITY_YAML, encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", path)
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(
            [ContainerCpuReading(container="booklore_db", cpu_percent=12.2)]
        ),
    )
    monkeypatch.setattr(
        cli,
        "HostProvider",
        lambda: FakeHostProvider(
            [
                TemperatureReading(
                    sensor="k10temp",
                    celsius=70.5,
                    high_celsius=70.0,
                    critical_celsius=90.0,
                )
            ]
        ),
    )

    findings, note = cli.qualified_findings()

    assert note == ""
    assert len(findings) == 1
    assert findings[0].subject == "booklore_db"
    assert "OPS-0004/sustainability-anomaly" in findings[0].qualifications


# --------------------------------------------------------------------
# main() — end to end, no model configured
# --------------------------------------------------------------------


def test_main_reports_no_model_configured(workspace, monkeypatch, capsys):
    ai_runtime_path = workspace / "ai_runtime.yml"
    ai_runtime_path.write_text(
        "host: GIGABYTE\nport: 11434\nmodel: null\n", encoding="utf-8"
    )
    monkeypatch.setattr(cli, "DEFAULT_AI_RUNTIME", ai_runtime_path)

    resource_priority_path = workspace / "resource_priority.yml"
    resource_priority_path.write_text(RESOURCE_PRIORITY_YAML, encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", resource_priority_path)

    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(
            [ContainerCpuReading(container="booklore_db", cpu_percent=12.2)]
        ),
    )
    monkeypatch.setattr(cli, "HostProvider", lambda: FakeHostProvider())

    cli.main()

    captured = capsys.readouterr()
    assert "no model is configured" in captured.out


def test_main_reports_nothing_to_reason_about(workspace, monkeypatch, capsys):
    ai_runtime_path = workspace / "ai_runtime.yml"
    ai_runtime_path.write_text(
        "host: GIGABYTE\nport: 11434\nmodel: llama3.1:8b\n", encoding="utf-8"
    )
    monkeypatch.setattr(cli, "DEFAULT_AI_RUNTIME", ai_runtime_path)
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", workspace / "absent.yml")

    cli.main()

    captured = capsys.readouterr()
    assert "No qualified finding to reason about right now." in captured.out


def test_main_reports_the_engine_unreachable_when_a_model_is_configured(
    workspace, monkeypatch, capsys
):
    ai_runtime_path = workspace / "ai_runtime.yml"
    ai_runtime_path.write_text(
        # Port 1 is reserved; nothing listens there — a real,
        # unreachable target, the same discipline
        # `test_ollama_engine.py`'s own unreachable-host test holds.
        "host: 127.0.0.1\nport: 1\nmodel: llama3.1:8b\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_AI_RUNTIME", ai_runtime_path)

    resource_priority_path = workspace / "resource_priority.yml"
    resource_priority_path.write_text(RESOURCE_PRIORITY_YAML, encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", resource_priority_path)

    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(
            [ContainerCpuReading(container="booklore_db", cpu_percent=12.2)]
        ),
    )
    monkeypatch.setattr(cli, "HostProvider", lambda: FakeHostProvider())

    cli.main()

    captured = capsys.readouterr()
    assert "booklore_db" in captured.out
    assert "not answered" in captured.out

    # J7, AI Reasoning History — traced even though every answer was
    # unreachable (`aistack.ai_runtime.reasoning_history`'s own
    # scoping decision, 2026-09-18).
    history_path = workspace / "reports" / "generated" / "ai-reasoning" / "booklore_db.json"
    assert history_path.exists()
    content = json.loads(history_path.read_text(encoding="utf-8"))
    assert content["finding"]["subject"] == "booklore_db"
    assert all(not a["reachable"] for a in content["answers"])


def test_main_builds_the_engine_with_the_declared_timeout(
    workspace, monkeypatch, capsys
):
    ai_runtime_path = workspace / "ai_runtime.yml"
    ai_runtime_path.write_text(
        "host: 127.0.0.1\nport: 1\nmodel: deepseek-r1:1.5b\ntimeout: 900\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_AI_RUNTIME", ai_runtime_path)

    resource_priority_path = workspace / "resource_priority.yml"
    resource_priority_path.write_text(RESOURCE_PRIORITY_YAML, encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", resource_priority_path)

    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(
            [ContainerCpuReading(container="booklore_db", cpu_percent=12.2)]
        ),
    )
    monkeypatch.setattr(cli, "HostProvider", lambda: FakeHostProvider())

    captured_kwargs = {}

    class RecordingOllamaEngine:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def complete(self, prompt):
            return "", "not actually called in this test"

    monkeypatch.setattr(cli, "OllamaEngine", RecordingOllamaEngine)

    cli.main()

    assert captured_kwargs["timeout"] == 900.0
    assert captured_kwargs["model"] == "deepseek-r1:1.5b"


def test_main_does_not_record_reasoning_history_when_nothing_was_asked(
    workspace, monkeypatch, capsys
):
    ai_runtime_path = workspace / "ai_runtime.yml"
    ai_runtime_path.write_text(
        "host: GIGABYTE\nport: 11434\nmodel: null\n", encoding="utf-8"
    )
    monkeypatch.setattr(cli, "DEFAULT_AI_RUNTIME", ai_runtime_path)
    monkeypatch.setattr(cli, "DEFAULT_RESOURCE_PRIORITY", workspace / "absent.yml")

    cli.main()

    # No qualified finding at all this run — nothing to have traced.
    assert not (workspace / "reports" / "generated" / "ai-reasoning").exists()


# --------------------------------------------------------------------
# Drift guard — this module's duplicated constant must match
# runtime_diagnose's own, the same way console_render.py's own
# duplicated threshold paths are already checked against
# health_render's.
# --------------------------------------------------------------------


def test_the_default_resource_priority_path_matches_runtime_diagnoses():
    assert (
        cli.DEFAULT_RESOURCE_PRIORITY
        == runtime_diagnose.DEFAULT_RESOURCE_PRIORITY
    )
    assert cli.DEFAULT_RESOURCE_PRIORITY.exists()

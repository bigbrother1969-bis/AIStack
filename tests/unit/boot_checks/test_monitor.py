"""Reading Uptime Kuma's metrics with an API key (ADR-0032, B4b): no key in a message, no address, names and statuses only."""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from aistack.boot_checks import monitor
from aistack.boot_checks.monitor import MonitorReading, parse_metrics, read_monitors
from aistack.cli import boot_check
from aistack.tasks import boot_check as task

METRICS = (
    "# HELP monitor_status Monitor Status (1 = UP, 0 = DOWN, 2 = PENDING, 3 = MAINTENANCE)\n"
    "# TYPE monitor_status gauge\n"
    'monitor_status{monitor_name="Plex",monitor_type="http",monitor_url="https://example.org",monitor_hostname="null",monitor_port="null"} 1\n'
    'monitor_status{monitor_name="He said \\"hi\\"",monitor_type="ping"} 0\n'
    'monitor_response_time{monitor_name="Plex",monitor_type="http"} 12\n'
    'monitor_status{monitor_type="http"} 1\n'
)


class _Answer(io.BytesIO):
    def __enter__(self) -> "_Answer":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_only_the_status_lines_with_a_name_are_read_and_an_escaped_quote_is_kept() -> None:
    assert parse_metrics(METRICS) == {"Plex": 1, 'He said "hi"': 0}
    assert parse_metrics("") == {}


def test_the_key_is_the_password_of_a_basic_request_on_metrics_and_nothing_else_leaves(monkeypatch) -> None:
    seen: list[urllib.request.Request] = []

    def fake(request, timeout):  # type: ignore[no-untyped-def]
        seen.append(request)

        return _Answer(METRICS.encode())

    monkeypatch.setattr(monitor.urllib.request, "urlopen", fake)
    reading = read_monitors("http://kuma.example:3001/", "uk2_secret")

    assert reading == MonitorReading(True, "", {"Plex": 1, 'He said "hi"': 0})
    assert seen[0].full_url == "http://kuma.example:3001/metrics"
    assert seen[0].get_header("Authorization") == "Basic OnVrMl9zZWNyZXQ="  # ":uk2_secret"


def test_a_refused_key_a_silent_server_and_an_empty_answer_are_states_with_a_reason_not_a_secret(monkeypatch) -> None:
    def refuse(request, timeout):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(request.full_url, 401, "no", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(monitor.urllib.request, "urlopen", refuse)

    assert read_monitors("http://kuma.example", "uk2_secret") == MonitorReading(False, "the API key was refused")

    def silent(request, timeout):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError("connection refused to http://kuma.example uk2_secret")

    monkeypatch.setattr(monitor.urllib.request, "urlopen", silent)
    reading = read_monitors("http://kuma.example", "uk2_secret")

    assert not reading.reachable and "kuma.example" not in reading.reason and "uk2_secret" not in reading.reason

    monkeypatch.setattr(monitor.urllib.request, "urlopen", lambda request, timeout: _Answer(b"nothing"))

    assert not read_monitors("http://kuma.example", "k").reachable


def _facts(directory: Path) -> None:
    from tests.unit.boot_checks.test_controls import _facts_file

    _facts_file(directory, datetime.now(timezone.utc))


def test_the_command_reads_kuma_only_when_the_address_and_the_key_are_set(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("AISTACK_KUMA_URL", raising=False)
    monkeypatch.delenv("AISTACK_KUMA_API_KEY", raising=False)
    monkeypatch.setattr(task, "read_monitors", lambda url, key: MonitorReading(True, "", {"Plex": 0}))
    _facts(tmp_path / "facts")
    arguments = ["--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--no-cockpit"]

    assert boot_check.main(arguments) == 0
    assert "not connected" in capsys.readouterr().out

    monkeypatch.setenv("AISTACK_KUMA_URL", "http://kuma.example:3001")
    monkeypatch.setenv("AISTACK_KUMA_API_KEY", "uk2_secret")

    assert boot_check.main(arguments) == 1
    printed = capsys.readouterr().out

    assert "monitor" in printed and "1 down" in printed and "Plex" in printed
    assert "uk2_secret" not in printed and "kuma.example" not in printed


def test_a_key_entered_in_settings_wins_over_the_environment_and_the_suggestion_lists_the_monitors(tmp_path: Path, capsys, monkeypatch) -> None:
    from aistack.api_keys import write_value

    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(task, "read_monitors", lambda url, key: seen.append((url, key)) or MonitorReading(True, "", {"Plex": 1, "Gitea": 1}))
    monkeypatch.setenv("AISTACK_KUMA_URL", "http://from-env")
    monkeypatch.setenv("AISTACK_KUMA_API_KEY", "from-env")
    write_value(tmp_path / "out", "AISTACK_KUMA_URL", "http://from-settings")
    write_value(tmp_path / "out", "AISTACK_KUMA_API_KEY", "from-settings")
    _facts(tmp_path / "facts")

    assert boot_check.main(["--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--suggest"]) == 0
    assert seen == [("http://from-settings", "from-settings")]
    assert "expected_monitors: [Gitea, Plex]" in capsys.readouterr().out

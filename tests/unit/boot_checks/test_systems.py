"""What Beszel says of the machines, and how the start-up checks judge it (ADR-0032, slice O1c)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.boot_checks.controls import CRITICAL, OK, SKIPPED, UNKNOWN, WARNING, Reading, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.phrases import say
from aistack.boot_checks.systems import SystemsReading, read_systems
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import DEFINITION, LATER, facts


def machine(name: str = "msi", status: str = "up", disk: float | None = 40.0, memory: float | None = 30.0, temp: float | None = 55.0) -> BeszelSystemReading:
    return BeszelSystemReading(name=name, host="h", status=status, disk_pct=disk, mem_pct=memory, temp_c=temp)


def judged(reading: SystemsReading | None, definition: BootChecksDefinition = DEFINITION) -> Result:
    results = evaluate(facts(), definition, LATER, Reading(True, 0), Reading(True, 0), None, None, reading)

    return {result.control: result for result in results}["systems"]


def test_without_an_account_the_control_is_skipped_and_says_so() -> None:
    result = judged(None)

    assert result.status == SKIPPED and "Beszel is not connected" in result.summary


def test_a_beszel_that_does_not_answer_or_reports_nothing_is_unknown_never_healthy() -> None:
    assert judged(SystemsReading(False, "Beszel did not answer")).status == UNKNOWN
    assert judged(SystemsReading(True, "", ())).status == UNKNOWN
    assert judged(SystemsReading(True, "", (machine(status="paused"), machine("pi", status="pending")))).status == UNKNOWN


def test_machines_in_service_under_their_limits_pass() -> None:
    result = judged(SystemsReading(True, "", (machine(), machine("raspberry", temp=61.8))))

    assert result.status == OK and result.summary == "2 system(s) read, none down, none under pressure"


def test_a_machine_beszel_calls_down_is_to_watch_by_name() -> None:
    result = judged(SystemsReading(True, "", (machine(), machine("raspberry", status="down"))))

    assert result.status == WARNING and result.finding == "system_down"
    assert result.summary == "2 system(s) read; 1 system(s) down" and result.details == ("raspberry",)


def test_a_disk_a_memory_or_a_temperature_at_its_limit_is_to_watch_and_just_under_is_not() -> None:
    assert judged(SystemsReading(True, "", (machine(disk=89.9, memory=89.9, temp=79.9),))).status == OK

    disk = judged(SystemsReading(True, "", (machine(disk=90.0),)))
    memory = judged(SystemsReading(True, "", (machine(memory=95.0),)))
    hot = judged(SystemsReading(True, "", (machine("raspberry", temp=80.0), machine())))

    assert (disk.status, disk.finding, disk.summary) == (WARNING, "system_pressure", "1 system(s) read; 1 with disk use at or above 90 %")
    assert "1 with memory use at or above 90 %" in memory.summary
    assert hot.summary == "2 system(s) read; 1 at or above 80 °C" and hot.details == ("raspberry",)


def test_the_limits_are_the_owner_s_and_a_missing_value_is_not_judged() -> None:
    strict = BootChecksDefinition(system_disk_percent=30, system_memory_percent=20, system_temperature_celsius=50)
    result = judged(SystemsReading(True, "", (machine(),)), strict)

    assert result.status == WARNING and "disk use at or above 30 %" in result.summary and "memory use at or above 20 %" in result.summary
    assert judged(SystemsReading(True, "", (machine(disk=None, temp=None),))).status == OK
    assert judged(SystemsReading(True, "", (machine(disk=None, memory=None, temp=None),))).status == UNKNOWN


def test_a_down_machine_is_not_hidden_by_the_pressure_of_another_and_the_weight_is_the_owner_s() -> None:
    reading = SystemsReading(True, "", (machine("a", disk=99.0), machine("b", status="down")))

    assert judged(reading).finding == "system_down" and judged(reading).details == ("b", "a")
    assert judged(reading, BootChecksDefinition(severity={"system_down": "critical"})).status == CRITICAL
    assert judged(reading, BootChecksDefinition(severity={"system_down": "ignore", "system_pressure": "ignore"})).status == SKIPPED


def test_the_sentences_are_told_in_french_with_their_numbers() -> None:
    fr = translator_for("fr")

    assert say(fr, "2 system(s) read, none down, none under pressure") == "2 machine(s) lue(s), aucune en panne, aucune sous tension"
    assert say(fr, "2 system(s) read; 1 system(s) down; 1 with disk use at or above 90 %; 1 at or above 80 °C") == (
        "2 machine(s) lue(s); 1 machine(s) en panne; 1 avec un disque rempli à 90 % ou plus; 1 à 80 °C ou plus"
    )
    assert say(fr, "2 system(s) read; something else") == "2 system(s) read; something else"
    assert say(fr, "Beszel is not connected (its account, in Settings)").startswith("Beszel n'est pas connecté")


class _Beszel(BaseHTTPRequestHandler):
    refuse = False
    records: list[dict] = []

    def _send(self, code: int, body: object) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802 - the name the server calls
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self._send(400, {}) if self.refuse else self._send(200, {"token": "t"})

    def do_GET(self) -> None:  # noqa: N802
        self._send(200, {"items": self.records}) if self.headers.get("Authorization") == "t" else self._send(401, {})

    def log_message(self, *_: object) -> None:
        return


def _serve(records: list[dict], refuse: bool = False):  # type: ignore[no-untyped-def]
    server = HTTPServer(("127.0.0.1", 0), type("Handler", (_Beszel,), {"records": records, "refuse": refuse}))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    return server, f"http://127.0.0.1:{server.server_port}"


def test_read_systems_signs_in_lists_the_machines_and_keeps_none_of_the_secrets_in_a_reason() -> None:
    records = [{"name": "msi", "host": "192.0.2.1", "status": "up", "info": {"dp": 41.5, "mp": 33.0, "dt": 52.0}}, {"name": "raspberry", "status": "down", "info": {}}]
    server, url = _serve(records)
    refused_server, refused_url = _serve([], refuse=True)

    try:
        reading = read_systems(url + "/", "me@example.org", "secret")
        refused = read_systems(refused_url, "me@example.org", "wrong")
    finally:
        server.shutdown()
        refused_server.shutdown()

    assert reading.reachable and [(item.name, item.status, item.disk_pct) for item in reading.systems] == [("msi", "up", 41.5), ("raspberry", "down", None)]
    assert not refused.reachable and refused.reason == "Beszel refused the account"
    assert "me@example.org" not in refused.reason and refused_url not in refused.reason


def test_an_address_that_does_not_answer_is_a_state_with_a_reason_without_the_address() -> None:
    server, url = _serve([])
    server.shutdown()
    server.server_close()
    result = read_systems(url, "a", "b", timeout=1.0)

    assert not result.reachable and result.reason == "Beszel did not answer" and url not in result.reason
    assert datetime.now(timezone.utc).year >= 2026


def test_the_task_asks_beszel_only_with_an_account_and_the_verdict_keeps_the_control(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from aistack.boot_checks.state import read_verdict
    from aistack.kernel.execution import Request
    from aistack.tasks import boot_check
    from tests.unit.boot_checks.test_controls import _facts_file

    asked: list[tuple[str, str, str]] = []

    def fake(url: str, email: str, password: str, timeout: float = 8.0) -> SystemsReading:
        asked.append((url, email, password))

        return SystemsReading(True, "", (machine("raspberry", status="down"),))

    monkeypatch.setattr(boot_check, "read_systems", fake)
    monkeypatch.delenv("BESZEL_EMAIL", raising=False)
    monkeypatch.delenv("BESZEL_PASSWORD", raising=False)
    declaration = tmp_path / "b.yml"
    declaration.write_text("mounts: []\n", encoding="utf-8")
    _facts_file(tmp_path / "facts", datetime.now(timezone.utc))
    payload = {"generated_dir": str(tmp_path / "out"), "facts_dir": str(tmp_path / "facts"), "definition": str(declaration), "cockpit": False}

    def run(name: str) -> dict:
        boot_check.BootCheckTask().execute(Request(request_id=name, task_id="boot.check", payload=payload))
        saved = read_verdict(tmp_path / "out")

        return {result.control: result for result in (saved.results if saved else ())}

    assert run("without")["systems"].status == SKIPPED and asked == []

    monkeypatch.setenv("BESZEL_EMAIL", "me@example.org")
    monkeypatch.setenv("BESZEL_PASSWORD", "secret")
    found = run("with")["systems"]

    assert found.status == WARNING and found.finding == "system_down" and len(asked) == 1
    assert asked[0][1:] == ("me@example.org", "secret") and asked[0][0].startswith("http")

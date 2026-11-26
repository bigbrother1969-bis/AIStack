"""What Scrutiny says of the disks, and how the start-up checks judge it (ADR-0032, slice O1b)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from aistack.boot_checks.controls import CRITICAL, INFORMATION, OK, SKIPPED, UNKNOWN, WARNING, Reading, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.disks import Disk, DiskReading, disk_of, parse_details, parse_summary, read_disks
from aistack.boot_checks.phrases import say
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import DEFINITION, LATER, facts

NOW = LATER
FRESH = (NOW - timedelta(hours=10)).isoformat().replace("+00:00", "Z")
OLD_REPORT = (NOW - timedelta(hours=80)).isoformat().replace("+00:00", "Z")


def entry(name: str = "sda", model: str = "ST2000DM008-2FR102", serial: str = "ZFL1234ABCD", status: int = 0, hours: int = 1000, archived: bool = False, collected: str = FRESH) -> dict:
    return {
        "device": {"device_name": name, "model_name": model, "serial_number": serial, "device_status": status, "archived": archived, "smart_support": False},
        "smart": {"collector_date": collected, "temp": 36, "power_on_hours": hours},
    }


def details(**attributes: tuple[int, int]) -> dict:
    """`details(**{"197": (raw, status)})` as `/api/device/<wwn>/details` carries it."""

    return {"smart_results": [{"attrs": {key: {"status": status, "raw_value": raw, "thresh": 0, "value": 100} for key, (raw, status) in attributes.items()}}]}


def disks_of(*pairs: tuple[dict, dict | None]) -> DiskReading:
    return DiskReading(True, "", tuple(disk_of(f"0x{index}", item, found) for index, (item, found) in enumerate(pairs)))


def judged(reading: DiskReading | None, definition: BootChecksDefinition = DEFINITION) -> Result:
    found = {result.control: result for result in evaluate(facts(), definition, NOW, Reading(True, 0), Reading(True, 0), None, reading)}

    return found["disks"]


GOOD = details(**{"5": (0, 0), "197": (0, 0), "198": (0, 0)})


def test_without_an_address_the_control_is_skipped_and_says_so() -> None:
    result = judged(None)

    assert result.status == SKIPPED and "Scrutiny is not connected" in result.summary


def test_a_scrutiny_that_does_not_answer_is_unknown_never_a_healthy_disk() -> None:
    assert judged(DiskReading(False, "Scrutiny did not answer (TimeoutError)")).status == UNKNOWN
    assert judged(DiskReading(True, "", ())).status == UNKNOWN
    assert judged(disks_of((entry(archived=True), None))).status == UNKNOWN


def test_healthy_disks_pass_and_the_flag_smart_support_is_not_trusted() -> None:
    result = judged(disks_of((entry(), GOOD), (entry("sdb", "WDC WD20EZRZ"), GOOD)))

    assert result.status == OK and result.summary == "2 disk(s) read, none failing"


def test_a_smart_failure_is_to_fix_by_name_with_only_the_end_of_the_serial_number() -> None:
    result = judged(disks_of((entry(), details(**{"5": (0, 0), "9": (10, 1)})), (entry("sdb", "WDC WD20EZRZ"), GOOD)))

    assert result.status == CRITICAL and result.finding == "disk_failing"
    assert result.summary == "2 disk(s) read; 1 failing SMART" and result.details == ("ST2000DM008-2FR102 …ABCD",)
    assert "ZFL1234" not in " ".join(result.details)
    assert judged(disks_of((entry(status=1), GOOD))).status == CRITICAL


def test_a_critical_attribute_above_zero_is_to_watch_and_the_others_are_not() -> None:
    reallocated = judged(disks_of((entry(), details(**{"5": (8, 0), "197": (0, 0)}))))

    assert reallocated.status == WARNING and reallocated.finding == "disk_attribute"
    assert reallocated.summary == "1 disk(s) read; 1 with a critical SMART attribute above zero"
    # CRC errors, high-fly writes, ECC recoveries and the like are counters that mean something only as they grow.
    assert judged(disks_of((entry(), details(**{"199": (9, 2), "189": (15, 2), "195": (295640, 4), "188": (7, 0)})))).status != WARNING


def test_what_only_scrutiny_s_statistics_flag_is_information_never_an_anomaly() -> None:
    result = judged(disks_of((entry(status=2), details(**{"199": (9, 2), "183": (5, 4)})), (entry("sdb"), GOOD)))

    assert result.status == INFORMATION and result.summary == "2 disk(s) read, none failing; 1 flagged only by Scrutiny's statistics"
    assert result.details == ("ST2000DM008-2FR102 …ABCD",)


def test_an_old_disk_is_said_only_when_the_owner_declared_an_age() -> None:
    reading = disks_of((entry(hours=68440), GOOD), (entry("sdb", hours=765), GOOD))

    assert judged(reading).status == OK

    result = judged(reading, BootChecksDefinition(disk_old_hours=50000))

    assert result.status == INFORMATION and "1 old" in result.summary


def test_a_report_that_is_too_old_or_a_disk_without_attributes_is_not_read() -> None:
    stale = judged(disks_of((entry(collected=OLD_REPORT), GOOD)))
    bare = judged(disks_of((entry(), None)))

    assert stale.status == UNKNOWN and "not reported for over 36 h" in stale.summary
    assert bare.status == UNKNOWN and "without readable attributes" in bare.summary
    assert judged(disks_of((entry(collected=""), GOOD))).status == UNKNOWN


def test_a_failure_is_not_hidden_by_a_disk_that_is_not_read() -> None:
    result = judged(disks_of((entry(), details(**{"197": (3, 0)})), (entry("sdb", collected=OLD_REPORT), GOOD)))

    assert result.status == WARNING and "not reported" in result.summary


def test_the_declaration_may_ignore_the_findings_or_change_their_weight() -> None:
    reading = disks_of((entry(), details(**{"197": (3, 0)})))

    assert judged(reading, BootChecksDefinition(severity={"disk_attribute": "ignore"})).status == SKIPPED
    assert judged(reading, BootChecksDefinition(severity={"disk_attribute": "critical"})).status == CRITICAL


def test_two_disks_with_the_same_name_stay_apart_by_their_wwn() -> None:
    reading = parse_summary({"data": {"summary": {"0xA": entry("sda", archived=True), "0xB": entry("sda", "ST4000VX016-3CV104", "WW6Z0001", hours=765)}}})

    assert [wwn for wwn, _ in reading] == ["0xA", "0xB"]
    assert len({disk_of(wwn, item, None).label for wwn, item in reading}) == 2


def test_the_shapes_that_are_not_scrutiny_s_are_not_read() -> None:
    assert parse_summary(None) == [] and parse_summary({"data": {"summary": []}}) == [] and parse_summary({"data": {"summary": {"x": 3}}}) == []
    assert parse_details({"smart_results": []}) is None and parse_details({"smart_results": [{"attrs": {}}]}) is None and parse_details("x") is None
    assert parse_details(details(**{"nvme": (1, 0), "5": (2, 0)})) == (False, (5,))


def test_the_sentences_are_told_in_french_with_their_numbers() -> None:
    fr = translator_for("fr")

    assert say(fr, "8 disk(s) read, none failing") == "8 disque(s) lu(s), aucun en défaut"
    assert say(fr, "8 disk(s) read; 1 failing SMART; 2 old; 3 flagged only by Scrutiny's statistics") == (
        "8 disque(s) lu(s); 1 en échec SMART; 2 ancien(s); 3 signalé(s) par les seules statistiques de Scrutiny"
    )
    assert say(fr, "1 disk(s) read; 1 not reported for over 36 h") == "1 disque(s) lu(s); 1 sans relevé depuis plus de 36 h"
    assert say(fr, "2 disk(s) read; something else") == "2 disk(s) read; something else"
    assert say(fr, "Scrutiny is not connected (its address, in Settings)").startswith("Scrutiny n'est pas connecté")


class _Scrutiny(BaseHTTPRequestHandler):
    summary: dict = {}
    missing: set[str] = set()

    def do_GET(self) -> None:  # noqa: N802 - the name the server calls
        if self.path == "/api/summary":
            body = {"data": {"summary": self.summary}}
        elif self.path.startswith("/api/device/") and self.path.split("/")[3] not in self.missing:
            body = {"data": details(**{"197": (4, 0)})}
        else:
            self.send_error(404)

            return

        raw = json.dumps(body).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_: object) -> None:
        return


def _serve(summary: dict, missing: set[str] = frozenset()):  # type: ignore[no-untyped-def]
    handler = type("Handler", (_Scrutiny,), {"summary": summary, "missing": set(missing)})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    return server, f"http://127.0.0.1:{server.server_port}"


def test_read_disks_asks_the_details_of_the_disks_that_are_still_in_the_machine_only() -> None:
    server, url = _serve({"0xA": entry("sda", archived=True), "0xB": entry("sdb"), "0xC": entry("sdc", "KINGSTON SUV400")}, missing={"0xC"})

    try:
        reading = read_disks(url + "/")
    finally:
        server.shutdown()

    found = {disk.wwn: disk for disk in reading.disks}

    assert reading.reachable and set(found) == {"0xA", "0xB", "0xC"}
    assert found["0xA"].archived and not found["0xA"].attributes_read
    assert found["0xB"].attributes_read and found["0xB"].worn == (197,)
    assert not found["0xC"].attributes_read


def test_an_address_that_does_not_answer_is_a_state_with_a_reason() -> None:
    server, url = _serve({})
    server.shutdown()
    server.server_close()
    refused = read_disks(url, timeout=1.0)

    assert not refused.reachable and "did not answer" in refused.reason


def test_disk_values_are_frozen_data() -> None:
    disk = Disk("0xA", "model", False)

    assert (disk.hours, disk.collected_at, disk.worn, disk.attributes_read) == (None, None, (), False)
    assert datetime.now(timezone.utc) > NOW - timedelta(days=3650)


def test_the_task_reads_scrutiny_when_its_address_is_set_and_the_verdict_keeps_the_disk_control(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from aistack.boot_checks.state import read_verdict
    from aistack.kernel.execution import Request
    from aistack.tasks.boot_check import BootCheckTask
    from tests.unit.boot_checks.test_controls import _facts_file

    server, url = _serve({"0xB": entry("sdb")})
    monkeypatch.setenv("AISTACK_SCRUTINY_URL", url)
    declaration = tmp_path / "b.yml"
    declaration.write_text("mounts: []\n", encoding="utf-8")
    _facts_file(tmp_path / "facts", datetime.now(timezone.utc))
    payload = {"generated_dir": str(tmp_path / "out"), "facts_dir": str(tmp_path / "facts"), "definition": str(declaration), "cockpit": False}

    try:
        data = BootCheckTask().execute(Request(request_id="r", task_id="boot.check", payload=payload)).data
    finally:
        server.shutdown()

    saved = read_verdict(tmp_path / "out")
    found = {result.control: result for result in (saved.results if saved else ())}

    assert data["overall"] == "warning" and found["disks"].status == WARNING and found["disks"].finding == "disk_attribute"

    monkeypatch.delenv("AISTACK_SCRUTINY_URL")
    BootCheckTask().execute(Request(request_id="r2", task_id="boot.check", payload=payload))
    again = {result.control: result for result in (read_verdict(tmp_path / "out") or saved).results}  # type: ignore[union-attr]

    assert again["disks"].status == SKIPPED

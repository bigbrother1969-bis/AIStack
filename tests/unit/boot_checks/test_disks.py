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

    # The task judges against the real clock, so the report must be young now, not 10 h before a fixed date.
    young = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    server, url = _serve({"0xB": entry("sdb", collected=young)})
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


# ---- O5: what the reports kept say over time ----------------------------------------------------------------------

DAY = timedelta(days=1)


def reports(*steps: tuple[int, dict[str, int], int | None]) -> dict:
    """`(days ago, {counter: raw}, temperature)` as the `smart_results` of a disk, newest first as Scrutiny sends them."""

    results = []

    for days, raws, temperature in sorted(steps):
        item: dict = {"date": (NOW - days * DAY).isoformat().replace("+00:00", "Z"), "attrs": {key: {"status": 0, "raw_value": raw, "thresh": 0, "value": 100} for key, raw in raws.items()}}

        if temperature is not None:
            item["temp"] = temperature

        results.append(item)

    return {"smart_results": results}


def with_temp(temperature: int, **extra: object) -> dict:
    found = entry(**extra)  # type: ignore[arg-type]
    found["smart"]["temp"] = temperature

    return found


def test_a_counter_that_rose_in_the_window_is_to_watch_with_what_to_do() -> None:
    link = disks_of((entry(), reports((20, {"188": 0, "199": 9}, 36), (10, {"188": 0, "199": 9}, 36), (1, {"188": 65537, "199": 9}, 37))))
    media = disks_of((entry(), reports((20, {"197": 0}, 36), (1, {"197": 8}, 36))))
    result, worn = judged(link), judged(media)

    assert result.status == WARNING and result.finding == "disk_counter_rising"
    assert result.summary == "1 disk(s) read, none failing; 1 with a counter rising"
    assert result.details[0] == f"ST2000DM008-2FR102 …ABCD: command timeouts rose from 0 to 65537 since {(NOW - 20 * DAY):%Y-%m-%d}"
    assert result.details[-1] == "to do: check the SATA cable and the power connector of the disks above" and len(result.details) == 2
    assert worn.finding == "disk_attribute"  # a sector counter above zero is already to watch; this is the one that moves


def test_a_counter_that_is_high_but_still_is_not_rising_and_one_outside_the_window_is_not_said() -> None:
    steady = disks_of((entry(), reports((20, {"199": 9}, 36), (1, {"199": 9}, 36))))
    old = disks_of((entry(), reports((50, {"188": 0}, 36), (40, {"188": 5}, 36), (10, {"188": 5}, 36), (1, {"188": 5}, 36))))
    single = disks_of((entry(), reports((1, {"188": 5}, 36))))

    assert judged(steady).status == OK and judged(old).status == OK and judged(single).status == OK


def test_the_window_is_the_owner_s_to_set() -> None:
    old = disks_of((entry(), reports((50, {"188": 0}, 36), (40, {"188": 5}, 36), (1, {"188": 5}, 36))))

    assert judged(old, BootChecksDefinition(disk_rising_days=60)).finding == "disk_counter_rising"
    assert judged(old, BootChecksDefinition(severity={"disk_counter_rising": "ignore"})).status == OK


def test_a_hot_disk_is_to_watch_and_one_that_peaked_before_is_only_said() -> None:
    hot = disks_of((with_temp(58), reports((1, {"5": 0}, 58))))
    peaked = disks_of((with_temp(32, model="WDC WD20EZRZ-00Z5HB0", serial="WCC4D5PH"), reports((30, {"5": 0}, 62), (1, {"5": 0}, 32))))
    result, said = judged(hot), judged(peaked)

    assert result.status == WARNING and result.finding == "disk_hot" and result.summary == "1 disk(s) read, none failing; 1 at or above 55 °C"
    assert result.details == ("ST2000DM008-2FR102 …ABCD: 58 °C now (limit 55 °C)", "to do: check the airflow and the fan of the machine")
    assert said.status == INFORMATION and said.summary == "1 disk(s) read, none failing; 1 peaked at or above 55 °C"
    assert said.details == (f"WDC WD20EZRZ-00Z5HB0 …D5PH: reached 62 °C on {(NOW - 30 * DAY):%Y-%m-%d}",)
    assert judged(hot, BootChecksDefinition(disk_temperature_celsius=60)).status == OK


def test_a_report_without_a_date_or_a_temperature_says_nothing_and_a_failure_still_comes_first() -> None:
    bare = disks_of((entry(), details(**{"5": (0, 0)})))
    failing = disks_of((entry(), reports((20, {"199": 1}, 36), (1, {"199": 9, "5": 1}, 70))), (entry(status=1), GOOD))

    assert judged(bare).status == OK
    assert judged(failing).finding == "disk_failing"


def test_the_new_sentences_are_told_in_french_with_their_numbers() -> None:
    fr = translator_for("fr")

    assert say(fr, "1 disk(s) read, none failing; 1 with a counter rising") == "1 disque(s) lu(s), aucun en défaut; 1 avec un compteur en hausse"
    assert say(fr, "ST2000DM008 …5CPV: command timeouts rose from 0 to 65537 since 2026-11-02") == "ST2000DM008 …5CPV : dépassements de délai de commande passés de 0 à 65537 depuis le 2026-11-02"
    assert say(fr, "WDC …5PH: 58 °C now (limit 55 °C)") == "WDC …5PH : 58 °C en ce moment (limite 55 °C)"
    assert say(fr, "WDC …5PH: reached 62 °C on 2026-07-02") == "WDC …5PH : a atteint 62 °C le 2026-07-02"
    assert say(fr, "to do: check the SATA cable and the power connector of the disks above").startswith("à faire : vérifier le câble SATA")
    assert say(fr, "to do: the power supply or its cable is too weak, use the board's own supply").startswith("à faire : l'alimentation")


# O5b: an SSD's life left, from the attribute the owner declared for its model.
KINGSTON = "KINGSTON SUV400S37240G"


def levels(left: int, attribute: str = "231") -> dict:
    return {"smart_results": [{"date": FRESH, "attrs": {attribute: {"status": 0, "raw_value": 100 - left, "thresh": 0, "value": left}, "9": {"status": 0, "raw_value": 1, "thresh": 0, "value": 100}}}]}


def declared(percent: int = 20, **models: int):  # type: ignore[no-untyped-def]
    from dataclasses import replace

    return replace(DEFINITION, ssd_life=models or {"SUV400S37240G": 231}, ssd_life_percent=percent)


def test_an_ssd_with_a_declared_attribute_says_its_life_left_and_how_long_it_lasts_at_the_pace_since_new() -> None:
    result = judged(disks_of((entry(model=KINGSTON, hours=10851), levels(77))), declared())

    assert result.status == INFORMATION
    assert any(line == f"{KINGSTON} …ABCD: 77 % of life left, about 4.1 year(s) at the pace since new" for line in result.details)


def test_an_ssd_at_or_under_the_limit_is_to_watch_with_what_to_do() -> None:
    result = judged(disks_of((entry(model=KINGSTON, hours=10851), levels(20))), declared())

    assert result.status == WARNING and "1 SSD(s) at or below 20 % of life left" in result.summary
    assert result.details[0].endswith("20 % of life left (limit 20 %)") and result.details[-1] == "to do: back up the SSD above and plan its replacement"
    assert judged(disks_of((entry(model=KINGSTON, hours=10851), levels(21))), declared()).status == INFORMATION
    assert judged(disks_of((entry(model=KINGSTON, hours=10851), levels(35))), declared(percent=40)).status == WARNING


def test_nothing_declared_or_nothing_read_is_not_judged_and_never_a_green_wear() -> None:
    plain = judged(disks_of((entry(model=KINGSTON), levels(5))))

    assert plain.status == OK and not any("life left" in line for line in plain.details)
    assert judged(disks_of((entry(model="ST2000DM008"), levels(5))), declared()).status == OK
    assert judged(disks_of((entry(model=KINGSTON), levels(5, attribute="177"))), declared()).status == OK
    assert judged(disks_of((entry(model=KINGSTON), None)), declared()).status == UNKNOWN


def test_the_pace_is_not_said_before_a_month_of_use_or_before_any_wear() -> None:
    new = judged(disks_of((entry(model=KINGSTON, hours=100), levels(90))), declared())
    unused = judged(disks_of((entry(model=KINGSTON, hours=5000), levels(100))), declared())

    assert new.details == (f"{KINGSTON} …ABCD: 90 % of life left",) and unused.details == (f"{KINGSTON} …ABCD: 100 % of life left",)


def test_a_failure_or_a_rising_counter_still_comes_before_the_wear() -> None:
    bad = disks_of((entry(model=KINGSTON, status=1, hours=10851), levels(10)))

    assert judged(bad, declared()).status == CRITICAL


def test_the_declaration_of_the_wear_is_checked_when_loaded(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import pytest

    from aistack.boot_checks.load import load_boot_checks_yaml

    def load(text: str):  # type: ignore[no-untyped-def]
        path = tmp_path / "b.yml"
        path.write_text(text, encoding="utf-8")

        return load_boot_checks_yaml(path)

    assert load("ssd_life:\n  SUV400S37240G: 231\nssd_life_percent: 15\n").ssd_life == {"SUV400S37240G": 231}
    assert load("settle_minutes: 10\n").ssd_life == {}

    for bad in ("ssd_life: [231]\n", "ssd_life:\n  X: 0\n", "ssd_life:\n  X: 300\n", "ssd_life:\n  X: true\n", "ssd_life:\n  '': 231\n"):
        with pytest.raises(ValueError):
            load(bad)


def test_the_wear_sentences_are_told_in_french() -> None:
    fr = translator_for("fr")

    assert say(fr, "1 SSD(s) at or below 20 % of life left") == "1 SSD à 20 % de vie restante ou moins"
    assert say(fr, "KINGSTON …ABCD: 19 % of life left (limit 20 %)") == "KINGSTON …ABCD : 19 % de vie restante (limite 20 %)"
    assert say(fr, "KINGSTON …ABCD: 77 % of life left, about 4.1 year(s) at the pace since new") == "KINGSTON …ABCD : 77 % de vie restante, environ 4.1 an(s) au rythme depuis l'achat"
    assert say(fr, "KINGSTON …ABCD: 77 % of life left") == "KINGSTON …ABCD : 77 % de vie restante"
    assert say(fr, "to do: back up the SSD above and plan its replacement").startswith("à faire : sauvegarder le SSD")


def test_the_life_left_is_still_said_when_another_disk_is_to_watch() -> None:
    rising = details(**{"5": (0, 0), "199": (3, 0)})
    rising["smart_results"] = [
        {"date": (NOW - timedelta(days=10)).isoformat().replace("+00:00", "Z"), "attrs": {"199": {"status": 0, "raw_value": 0, "thresh": 0, "value": 100}}},
        {"date": FRESH, "attrs": {"199": {"status": 0, "raw_value": 7, "thresh": 0, "value": 100}}},
    ]
    result = judged(disks_of((entry(model=KINGSTON, hours=10851), levels(77)), (entry(name="sdb", serial="ZZZ9999WXYZ"), rising)), declared())

    assert result.status == WARNING and any("77 % of life left" in line for line in result.details)

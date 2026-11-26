"""The base controls and the verdict of a start (ADR-0032, B2), and the replay of the morning of 2026-11-26."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.boot_checks.controls import INFORMATION, OK, PENDING, SKIPPED, UNKNOWN, Reading, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.facts import BootFacts, Container
from aistack.boot_checks.state import judge, overall, read_verdict, unknown, write_verdict
from aistack.cli import boot_check

BOOT = datetime(2026, 11, 26, 6, 5, 27, tzinfo=timezone.utc)
LATER = BOOT + timedelta(hours=3)

DEFINITION = BootChecksDefinition(
    expected_containers=("web", "db", "olala"),
    expected_stopped=("olala",),
    mounts=("/", "/media/Data"),
    docker_user_rules=6,
    probes={"proxy": 200},
)


def facts(**changes: object) -> BootFacts:
    base: dict[str, object] = {
        "collected_at": LATER,
        "booted_at": BOOT,
        "uptime_seconds": 10800,
        "boot_id": "boot-1",
        "failed_units": (),
        "mounts": ("/", "/media/Data", "/var/lib/containerd"),
        "containers": (Container("web", "running", "healthy"), Container("db", "running", "none"), Container("olala", "exited", "none")),
        "docker_user_rules": 6,
        "kvm_modules": False,
        "previous_boot_clean": False,
        "ups": "OL",
        "probes": {"proxy": 200},
        "sources": {"ups": "ok"},
    }
    base.update(changes)

    return BootFacts(**base)  # type: ignore[arg-type]


def by_control(results: list[Result]) -> dict[str, Result]:
    return {result.control: result for result in results}


def test_the_morning_of_26_november_is_green_with_the_past_told_as_information() -> None:
    results = evaluate(facts(), DEFINITION, LATER, Reading(True, 0), Reading(True, 0))
    found = by_control(results)

    assert overall(results) == OK
    assert all(result.status in (OK, INFORMATION) for result in results)
    assert found["previous_boot"].status == INFORMATION and "did not end" in found["previous_boot"].summary
    assert found["containers"].summary == "3 expected present, 2 running"
    assert "kvm_modules" in found and found["kvm_modules"].status == OK


def test_a_missing_container_is_to_fix_and_one_stopped_by_mistake_is_to_watch() -> None:
    missing = by_control(evaluate(facts(containers=(Container("web", "running", "none"),)), DEFINITION, LATER))
    stopped = by_control(
        evaluate(
            facts(containers=(Container("web", "exited", "none"), Container("db", "running", "none"), Container("olala", "exited", "none"))),
            DEFINITION,
            LATER,
        )
    )

    assert missing["containers"].status == "critical" and missing["containers"].details == ("db", "olala")
    assert stopped["containers"].status == "warning" and stopped["containers"].details == ("web",)


def test_an_unhealthy_container_is_to_watch_and_one_still_starting_is_pending() -> None:
    unhealthy = by_control(evaluate(facts(containers=(Container("web", "running", "unhealthy"), Container("db", "running", "none"), Container("olala", "exited", "none"))), DEFINITION, LATER))
    starting = by_control(evaluate(facts(containers=(Container("web", "running", "starting"), Container("db", "running", "none"), Container("olala", "exited", "none"))), DEFINITION, LATER))

    assert unhealthy["container_health"].status == "warning"
    assert starting["container_health"].status == PENDING


def test_before_the_settle_time_what_fails_is_pending_not_an_anomaly() -> None:
    early = BOOT + timedelta(minutes=3)
    results = evaluate(facts(failed_units=("foo.service",), containers=()), DEFINITION, early)
    verdict = judge(results, facts(), early)

    assert by_control(results)["failed_units"].status == PENDING
    assert verdict.overall == PENDING and verdict.anomalies == 0


def test_after_the_settle_time_the_same_failures_count() -> None:
    results = evaluate(facts(failed_units=("foo.service", "bar.mount"), docker_user_rules=7, probes={"proxy": 502}, ups="OB DISCHRG"), DEFINITION, LATER)
    found = by_control(results)

    assert found["failed_units"].status == "critical" and found["failed_units"].details == ("foo.service", "bar.mount")
    assert found["docker_user"].details == ("declared 6, found 7",)
    assert found["probes"].status == "critical" and "proxy: 502 instead of 200" in found["probes"].details
    assert found["ups"].status == "warning"
    assert judge(results, facts(), LATER).anomalies == 4


def test_a_control_nobody_declared_is_skipped_and_says_so_never_passed() -> None:
    found = by_control(evaluate(facts(), BootChecksDefinition(), LATER))

    for control in ("mounts", "containers", "docker_user", "probes"):
        assert found[control].status == SKIPPED, control

    assert found["failed_units"].status == OK


def test_a_source_that_did_not_answer_is_unknown_never_healthy() -> None:
    silent = facts(failed_units=None, containers=None, mounts=None, ups=None, sources={"failed_units": "error: denied", "containers": "error: no docker", "ups": "error: no upsc"})
    found = by_control(evaluate(silent, DEFINITION, LATER))

    assert found["failed_units"].status == UNKNOWN and "denied" in found["failed_units"].summary
    assert found["containers"].status == UNKNOWN and found["container_health"].status == UNKNOWN
    assert found["ups"].status == UNKNOWN and found["mounts"].status == UNKNOWN


def test_what_the_owner_ignores_is_not_a_control() -> None:
    quiet = BootChecksDefinition(severity={"kvm_modules": "ignore"})

    assert "kvm_modules" not in by_control(evaluate(facts(kvm_modules=True), quiet, LATER))
    assert by_control(evaluate(facts(kvm_modules=True), BootChecksDefinition(severity={"kvm_modules": "warning"}), LATER))["kvm_modules"].status == "warning"


def test_the_disks_and_the_backups_come_from_the_cockpit_and_a_missing_reading_is_skipped() -> None:
    found = by_control(evaluate(facts(), DEFINITION, LATER, Reading(True, 2), Reading(False, 0, "no threshold for this host")))

    assert found["storage"].status == "warning" and found["storage"].finding == "storage_low"
    assert found["backup"].status == SKIPPED and found["backup"].summary == "no threshold for this host"
    assert by_control(evaluate(facts(), DEFINITION, LATER))["storage"].status == SKIPPED


# -- the incidents since the start ---------------------------------------------------------


def test_an_incident_is_kept_after_it_is_resolved_and_a_new_start_forgets_it() -> None:
    bad = judge(evaluate(facts(failed_units=("foo.service",)), DEFINITION, LATER), facts(), LATER)
    again = judge(evaluate(facts(), DEFINITION, LATER + timedelta(minutes=5)), facts(), LATER + timedelta(minutes=5), bad)
    after_reboot = judge(evaluate(facts(boot_id="boot-2"), DEFINITION, LATER), facts(boot_id="boot-2"), LATER, again)

    assert bad.overall == "critical" and [item.control for item in bad.incidents] == ["failed_units"]
    assert again.overall == OK and again.anomalies == 0
    assert again.incidents[0].resolved_at is not None and again.incidents[0].control == "failed_units"
    assert after_reboot.incidents == ()


def test_the_verdict_is_written_whole_and_read_back_and_a_damaged_file_is_nothing(tmp_path: Path) -> None:
    verdict = judge(evaluate(facts(failed_units=("x.service",)), DEFINITION, LATER), facts(), LATER)
    write_verdict(tmp_path, verdict)

    assert read_verdict(tmp_path) == verdict

    (tmp_path / "boot-check.json").write_text("{not json", encoding="utf-8")
    assert read_verdict(tmp_path) is None
    assert read_verdict(tmp_path / "nowhere") is None
    assert unknown(LATER, "no facts").overall == UNKNOWN


# -- the command ----------------------------------------------------------------------------


def _facts_file(directory: Path, at: datetime, **changes: object) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    report = {
        "collected_at": at.isoformat(),
        "boot": {"booted_at": BOOT.isoformat(), "uptime_seconds": 10800, "boot_id": "boot-1"},
        "failed_units": [],
        "mounts": ["/", "/media/Data"],
        "containers": [{"name": "web", "state": "running", "health": "none"}, {"name": "olala", "state": "exited", "health": "none"}],
        "docker_user_rules": 6,
        "kvm_modules": False,
        "previous_boot_clean": True,
        "probes": {"proxy": 200},
        "sources": {"ups": "absent"},
    }
    report.update(changes)
    (directory / "boot-facts.json").write_text(json.dumps(report), encoding="utf-8")


def test_the_command_judges_writes_and_says_how_it_went(tmp_path: Path, capsys, monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    declaration = tmp_path / "b.yml"
    declaration.write_text("expected_containers: [web, olala]\nexpected_stopped: [olala]\nmounts: [/, /media/Data]\nprobes:\n  proxy: 200\n", encoding="utf-8")
    _facts_file(tmp_path / "facts", now)

    code = boot_check.main(["--once", "--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--definition", str(declaration), "--no-cockpit"])
    printed = capsys.readouterr().out

    assert code == 0 and "start-up checks: ok (0 anomaly(ies))" in printed
    assert read_verdict(tmp_path / "out") is not None

    _facts_file(tmp_path / "facts", now, failed_units=["foo.service"])
    code = boot_check.main(["--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--definition", str(declaration), "--no-cockpit"])

    assert code == 2 and "- foo.service" in capsys.readouterr().out


def test_without_facts_the_command_says_it_could_not_judge_and_never_a_green(tmp_path: Path, capsys) -> None:
    code = boot_check.main(["--facts", str(tmp_path / "none"), "--output", str(tmp_path / "out"), "--no-cockpit"])

    assert code == 3 and "no boot facts yet" in capsys.readouterr().out
    assert (read_verdict(tmp_path / "out") or unknown(BOOT, "")).overall == UNKNOWN


def test_a_dry_run_writes_nothing_and_a_bad_argument_is_refused(tmp_path: Path, capsys) -> None:
    _facts_file(tmp_path / "facts", datetime.now(timezone.utc))

    assert boot_check.main(["--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--dry-run", "--no-cockpit"]) == 0
    assert not (tmp_path / "out" / "boot-check.json").exists()

    with pytest.raises(SystemExit) as stopped:
        boot_check.main(["--nonsense"])

    assert stopped.value.code == 2


def test_the_suggestion_is_the_facts_as_a_declaration_to_copy(tmp_path: Path, capsys) -> None:
    _facts_file(tmp_path / "facts", datetime.now(timezone.utc))

    assert boot_check.main(["--facts", str(tmp_path / "facts"), "--suggest"]) == 0
    printed = capsys.readouterr().out

    assert "expected_containers: [olala, web]" in printed and "expected_stopped: [olala]" in printed
    assert "mounts: [/, /media/Data]" in printed and "docker_user_rules: 6" in printed and "  proxy: 200" in printed

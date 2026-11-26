"""The morning of 26 November 2026 replayed with the controls of today (ADR-0032, B5d).

That morning the MSI stopped hard at 07:04:42 (Paris), came back at 07:05:27 and eight database
containers were checked by hand: six of them had recovered after the stop. The facts below are the
ones the start-up unit reported that day (counts only, never a log line).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.boot_checks.catalogue import choose, circumstances, evaluate_extra, settled_since
from aistack.boot_checks.controls import OK, PENDING, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.state import judge, read_verdict
from aistack.cli import boot_check
from aistack.i18n import translator_for
from aistack.vigil import boot_notify, notify
from tests.unit.boot_checks.test_controls import BOOT, DEFINITION as BASE, LATER, _facts_file, by_control, facts

DATABASES = ("booklore_db", "bookstack_db", "immich_postgres", "nc_db", "paperless_db", "romm-db", "vikunja-db", "wordpress_db")
RECOVERIES = {"booklore_db": 1, "bookstack_db": 1, "immich_postgres": 5, "nc_db": 0, "paperless_db": 3, "romm-db": 0, "vikunja-db": 1, "wordpress_db": 2}
RECOVERED = ("booklore_db", "bookstack_db", "immich_postgres", "paperless_db", "vikunja-db", "wordpress_db")
DEFINITION = BootChecksDefinition(
    expected_containers=BASE.expected_containers,
    expected_stopped=BASE.expected_stopped,
    mounts=BASE.mounts,
    docker_user_rules=BASE.docker_user_rules,
    probes=BASE.probes,
    database_containers=DATABASES,
)


def that_morning(**changes: object):
    # Not a clean stop, the journal does not say why, no disk error in the kernel.
    return facts(previous_boot_clean=False, stop_reason="unknown", kernel_disk_errors=0, database_recovery=RECOVERIES, **changes)


def passes(at: datetime):
    seen = that_morning()
    found = circumstances(seen, DEFINITION)
    chosen = choose(found, DEFINITION)
    results = [*evaluate(seen, DEFINITION, at, None, None), *evaluate_extra(chosen, seen, DEFINITION, None, settled_since(seen, DEFINITION, at))]

    return found, chosen, results, judge(results, seen, at, None, found, chosen)


def test_the_stop_and_the_restart_call_for_the_databases_the_kernel_and_the_cause() -> None:
    found, chosen, _, _ = passes(LATER)

    assert found == ("unclean_previous_stop", "recent_restart")
    assert chosen == ("database_recovery", "kernel_disk_errors", "restart_cause")


def test_three_hours_after_the_start_the_six_databases_that_recovered_are_named() -> None:
    _, _, results, verdict = passes(LATER)
    found = by_control(results)

    assert found["database_recovery"].status == "warning" and found["database_recovery"].details == RECOVERED
    assert found["database_recovery"].summary == "6 database(s) recovered after the start"
    assert "nc_db" not in found["database_recovery"].details and "romm-db" not in found["database_recovery"].details
    assert found["kernel_disk_errors"].status == OK
    assert found["restart_cause"].status == "information" and "not in the journal" in found["restart_cause"].summary
    assert verdict.overall == "warning" and verdict.anomalies == 1


def test_the_minutes_after_the_start_are_not_judged_yet() -> None:
    _, _, results, verdict = passes(BOOT + timedelta(minutes=3))

    assert by_control(results)["database_recovery"].status == PENDING
    assert verdict.overall == PENDING and verdict.anomalies == 0


def test_the_same_morning_without_the_new_controls_would_have_been_green() -> None:
    results = evaluate(that_morning(), DEFINITION, LATER, None, None)

    assert not any(result.status in ("warning", "critical") for result in results if result.control != "monitor")


def test_the_command_replays_the_morning_end_to_end(tmp_path: Path, capsys) -> None:
    declaration = tmp_path / "b.yml"
    declaration.write_text(
        "expected_containers: [web, olala]\nexpected_stopped: [olala]\nmounts: [/, /media/Data]\nprobes:\n  proxy: 200\n"
        f"database_containers: [{', '.join(DATABASES)}]\n",
        encoding="utf-8",
    )
    _facts_file(tmp_path / "facts", datetime.now(timezone.utc), previous_boot_clean=False, stop_reason="unknown", kernel_disk_errors=0, database_recovery=RECOVERIES)
    boot_check.main(["--once", "--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--definition", str(declaration), "--no-cockpit"])
    printed = capsys.readouterr().out
    saved = read_verdict(tmp_path / "out")

    assert "database_recovery" in printed and "6 database(s) recovered after the start" in printed
    assert saved is not None and saved.extra == ("database_recovery", "kernel_disk_errors", "restart_cause")


def test_the_summary_tells_the_anomaly_with_the_databases_counted_never_a_log_line(tmp_path: Path) -> None:
    from aistack.boot_checks.state import write_verdict

    _, _, _, verdict = passes(LATER)
    write_verdict(tmp_path, verdict)
    found, day = boot_notify.events(translator_for("fr"), notify.State(known=True), tmp_path, DEFINITION, LATER + timedelta(minutes=10), "Europe/Paris")
    told = [event.line for event in found]

    assert day == "2026-11-26" and told[0] == "Contrôles du matin :"
    assert any("Récupération des bases de données" in line and "6 base(s) de données récupérée(s) après le démarrage" in line for line in told)
    assert not any("immich_postgres" in line for line in told)

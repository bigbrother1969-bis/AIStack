"""The sentences of the controls, told in the owner's language (ADR-0032)."""

from __future__ import annotations


from aistack.boot_checks.catalogue import evaluate_extra, settled_since
from aistack.boot_checks.controls import Reading, evaluate, evaluate_companion
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.disks import DiskReading
from aistack.boot_checks.monitor import MonitorReading
from aistack.boot_checks.phrases import RULES, say
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import DEFINITION as BASE, LATER, facts
from tests.unit.boot_checks.test_disks import GOOD, OLD_REPORT, details, disks_of, entry

FR = translator_for("fr")
EN = translator_for("en")
WIDE = BootChecksDefinition(
    expected_containers=("web", "db", "olala"),
    expected_stopped=("olala",),
    mounts=("/", "/media/Data"),
    docker_user_rules=6,
    probes={"proxy": 200},
    database_containers=("app_db", "other_db"),
    expected_monitors=("Pi-hole",),
)


def _every_sentence() -> set[str]:
    """What the controls say across the situations that make them speak: good, bad, not read, not declared."""

    said: set[str] = set()
    cases = [
        (facts(), WIDE),
        (facts(failed_units=("a", "b"), mounts=("/",), containers=(), docker_user_rules=7, probes={"proxy": 502}, ups="OB DISCHRG", kvm_modules=True, previous_boot_clean=True), WIDE),
        (facts(failed_units=None, mounts=None, containers=None, docker_user_rules=None, probes=None, ups=None, kvm_modules=None, previous_boot_clean=None, sources={"ups": "error: x"}), WIDE),
        (facts(probes={}), WIDE),
        (facts(), BootChecksDefinition()),
        (facts(), BASE),
    ]

    for seen, definition in cases:
        for reading in (None, Reading(True, 0), Reading(True, 2), Reading(False, 0, ""), Reading(False, 0, "a note of its own")):
            for monitors in (None, MonitorReading(False, "refused"), MonitorReading(True, "", {"Pi-hole": 1, "x": 0, "y": 2}), MonitorReading(True, "", {"a": 1})):
                for result in evaluate(seen, definition, LATER, reading, reading, monitors):
                    said.update([result.summary, *result.details])

                settled = settled_since(seen, definition, LATER)

                for chosen in (("database_recovery", "kernel_disk_errors", "restart_cause", "backup_after_restart", "memory"),):
                    for extra in (
                        facts(database_recovery={"app_db": 1, "other_db": 0}, kernel_disk_errors=2, stop_reason="ups", memory_pressure=30.0, swap_used_percent=90),
                        facts(database_recovery={"app_db": 0, "other_db": 0}, kernel_disk_errors=0, stop_reason="requested", memory_pressure=1.0, swap_used_percent=1),
                        facts(database_recovery={"app_db": 0}, stop_reason="unknown"),
                        facts(database_recovery=None, kernel_disk_errors=None, stop_reason=None, memory_pressure=None, swap_used_percent=None),
                    ):
                        for result in evaluate_extra(chosen, extra, definition, reading, settled):
                            said.add(result.summary)

    for throttled in (0x50005, 0x50000, 0, None):
        for result in evaluate_companion("pi", facts(throttled=throttled, sources={"throttled": "ok"}), "", WIDE, LATER):
            said.update([result.summary, *result.details])

    said.update(result.summary for result in evaluate_companion("pi", None, "", WIDE, LATER))

    aged = BootChecksDefinition(disk_old_hours=50000)
    readings = (
        None,
        DiskReading(False, "refused"),
        DiskReading(True, "", ()),
        disks_of((entry(hours=60000), GOOD), (entry("sdb", status=2), details(**{"199": (9, 2)})), (entry("sdc"), details(**{"5": (3, 0)}))),
        disks_of((entry(), details(**{"9": (1, 1)})), (entry("sdb", collected=OLD_REPORT), GOOD), (entry("sdc"), None)),
        disks_of((entry(), GOOD)),
    )

    for definition in (WIDE, aged, BootChecksDefinition(severity={"disk_attribute": "ignore", "disk_failing": "ignore"})):
        for disks in readings:
            for result in evaluate(facts(), definition, LATER, Reading(True, 0), Reading(True, 0), None, disks):
                said.update([result.summary, *result.details])

    return said


def test_every_sentence_the_controls_say_is_told_in_french() -> None:
    # Names of the host (mounts, containers, monitors) and a note that is not the program's own are shown as they are.
    names = {"/", "/media/Data", "Pi-hole", "ST2000DM008-2FR102 …ABCD", "a", "b", "x", "y", "db", "olala", "web", "a note of its own", "refused"}
    unknown = sorted(text for text in _every_sentence() if say(FR, text) == text and text not in names)

    assert unknown == []


def test_in_english_a_sentence_comes_back_as_it_was_written() -> None:
    assert all(say(EN, text) == text for text in _every_sentence())


def test_the_numbers_and_names_are_kept() -> None:
    assert say(FR, "6 database(s) recovered after the start") == "6 base(s) de données récupérée(s) après le démarrage"
    assert say(FR, "2 down (Gitea, Frigate)") == "2 en panne (Gitea, Frigate)"
    assert say(FR, "1 down, 3 missing or paused (a, b, c, d, +2)") == "1 en panne, 3 absente(s) ou en pause (a, b, c, d, +2)"
    assert say(FR, "7 down") == "7 en panne"
    assert say(FR, "3 missing or paused") == "3 absente(s) ou en pause"
    assert say(FR, "proxy: 502 instead of 200") == "proxy : 502 au lieu de 200"
    assert say(FR, "proxy: not read instead of 200") == "proxy : non lu au lieu de 200"
    assert say(FR, "declared 6, found 7") == "déclaré 6, trouvé 7"
    assert say(FR, "memory pressure 0.06 %, swap 41 % in use") == "pression mémoire 0.06 %, swap utilisé à 41 %"
    assert say(FR, "storage was not read") == "stockage non lu"
    assert say(FR, "under-voltage") == "sous-tension"


def test_a_sentence_that_is_not_the_program_s_own_is_shown_as_it_is() -> None:
    assert say(FR, "Uptime Kuma did not answer (TimeoutError)") == "Uptime Kuma did not answer (TimeoutError)"
    assert say(FR, "not read: error: nope") == "non lu : error: nope"
    assert say(FR, "") == ""


def test_the_catalogs_have_every_sentence_in_both_languages() -> None:
    for key, _ in RULES:
        for translate in (FR, EN):
            assert translate(f"boot_check.phrase.{key}", n=1, running=1, declared=1, found=1, label="x", got="y", want="z", says="s", hours="36", hour="01:00", domain="d", reason="r", pressure="1", swap="2") != f"boot_check.phrase.{key}"

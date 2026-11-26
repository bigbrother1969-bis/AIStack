"""The copies of the host and the restore tests, judged on the morning (O6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.boot_checks.controls import OK, SKIPPED, UNKNOWN, RestoreGap, RestoreReading, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.facts import Copy
from aistack.boot_checks.phrases import say
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import LATER, facts

NOW = datetime(2026, 11, 26, 21, 0, tzinfo=timezone.utc)
DECLARED = BootChecksDefinition(copies={"rescue-image": 9, "snapshots": 3})


def copy(days: float, count: int = 1) -> Copy:
    return Copy(NOW - timedelta(days=days), count)


def control(results: list[Result], name: str) -> Result:
    return next(result for result in results if result.control == name)


def copies_of(definition: BootChecksDefinition = DECLARED, **found: Copy) -> Result:
    return control(evaluate(facts(copies=dict(found), sources={"copies": "ok"}), definition, NOW), "copies")


def test_nothing_declared_is_skipped_and_says_so_never_passed() -> None:
    result = control(evaluate(facts(), BootChecksDefinition(), NOW), "copies")

    assert result.status == SKIPPED and result.summary == "no copy declared"


def test_the_copies_of_the_26_november_are_within_their_limit() -> None:
    # The rescue image of 22 November 05:35 and a Timeshift snapshot of 26 November 14:00, read at 22:00 CET.
    result = copies_of(**{"rescue-image": Copy(datetime(2026, 11, 22, 4, 35, tzinfo=timezone.utc), 1), "snapshots": Copy(datetime(2026, 11, 26, 13, 0, tzinfo=timezone.utc), 9)})

    assert result.status == OK and result.summary == "2 declared copy(ies) within their limit"


def test_a_copy_older_than_its_limit_is_late_and_says_by_how_much() -> None:
    result = copies_of(**{"rescue-image": copy(11.2), "snapshots": copy(0.5)})

    assert result.status == "warning" and result.finding == "copy_late"
    assert result.summary == "1 copy(ies) late or missing"
    assert "rescue-image: newest copy is 12 day(s) old (limit 9 day(s))" in result.details
    assert result.details[-1].startswith("to do: check that the job that makes each copy")


def test_a_copy_with_nothing_in_it_is_missing_and_to_fix() -> None:
    result = copies_of(**{"rescue-image": Copy(None, 0), "snapshots": copy(0.5)})

    assert result.status == "critical" and result.finding == "copy_missing"
    assert result.details[0] == "rescue-image: no copy found"


def test_a_copy_the_host_did_not_tell_is_not_read_and_never_fine() -> None:
    result = copies_of(**{"snapshots": copy(0.5)})

    assert result.status == UNKNOWN and result.summary == "1 declared copy(ies) not read"
    assert result.details == ("rescue-image: not read: the host unit does not report it",)
    assert copies_of(**{"rescue-image": Copy(None, 0, "denied"), "snapshots": copy(0.5)}).details == ("rescue-image: not read: denied",)


def test_a_late_copy_outweighs_an_unread_one_and_the_unread_one_is_still_told() -> None:
    result = copies_of(**{"snapshots": copy(8)})

    assert result.status == "warning" and "rescue-image: not read: the host unit does not report it" in result.details


def test_a_host_unit_that_was_not_told_its_copies_is_not_read() -> None:
    result = control(evaluate(facts(sources={"copies": "absent"}), DECLARED, NOW), "copies")

    assert result.status == UNKNOWN and "AISTACK_BOOT_COPIES" in result.summary


def test_a_source_that_failed_says_why() -> None:
    result = control(evaluate(facts(copies=None, sources={"copies": "error: denied"}), DECLARED, NOW), "copies")

    assert result.status == UNKNOWN and result.summary == "not read: error: denied"


def test_what_the_owner_ignores_is_not_a_finding() -> None:
    quiet = BootChecksDefinition(copies={"rescue-image": 1}, severity={"copy_late": "ignore"})

    assert copies_of(quiet, **{"rescue-image": copy(5)}).status == SKIPPED


def test_a_copy_is_judged_on_the_day_and_not_before() -> None:
    assert copies_of(**{"rescue-image": copy(9.0), "snapshots": copy(3.0)}).status == OK
    assert copies_of(**{"rescue-image": copy(9.1), "snapshots": copy(3.0)}).status == "warning"


def test_the_copies_are_told_in_french() -> None:
    result = copies_of(**{"rescue-image": copy(11.2), "snapshots": copy(0.5)})
    fr = translator_for("fr")

    assert say(fr, result.summary) == "1 copie(s) en retard ou absente(s)"
    assert say(fr, result.details[0]) == "rescue-image : la copie la plus récente a 12 jour(s) (limite 9 jour(s))"
    assert say(fr, "snapshots: no copy found") == "snapshots : aucune copie trouvée"


# The restore tests (OPS-0009).
READING = RestoreReading(tests=6)


def restore_of(reading: RestoreReading | None, definition: BootChecksDefinition | None = None) -> Result:
    return control(evaluate(facts(), definition or BootChecksDefinition(), NOW, restore=reading), "restore_tests")


def test_without_a_reading_or_a_declaration_the_restore_tests_are_skipped() -> None:
    assert restore_of(None).status == SKIPPED
    assert restore_of(RestoreReading(declared=False)).summary == "no restore test declared"
    assert restore_of(RestoreReading(tests=0)).summary == "no restore test declared"


def test_restore_tests_that_cannot_be_read_are_unknown_never_fine() -> None:
    result = restore_of(RestoreReading(reason="the restore test definition cannot be read (bad)"))

    assert result.status == UNKNOWN and "cannot be read" in result.summary


def test_restore_tests_within_their_limit_pass() -> None:
    assert restore_of(READING).status == OK and restore_of(READING).summary == "6 restore test(s) within their limit"


def test_a_restore_test_that_is_old_or_never_done_is_to_watch_and_names_the_service() -> None:
    result = restore_of(RestoreReading(tests=6, gaps=(RestoreGap("wordpress", "stale", NOW - timedelta(days=100), 90.0), RestoreGap("gigabyte", "untested", None, 90.0))))

    assert result.status == "warning" and result.finding == "restore_test_old"
    assert result.summary == "2 of 6 restore test(s) to redo"
    assert result.details[:2] == ("wordpress: last restore test 100 day(s) ago (limit 90 day(s))", "gigabyte: never tested")


def test_a_restore_test_that_failed_is_to_fix() -> None:
    result = restore_of(RestoreReading(tests=6, gaps=(RestoreGap("nextcloud", "failed", NOW, 90.0), RestoreGap("wordpress", "stale", NOW - timedelta(days=100), 90.0))))

    assert result.status == "critical" and result.finding == "restore_test_failed"
    assert result.details[0] == "nextcloud: the last restore test failed"


def test_the_restore_tests_the_owner_ignores_are_not_a_finding() -> None:
    quiet = BootChecksDefinition(severity={"restore_test_old": "ignore"})

    assert restore_of(RestoreReading(tests=6, gaps=(RestoreGap("w", "stale", NOW - timedelta(days=100), 90.0),)), quiet).status == SKIPPED


def test_a_restore_test_is_told_in_french() -> None:
    fr = translator_for("fr")

    assert say(fr, "2 of 6 restore test(s) to redo") == "2 test(s) de restauration sur 6 à refaire"
    assert say(fr, "gigabyte: never tested") == "gigabyte : jamais testé"


def test_the_start_judged_with_its_copies_stays_in_a_stable_order() -> None:
    names = [result.control for result in evaluate(facts(), DECLARED, LATER)]

    assert names.index("backup") < names.index("copies") < names.index("restore_tests") < names.index("previous_boot")

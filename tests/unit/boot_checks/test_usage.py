"""The data disks of the host and their trend (ADR-0032, slice O4b)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from aistack.boot_checks.controls import CRITICAL, OK, SKIPPED, WARNING, Reading, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.phrases import say
from aistack.boot_checks.state import write_usage
from aistack.boot_checks.trend import DiskPoint
from aistack.boot_checks.usage import AUTOMATIC, SAMPLE_EVERY, GB, Sample, UsageReading, due, parse, prune, read_history, read_samples, series
from aistack.host.mounts import Usage
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import DEFINITION, LATER, facts
from tests.unit.boot_checks.test_trend import line

NOW = LATER

MOUNTS = """\
/dev/sdd2 / ext4 rw,relatime 0 0
/dev/sdd2 /srv ext4 ro,relatime 0 0
/dev/sdd2 /media ext4 ro,relatime 0 0
/dev/mapper/stockage-data /media/Data ext4 ro,relatime 0 0
/dev/sdh1 /media/Video ext4 ro,relatime 0 0
/dev/sdh1 /media/Video-bind ext4 ro,relatime 0 0
/dev/sdc1 /mnt/backup ext4 rw,relatime 0 0
tmpfs /run tmpfs rw 0 0
"""


def measure(point: str) -> Usage:
    sizes = {"/media/Data": (1000, 500), "/media/Video": (2000, 1640), "/mnt/backup": (500, 100)}
    total, used = sizes.get(point, (200, 80))

    return Usage(total * GB, (total - used) * GB)


def judged(reading: UsageReading | None, definition: BootChecksDefinition = DEFINITION) -> Result | None:
    results = evaluate(facts(), definition, NOW, Reading(True, 0), Reading(True, 0), None, None, None, reading)

    return {result.control: result for result in results}.get("data_disks")


def sample(point: str, used: float, total: float = 1000.0) -> Sample:
    return Sample(NOW, point, total, used)


def reading(*disks: tuple[str, float, float, tuple[DiskPoint, ...]]) -> UsageReading:
    return UsageReading(tuple(sample(point, used, total) for point, used, total, _ in disks), tuple((point, points) for point, _, _, points in disks))


def test_without_a_declaration_what_is_under_media_and_mnt_is_a_data_disk_once_per_device() -> None:
    found = read_samples((), NOW, lambda: MOUNTS, measure, lambda _: False)

    assert [sample.point for sample in found] == ["/media/Data", "/media/Video", "/mnt/backup"]
    assert found[1].total == 2000.0 and found[1].used == 1640.0
    assert AUTOMATIC == ("/media/", "/mnt/")


def test_a_declaration_names_the_disks_and_replaces_the_automatic_scope() -> None:
    found = read_samples(("/media/Data", "/srv"), NOW, lambda: MOUNTS, measure, lambda _: False)

    assert [sample.point for sample in found] == ["/media/Data", "/srv"]  # what is named, and nothing else (not /media/Video)


def test_a_disk_that_does_not_answer_is_not_read_rather_than_empty() -> None:
    def silent(_: str) -> Usage:
        raise OSError("stale handle")

    assert read_samples((), NOW, lambda: MOUNTS, silent, lambda _: False) == ()


def test_a_sample_is_kept_about_every_seven_hours_and_the_journal_is_bounded(tmp_path: Path) -> None:
    now = NOW
    current = (Sample(now, "/media/Data", 1000.0, 500.0),)

    first = write_usage(tmp_path, current, now, 60)
    again = write_usage(tmp_path, (Sample(now + timedelta(hours=3), "/media/Data", 1000.0, 501.0),), now + timedelta(hours=3), 60)
    later = write_usage(tmp_path, (Sample(now + SAMPLE_EVERY, "/media/Data", 1000.0, 502.0),), now + SAMPLE_EVERY, 60)

    assert len(first) == 1 and len(again) == 1 and len(later) == 2
    assert [item.used for item in read_history(tmp_path)] == [500.0, 502.0]
    assert len(write_usage(tmp_path, (Sample(now + timedelta(days=70), "/media/Data", 1000.0, 600.0),), now + timedelta(days=70), 60)) == 1


def test_a_journal_that_cannot_be_written_is_the_one_that_was_read(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("x")

    assert write_usage(blocked, (sample("/media/Data", 500.0),), NOW, 60) == []


def test_lines_that_are_not_samples_are_left_out_and_series_are_per_disk_oldest_first() -> None:
    text = '{"at": "2026-11-20T10:00:00+00:00", "point": "/a", "total": 10, "used": 2}\nnot json\n{"at": "2026-11-19T10:00:00", "point": "/a", "total": 10, "used": 1}\n{"point": "/b"}\n'
    found = parse(text)

    assert len(found) == 2
    assert [point.used for _, points in series(found) for point in points] == [1.0, 2.0]
    assert prune(found, NOW, 1) == []
    assert due([], (sample("/a", 1.0),), NOW) == [sample("/a", 1.0)]


def test_the_percent_and_the_trend_are_told_with_the_figures() -> None:
    full = judged(reading(("/media/Video", 1900.0, 2000.0, ()), ("/media/Data", 500.0, 1000.0, ())))
    steady = judged(reading(("/media/Data", 500.0, 1000.0, line(10, 0.0, start=500.0, total=1000.0))))
    filling = judged(reading(("/media/Data", 500.0, 1000.0, line(10, 40.0, start=100.0, total=1000.0))))
    young = judged(reading(("/media/Data", 500.0, 1000.0, line(2, 1.0))))

    assert full is not None and full.status == WARNING and full.finding == "data_disk_full"
    assert full.summary == "2 data disk(s) read; 1 at or above 90 %; 2 without enough history"
    assert full.details == ("/media/Video: 95.0 % used (1900 of 2000 GB)",)
    assert steady is not None and steady.status == OK
    assert steady.summary == "1 data disk(s) read, none at or above 90 %, none full within 30 days"
    assert filling is not None and filling.status == WARNING and filling.finding == "data_disk_soon"
    assert filling.summary == "1 data disk(s) read; 1 full within 30 days"
    assert filling.details[0].startswith("/media/Data: about ") and "+40.00 GB/day" in filling.details[0]
    assert young is not None and young.status == OK and young.summary.endswith("1 without enough history")


def test_a_copy_that_jumps_a_data_disk_is_a_step_not_a_trend() -> None:
    flat = line(13, 0.05, start=600.0, total=2000.0)
    jumped = tuple(DiskPoint(p.at, p.total, p.used + (40.0 if p.at > NOW - timedelta(days=5) else 0.0)) for p in flat)
    result = judged(reading(("/media/Lecture", 700.0, 2000.0, jumped)))

    assert result is not None and result.status == OK


def test_no_reading_says_nothing_and_no_disk_is_skipped_never_fine() -> None:
    nothing = judged(UsageReading())

    assert judged(None) is None
    assert nothing is not None and nothing.status == SKIPPED and nothing.summary.startswith("no data disk to read")


def test_the_owner_sets_the_percent_the_days_and_the_weight() -> None:
    disks = reading(("/media/Data", 500.0, 1000.0, ()))

    assert judged(disks, BootChecksDefinition(data_disk_percent=40)).finding == "data_disk_full"  # type: ignore[union-attr]
    assert judged(disks, BootChecksDefinition(data_disk_percent=40, severity={"data_disk_full": "critical"})).status == CRITICAL  # type: ignore[union-attr]
    ignored = judged(disks, BootChecksDefinition(data_disk_percent=40, severity={"data_disk_full": "ignore"}))

    assert ignored is not None and ignored.status == SKIPPED and ignored.summary == "data disk findings are ignored"


def test_the_sentences_are_told_in_french_with_their_numbers() -> None:
    fr = translator_for("fr")

    assert say(fr, "3 data disk(s) read, none at or above 90 %, none full within 30 days") == "3 disque(s) de données lu(s), aucun à 90 % ou plus, aucun plein d'ici 30 jours"
    assert say(fr, "2 data disk(s) read; 1 at or above 90 %; 1 without enough history") == "2 disque(s) de données lu(s); 1 à 90 % ou plus; 1 sans assez d'historique"
    assert say(fr, "/media/Video: 95.0 % used (1900 of 2000 GB)") == "/media/Video : 95.0 % utilisé (1900 sur 2000 Go)"
    assert say(fr, "/media/Data: about 12 day(s) left at +40.00 GB/day (500 of 1000 GB)") == "/media/Data : environ 12 jour(s) restant(s) à +40.00 Go/jour (500 sur 1000 Go)"
    assert say(fr, "data disk findings are ignored") == "les constats des disques de données sont ignorés"

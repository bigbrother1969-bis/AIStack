"""
What the start-up checks say to a person, without a wall clock of its own (ADR-0032, slice B3).

The indicator in the health strip and the detail page read the verdict
`boot-check.json` and say how long ago the host started. The time is
computed when the page is asked for, never when the verdict was written, so
"all well for 5 h 12" is right at every load. A verdict that is old is not
trusted: a green written three hours ago, by a check that stopped running,
reads as *not judged*.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.boot_checks.controls import PENDING
from aistack.boot_checks.state import Verdict, read_verdict

# The vigil judges every 15 minutes; two missed passes make a verdict old.
MAX_AGE = timedelta(minutes=40)
LEVELS = {"ok": "clean", "pending": "watch", "warning": "watch", "critical": "alert", "unknown": "not-instrumented"}


@dataclass(frozen=True)
class Indicator:
    """What the strip shows: a status, how many anomalies, how long since the start, and the note when not judged."""

    status: str
    anomalies: int
    elapsed_seconds: int | None
    note: str = ""
    skipped: int = 0

    @property
    def level(self) -> str:
        """The badge class of the console: clean, watch, alert or not-instrumented."""

        return LEVELS.get(self.status, "not-instrumented")


def indicator(verdict: Verdict | None, now: datetime) -> Indicator:
    if verdict is None:
        return Indicator("unknown", 0, None, "no verdict yet")

    checked = datetime.fromisoformat(verdict.checked_at)
    checked = checked if checked.tzinfo else checked.replace(tzinfo=timezone.utc)

    if now - checked > MAX_AGE:
        return Indicator("unknown", 0, None, f"the last check is old ({verdict.checked_at[:16]})")

    if verdict.overall == "unknown" or verdict.booted_at is None:
        return Indicator("unknown", 0, None, verdict.note or "no facts")

    started = datetime.fromisoformat(verdict.booted_at)
    started = started if started.tzinfo else started.replace(tzinfo=timezone.utc)
    seconds = max(int((now - started).total_seconds()), 0)

    skipped = sum(1 for result in verdict.results if result.status == "skipped")

    return Indicator(verdict.overall, verdict.anomalies, seconds, skipped=skipped)


def elapsed(t: Callable[..., str], seconds: int) -> str:
    """`2 d 3 h`, `5 h 12` or `7 min`, in the page's language."""

    minutes, _ = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    days, hour = divmod(hours, 24)

    if days:
        return t("boot_check.elapsed.days", d=days, h=hour)

    if hours:
        return t("boot_check.elapsed.hours", h=hours, m=f"{minute:02d}")

    return t("boot_check.elapsed.minutes", m=minutes)


def label(t: Callable[..., str], host: str | None) -> str:
    """`Start`, or `Start of <host>` for a companion machine."""

    return t("boot_check.indicator.label") if host is None else t("boot_check.indicator.label_host", host=host)


def sentence(t: Callable[..., str], shown: Indicator, host: str | None = None) -> tuple[str, str]:
    """The strip's text and its tooltip, for this machine or for a companion."""

    name = label(t, host)

    if shown.status == "unknown" or shown.elapsed_seconds is None:
        return (
            t("boot_check.indicator.unknown", label=name),
            t("boot_check.indicator.title_unknown", note=shown.note),
        )

    when = elapsed(t, shown.elapsed_seconds)

    if shown.status == "ok" and shown.skipped:
        return (
            t("boot_check.indicator.ok_partial", label=name, elapsed=when, skipped=shown.skipped),
            t("boot_check.indicator.title_partial", elapsed=when, skipped=shown.skipped),
        )

    if shown.status == "ok":
        return t("boot_check.indicator.ok", label=name, elapsed=when), t("boot_check.indicator.title_ok", elapsed=when)

    if shown.status == PENDING:
        return (
            t("boot_check.indicator.pending", label=name, elapsed=when),
            t("boot_check.indicator.title_pending", elapsed=when),
        )

    return (
        t(f"boot_check.indicator.{shown.status}", label=name, count=shown.anomalies, elapsed=when),
        t("boot_check.indicator.title_anomaly", elapsed=when),
    )


def read_indicator(generated_dir: Path, now: datetime | None = None, host: str | None = None) -> Indicator:
    return indicator(read_verdict(generated_dir, host), now or datetime.now(timezone.utc))


def companions(generated_dir: Path) -> list[str]:
    """The companion machines that have a verdict: one `boot-check-<host>.json` each, by name."""

    try:
        files = sorted(generated_dir.glob("boot-check-*.json"))
    except OSError:
        return []

    return [file.name[len("boot-check-") : -len(".json")] for file in files]


def read_indicators(generated_dir: Path, now: datetime | None = None) -> list[tuple[str | None, Indicator]]:
    """This machine first, then each companion, as the strip draws them."""

    moment = now or datetime.now(timezone.utc)

    return [(None, read_indicator(generated_dir, moment)), *((host, read_indicator(generated_dir, moment, host)) for host in companions(generated_dir))]

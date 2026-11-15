"""
The watch's decision, cycle by cycle: confirm, the window, the hourly
limit, a plan that fails, the dry run. Docker is replaced by a stub.
"""

from __future__ import annotations

from pathlib import Path

from conftest import container

from aistack.cli.restart_watch import Watch, run_cycle
from aistack.restart_watch import journal
from aistack.restart_watch.act import Outcome
from aistack.restart_watch.definition import RestartWatchDefinition

DEFINITION = RestartWatchDefinition()
FACTS = (
    container("gluetun", started=40, health="healthy"),
    container("qbittorrent", started=20, provider="gluetun"),
    container("firefly", health="unhealthy"),
)


class Restarts:
    def __init__(self, fail: str | None = None):
        self.calls: list[tuple[str, ...]] = []
        self.fail = fail

    def __call__(self, order, probes, wait, dry_run=False):
        self.calls.append(tuple(order))
        done = []
        for name in order:
            if dry_run:
                done.append(Outcome(name, True, "dry run"))
                continue
            ok = name != self.fail
            done.append(Outcome(name, ok, "healthy" if ok else "still starting"))
            if not ok:
                break
        return tuple(done)


def cycle(watch, generated, restart, *, now=100.0, facts=FACTS, definition=DEFINITION, dry_run=False, ignore=False, told=None):
    return run_cycle(
        watch, definition, facts, frozenset(),
        now=now, generated=generated, dry_run=dry_run, ignore_window=ignore,
        restart=restart, tell=(lambda title, body: told.append(body)) if told is not None else (lambda t, b: None),
    )


def test_a_container_is_restarted_only_the_second_time_it_is_seen_stuck(tmp_path: Path):
    watch, restart = Watch(started=0.0), Restarts()

    assert cycle(watch, tmp_path, restart) == []
    assert restart.calls == []

    written = cycle(watch, tmp_path, restart, now=130.0)

    assert restart.calls == [("firefly", "qbittorrent")]
    assert [(e.event, e.container) for e in written] == [(journal.RESTARTED, "firefly"), (journal.RESTARTED, "qbittorrent")]


def test_outside_the_window_it_writes_down_once_and_does_nothing(tmp_path: Path):
    watch, restart = Watch(started=0.0), Restarts()
    late = 31 * 60.0

    cycle(watch, tmp_path, restart, now=late)
    first = cycle(watch, tmp_path, restart, now=late + 30)
    again = cycle(watch, tmp_path, restart, now=late + 60)

    assert restart.calls == []
    assert sorted(e.container for e in first) == ["firefly", "qbittorrent"]
    assert {e.event for e in first} == {journal.OUTSIDE_WINDOW}
    assert again == []
    assert journal.read_state(tmp_path)["window_open"] is False


def test_ignoring_the_window_acts_anyway(tmp_path: Path):
    watch, restart = Watch(started=0.0), Restarts()

    cycle(watch, tmp_path, restart, now=99999.0, ignore=True)
    cycle(watch, tmp_path, restart, now=100030.0, ignore=True)

    assert restart.calls


def test_a_third_attempt_in_the_hour_is_refused(tmp_path: Path):
    watch, restart = Watch(started=0.0), Restarts()
    only = (container("firefly", health="unhealthy"),)

    for moment in (100.0, 130.0, 200.0, 230.0, 300.0, 330.0):
        cycle(watch, tmp_path, restart, now=moment, facts=only)

    events = [e.event for e in journal.read(tmp_path)]

    assert len(restart.calls) == 2
    assert journal.SKIPPED_LIMIT in events


def test_a_container_that_does_not_come_back_is_reported_and_stops_the_plan(tmp_path: Path):
    watch, restart, told = Watch(started=0.0), Restarts(fail="firefly"), []

    cycle(watch, tmp_path, restart, told=told)
    written = cycle(watch, tmp_path, restart, now=130.0, told=told)

    assert [(e.event, e.container) for e in written] == [
        (journal.FAILED, "firefly"),
        (journal.FAILED, "qbittorrent"),
    ]
    assert len(told) == 1 and "firefly" in told[0]


def test_a_dry_run_plans_but_spends_no_attempt(tmp_path: Path):
    watch, restart = Watch(started=0.0), Restarts()

    cycle(watch, tmp_path, restart, dry_run=True)
    written = cycle(watch, tmp_path, restart, now=130.0, dry_run=True)

    assert {e.event for e in written} == {journal.PLANNED}
    assert watch.attempts == {}


def test_what_recovers_is_forgotten(tmp_path: Path):
    watch, restart = Watch(started=0.0), Restarts()

    cycle(watch, tmp_path, restart)
    cycle(watch, tmp_path, restart, facts=(container("firefly", health="healthy"),), now=130.0)

    assert watch.seen == {}
    assert journal.read_state(tmp_path)["stuck"] == []

from pathlib import Path

import pytest

from aistack.cli.resource_priority_monitor import (
    USAGE,
    ApplyReport,
    is_playing_now,
    log_cycle,
    parse,
)


class FakeJellyfinProvider:
    """
    A provider that answers without a Jellyfin daemon.

    `is_playing_now` is the chain under test: reachability and
    session shape in, a boolean out. `JellyfinProvider` itself is
    covered by its own tests against a real `ThreadingHTTPServer`,
    and `has_active_playback` by its own — this stays a stand-in
    for the one interface both are read through, `collect()`.
    """

    def __init__(self, jellyfin: dict):
        self._jellyfin = jellyfin

    def collect(self):
        return {"jellyfin": self._jellyfin}


def test_playing_now_is_true_when_reachable_and_playing():
    provider = FakeJellyfinProvider(
        {
            "reachable": True,
            "sessions": [
                {
                    "NowPlayingItem": {"Name": "A Film"},
                    "PlayState": {"IsPaused": False},
                }
            ],
        }
    )

    assert is_playing_now(provider) is True


def test_playing_now_is_false_when_reachable_but_idle():
    provider = FakeJellyfinProvider({"reachable": True, "sessions": []})

    assert is_playing_now(provider) is False


def test_playing_now_is_false_when_unreachable():
    """
    Decision #4: an unreachable Jellyfin falls back to full power
    for the background containers rather than leaving them
    throttled by a supervision failure — read here as "not playing"
    regardless of what `sessions` (empty, stale, or absent) says.
    """

    provider = FakeJellyfinProvider(
        {"reachable": False, "unreachable_reason": "timed out", "sessions": []}
    )

    assert is_playing_now(provider) is False


def test_parse_defaults_to_the_real_definition_looping_forever():
    definition_path, once, dry_run = parse([])

    assert definition_path.name == "resource_priority.yml"
    assert once is False
    assert dry_run is False


def test_parse_accepts_a_definition_override():
    definition_path, _, _ = parse(["--definition", "/tmp/custom.yml"])

    assert definition_path == Path("/tmp/custom.yml")


def test_parse_accepts_once_and_dry_run_together():
    _, once, dry_run = parse(["--once", "--dry-run"])

    assert once is True
    assert dry_run is True


def test_parse_prints_usage_and_exits_on_help():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--help"])

    assert excinfo.value.code == 0


def test_parse_rejects_an_unknown_argument():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--nonsense"])

    assert excinfo.value.code == 2


def test_usage_names_every_flag_parse_accepts():
    for flag in ("--definition", "--once", "--dry-run"):
        assert flag in USAGE


def test_log_cycle_is_silent_when_nothing_changed(capsys):
    log_cycle(boosted=False, report=ApplyReport())

    assert capsys.readouterr().out == ""


def test_log_cycle_prints_when_something_was_applied(capsys):
    log_cycle(boosted=True, report=ApplyReport(applied=("jellyfin",)))

    out = capsys.readouterr().out

    assert "state=boosted" in out
    assert "jellyfin" in out


def test_log_cycle_always_prints_a_labelled_line(capsys):
    """
    The shutdown release is worth a line even when nothing needed
    to change — it is the record that the monitor exited cleanly
    rather than the reason a container quietly stayed throttled.
    """

    log_cycle(boosted=False, report=ApplyReport(), label="releasing on exit")

    assert "releasing on exit" in capsys.readouterr().out

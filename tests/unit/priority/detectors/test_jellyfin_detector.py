from aistack.priority.detectors.jellyfin import JellyfinDetector


class FakeJellyfinProvider:
    """
    A provider that answers without a Jellyfin daemon.

    `JellyfinDetector.is_active()` is the chain under test:
    reachability and session shape in, a boolean out.
    `JellyfinProvider` itself is covered by its own tests against a
    real `ThreadingHTTPServer`, and `has_active_playback` by its
    own — this stays a stand-in for the one interface both are read
    through, `collect()`. Moved here unchanged, 2026-09-03, from
    `tests/unit/cli/test_resource_priority_monitor.py`'s own
    `is_playing_now` tests, when that function's logic became this
    class.
    """

    def __init__(self, jellyfin: dict):
        self._jellyfin = jellyfin

    def collect(self):
        return {"jellyfin": self._jellyfin}


def detector(jellyfin: dict) -> JellyfinDetector:
    return JellyfinDetector(
        url="http://127.0.0.1:8096",
        api_key="unused",
        provider=FakeJellyfinProvider(jellyfin),
    )


def test_is_active_when_reachable_and_playing():
    subject = detector(
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

    assert subject.is_active() is True


def test_is_not_active_when_reachable_but_idle():
    subject = detector({"reachable": True, "sessions": []})

    assert subject.is_active() is False


def test_is_not_active_when_unreachable():
    """
    Decision #4: an unreachable Jellyfin falls back to full power
    for the background containers rather than leaving them
    throttled by a supervision failure — read here as "not active"
    regardless of what `sessions` (empty, stale, or absent) says.
    """

    subject = detector(
        {"reachable": False, "unreachable_reason": "timed out", "sessions": []}
    )

    assert subject.is_active() is False

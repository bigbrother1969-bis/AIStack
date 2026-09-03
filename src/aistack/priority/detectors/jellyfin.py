from __future__ import annotations

from aistack.priority.playback import has_active_playback
from aistack.providers.jellyfin import JellyfinProvider


class JellyfinDetector:
    """
    Detect activity by asking Jellyfin's own `/Sessions` endpoint.

    Conforms to `aistack.priority.detectors.base.Detector`. This is
    `aistack.cli.resource_priority_monitor.is_playing_now`, moved
    here unchanged when this feature generalised to a pluggable
    detector abstraction 2026-09-03 — the original monitor's own
    logic, not a rewrite: a provider that observes and does not
    qualify (`JellyfinProvider`), composed with the pure function
    that decides what a session means (`has_active_playback`).

    **Decision #4 (2026-09-03, the original build) carries forward
    unchanged: an unreachable Jellyfin reads as "not active".** A
    supervision failure must not starve the background containers
    indefinitely, so the fallback is full power for them — accepted
    cost: Jellyfin itself may then contend with them on a day its
    own API is down, which decision #4 already weighed against the
    alternative and chose.

    **The key is a value, never a lookup** — GOV-P-001, same
    handling as `JellyfinProvider` itself and `SyncthingProvider`.
    This class reads no environment; the caller
    (`aistack.cli.resource_priority_monitor.main`) reads
    `definition.priority[i].detector.api_key_env` from the process
    environment and passes the raw key in.

    **`provider` is test-only injection, not a real configuration
    knob.** Defaulting to a real `JellyfinProvider` built from
    `url`/`api_key`/`timeout` covers every real caller; the governed
    suite passes a fake in its place — the same seam
    `is_playing_now(provider)` gave the original, single-detector
    monitor before this class existed, kept rather than lost when
    that function's logic moved here.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        timeout: float = 5.0,
        *,
        provider: JellyfinProvider | None = None,
    ) -> None:
        self._provider = (
            provider
            if provider is not None
            else JellyfinProvider(url, api_key, timeout=timeout)
        )

    def is_active(self) -> bool:
        observation = self._provider.collect()["jellyfin"]

        if not observation["reachable"]:
            return False

        return has_active_playback(observation["sessions"])

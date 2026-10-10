from __future__ import annotations

from aistack.priority.playback import has_active_playback
from aistack.providers.jellyfin import JellyfinProvider


class JellyfinDetector:
    """
    Detect activity by asking Jellyfin's `/Sessions` endpoint.

    An unreachable Jellyfin reads as "not active", so a monitoring failure
    never leaves the background containers throttled indefinitely.
    `api_key` is the key itself; the caller reads it from the environment.
    `provider` is for tests.
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

"""
Knowledge Transport Layer - Event Publisher interface.
"""

from __future__ import annotations

from typing import Protocol


class EventPublisher(Protocol):
    """
    Publishes transport events.
    """

    def publish(
        self,
        event_name: str,
        payload: dict,
    ) -> None:
        ...

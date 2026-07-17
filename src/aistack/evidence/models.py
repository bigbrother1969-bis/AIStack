"""Technology-neutral Evidence models."""

from dataclasses import dataclass

from aistack.item import Item


@dataclass(frozen=True, slots=True)
class Evidence(Item):
    """
    Immutable acquired evidence.

    Evidence represents raw facts acquired from reality before any
    normalization or interpretation.
    """

    source: str

    def __post_init__(self) -> None:
        Item.__post_init__(self)

        if not self.source.strip():
            raise ValueError("source must not be empty")

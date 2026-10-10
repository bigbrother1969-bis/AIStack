from __future__ import annotations

from dataclasses import dataclass

from aistack.selection.subtree import SubtreeResolution


@dataclass(frozen=True)
class CapacityVerdict:
    """Whether the designated media fit in the declared capacity.

    The capacity is a quota declared in the application definition, not a
    device measurement: the Syncthing API exposes no free space. With no
    quota declared, `declared` is False and the verdict `fits`.
    `remaining_bytes` goes negative on overflow, to show how much must go.
    """

    declared: bool
    declared_bytes: int
    selected_bytes: int
    remaining_bytes: int
    percent_used: float
    fits: bool

    @property
    def overflow_bytes(self) -> int:
        """How much has to come off, zero when it fits."""

        return max(0, -self.remaining_bytes)


def assess_capacity(
    resolution: SubtreeResolution, declared_bytes: int
) -> CapacityVerdict:
    """Weigh a resolution against the declared capacity.

    Pure, so the screen can show it before anything is written;
    `materialise_by_hardlink` also takes the verdict to enforce it at write
    time. A declared capacity of zero or less means "not declared".
    """

    selected = resolution.media_bytes

    if declared_bytes <= 0:
        return CapacityVerdict(
            declared=False,
            declared_bytes=0,
            selected_bytes=selected,
            remaining_bytes=0,
            percent_used=0.0,
            fits=True,
        )

    return CapacityVerdict(
        declared=True,
        declared_bytes=declared_bytes,
        selected_bytes=selected,
        remaining_bytes=declared_bytes - selected,
        percent_used=selected / declared_bytes * 100,
        fits=selected <= declared_bytes,
    )

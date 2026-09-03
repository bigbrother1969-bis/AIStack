from __future__ import annotations

from dataclasses import dataclass

from aistack.selection.subtree import SubtreeResolution


@dataclass(frozen=True)
class CapacityVerdict:
    """
    Whether what is designated fits in the capacity that was declared.

    **`declared` is the field that keeps this honest.** The
    capacity is a number the owner writes in the application
    definition, not a measurement of the device: the Syncthing API
    exposes no free space, measured on 2026-08-29 on both the
    server and the phone, and the owner decided that day to
    declare a quota rather than approximate one. A screen that
    printed *61 Go free* would be inventing; a screen that prints
    *61 Go left of the 64 Go you declared* is telling the truth.

    So a verdict where nothing was declared says so, and says
    `fits` — an undeclared quota constrains nothing. It does not
    pretend to a capacity of zero, which would refuse everything,
    and it does not silently behave as if a quota existed.

    `remaining_bytes` goes negative on overflow rather than
    clamping at zero. *How far over* is the number the owner acts
    on: it says how much has to come off, and the owner's saved
    selection was 118 Gio against 64 Go on 2026-08-29 — nearly
    double, which is a selection to halve and not a line to nudge.
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
    """
    Weigh a resolution against the declared capacity.

    Pure, and separate from the materialisation on purpose: the
    screen has to show this on every display, long before anyone
    clicks anything. A guard that only existed inside the write
    would answer the question at the one moment it is too late to
    be useful — after the human has chosen.

    It is *also* enforced at the write, and that is a different
    concern: see `materialise_by_hardlink`, which takes a verdict
    rather than a number so that materialising without having
    weighed is not something a caller can express.

    A declared capacity of zero or less means *not declared*. The
    definition is written by hand; an absent line and a line
    reading `0` are the same accident, and neither should quietly
    become a quota that refuses everything.
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

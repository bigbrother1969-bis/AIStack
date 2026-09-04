from dataclasses import dataclass


@dataclass(frozen=True)
class CpuReductionMeasurement:
    """
    A before/after CPU reading pair, and whether the drop between
    them clears a declared threshold.

    `STD-0300` § VS-4 criterion 4.8: "before/after verification
    measures a CPU reduction ≥ 95 %." The reference incident is
    `aistack-selection-ui`'s permanent `--reload` (§ VS-4's own
    reference incident): 48-58 % of one core while idle, before;
    `docker-compose.selection-ui.yml`'s own comment records 0.32 %,
    measured after two minutes of inactivity, after — a reduction
    this class can verify rather than take on faith.

    Both readings carry their own observation reference, the same
    discipline `CorrelatedFinding` (VS-4 4.2) already holds each of
    its three readings to: a percentage with no stated source is an
    assertion, not a measurement.
    """

    subject: str
    before_percent: float
    after_percent: float
    before_reference: str
    after_reference: str
    threshold_percent: float = 95.0

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError(
                "a CPU reduction measurement names the subject it "
                "is about; this one names none"
            )

        if self.before_percent <= 0.0:
            raise ValueError(
                f"{self.subject}: a before-reading of "
                f"{self.before_percent}% cannot be reduced from — "
                f"nothing to measure a drop against"
            )

        if self.after_percent < 0.0:
            raise ValueError(
                f"{self.subject}: an after-reading of "
                f"{self.after_percent}% is not a CPU percentage"
            )

        if self.after_percent > self.before_percent:
            raise ValueError(
                f"{self.subject}: after ({self.after_percent}%) "
                f"exceeds before ({self.before_percent}%) — this is "
                f"not a reduction"
            )

        if not self.before_reference.strip():
            raise ValueError(
                f"{self.subject}: the before-reading carries no "
                f"observation reference"
            )

        if not self.after_reference.strip():
            raise ValueError(
                f"{self.subject}: the after-reading carries no "
                f"observation reference"
            )

    @property
    def reduction_percent(self) -> float:
        return (
            (self.before_percent - self.after_percent)
            / self.before_percent
            * 100.0
        )

    @property
    def meets_threshold(self) -> bool:
        return self.reduction_percent >= self.threshold_percent

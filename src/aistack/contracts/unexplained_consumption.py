from dataclasses import dataclass


@dataclass(frozen=True)
class UnexplainedConsumption:
    """
    A container using CPU above the threshold while absent from the
    resource-priority definition (neither `priority` nor `background`).

    Not a verdict: the container may be legitimately busy and simply not
    yet classified.
    """

    container: str
    cpu_percent: float
    threshold_percent: float

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError(
                "an unexplained-consumption finding names the "
                "container it is about; this one names none"
            )

        if self.cpu_percent < self.threshold_percent:
            raise ValueError(
                f"{self.container} reads {self.cpu_percent}%, below "
                f"the declared threshold of {self.threshold_percent}%: "
                f"this is not what the threshold names as unexplained"
            )

from dataclasses import dataclass


@dataclass(frozen=True)
class UnexplainedConsumption:
    """
    One container using CPU while nothing declares what it is for.

    `STD-0300` § VS-4 criterion 4.1: "AIStack detects abnormal idle
    resource consumption without being pointed at the service." The
    reference incident — `aistack-selection-ui` at 48-58 % of one
    core while idle — was, at the time, exactly this: a container
    Docker reported that appeared in neither `priority` nor
    `background` of `ResourcePriorityDefinition`. Nobody had declared
    a resource expectation for it, so nothing was watching it either.

    **This is not a verdict on the container, and it does not
    replace a declaration.** A container this names may turn out to
    be legitimately busy and simply not yet classified — the same
    way `frigate` was not a fault, only undeclared, before
    `OPS-0003`. What this states is narrower and purely observed:
    this container is not in the resource-priority definition, and
    its own reading crossed the declared threshold. Explaining *why*
    — `OPS-0001`'s remediation, `OPS-0003`'s lifecycle context, a
    `resource_priority.yml` entry the owner has not written yet — is
    a later step, not this one.
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

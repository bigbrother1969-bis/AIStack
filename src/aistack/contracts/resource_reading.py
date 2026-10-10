from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerCpuReading:
    """
    One container's CPU usage at one point in time, from `docker stats`.

    A reading, not a verdict: `aistack.runtime.idle_consumption` judges
    it. `cpu_percent` is Docker's `CPUPerc`, parsed from `"12.34%"`.
    """

    container: str
    cpu_percent: float

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError(
                "a CPU reading is about one container; this one names none"
            )

        if self.cpu_percent < 0:
            raise ValueError(
                f"{self.container} reports negative CPU usage: "
                f"{self.cpu_percent}"
            )

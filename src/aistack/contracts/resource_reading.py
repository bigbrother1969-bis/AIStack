from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerCpuReading:
    """
    One container's own CPU usage, at one point in time.

    ARC-P-012's boundary applies here exactly as it does to
    `RuntimeObservation`: this is what `docker stats` reported,
    concluding nothing. Whether a reading is "abnormal" is a
    question for something that reads a collection of these against
    a declared policy — `aistack.runtime.idle_consumption`, not this
    type.

    `cpu_percent` is Docker's own `CPUPerc`, already parsed from its
    `"12.34%"` string form — the same reading
    `CpuThresholdDetector._read_cpu_percent` takes for one named
    container, here taken for every container in one call instead,
    which is the mechanism `STD-0300` § VS-4 criterion 4.1 asks for:
    detection without being pointed at a service.
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

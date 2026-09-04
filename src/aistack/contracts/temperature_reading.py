from dataclasses import dataclass


@dataclass(frozen=True)
class TemperatureReading:
    """
    One hardware sensor's own reported temperature, together with
    whichever risk thresholds the sensor itself declares.

    `high_celsius` and `critical_celsius` are the sensor chip's own
    limits — `sensors`' (lm-sensors) own "high" and "crit" fields,
    not a number `aistack` proposed. `STD-0300` § VS-4's
    sustainability-anomaly qualification (`OPS-0004`) asks whether
    excessive CPU consumption carries "a risk to hardware
    components"; reading the hardware's own declared limit answers
    that without inventing a threshold no one has stated
    (`GOV-P-001`) — the same reasoning that keeps
    `idle_consumption.DEFAULT_THRESHOLD_PERCENT` named as a proposed
    guess rather than a fact.

    Either threshold may be absent — not every sensor chip reports
    both, and some report neither. Absent is a fact about the
    reading, not zero risk: `at_or_above_high`/`at_or_above_critical`
    return `None` rather than `False` when there is nothing to
    compare against, the same "not measured is not zero" convention
    `false-declarations` already holds for an inventory that cannot
    see everything.
    """

    sensor: str
    celsius: float
    high_celsius: float | None = None
    critical_celsius: float | None = None

    def __post_init__(self) -> None:
        if not self.sensor.strip():
            raise ValueError(
                "a temperature reading names the sensor it came "
                "from; this one names none"
            )

    @property
    def at_or_above_high(self) -> bool | None:
        if self.high_celsius is None:
            return None
        return self.celsius >= self.high_celsius

    @property
    def at_or_above_critical(self) -> bool | None:
        if self.critical_celsius is None:
            return None
        return self.celsius >= self.critical_celsius

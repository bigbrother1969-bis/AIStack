from dataclasses import dataclass


@dataclass(frozen=True)
class TemperatureReading:
    """
    One hardware sensor's temperature, with the limits the sensor
    itself declares.

    `high_celsius`/`critical_celsius` are lm-sensors' "high" and "crit"
    fields, not values AIStack chose. Either may be absent; then
    `at_or_above_high`/`at_or_above_critical` return `None`, not False.
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

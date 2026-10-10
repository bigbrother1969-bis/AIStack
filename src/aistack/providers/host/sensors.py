from __future__ import annotations

import re

from aistack.contracts.temperature_reading import TemperatureReading


_READING_LINE = re.compile(
    r"^(?P<label>[^\s:][^:]*):\s+(?P<value>[+-]?\d+\.\d+)°C"
)
_HIGH = re.compile(r"high\s*=\s*([+-]?\d+\.\d+)°C")
_CRIT = re.compile(r"crit\s*=\s*([+-]?\d+\.\d+)°C")


def parse_sensors_output(text: str) -> tuple[TemperatureReading, ...]:
    """Parse the human-readable output of `sensors` (lm-sensors) into
    temperature readings. Pure: no subprocess call.

    A chip block looks like this:

    ```
    k10temp-pci-00c3
    Adapter: PCI adapter
    temp1:        +70.5°C  (high = +70.0°C)
                           (crit = +72.0°C, hyst = +70.0°C)
    ```

    The first line of a block is the chip name; `Adapter:` is skipped; any
    other top-level line with a `°C` value is a reading (fans and voltages
    are ignored). An indented line continues the previous reading
    (`crit`/`hyst` often wrap). The sensor name is `chip/label`, since a
    bare `temp1` is not unique across chips.
    """

    readings: list[TemperatureReading] = []

    chip: str | None = None
    label: str | None = None
    value: float | None = None
    extra = ""

    def flush() -> None:
        nonlocal label, value, extra

        if label is not None and value is not None and chip is not None:
            high = _HIGH.search(extra)
            crit = _CRIT.search(extra)
            readings.append(
                TemperatureReading(
                    sensor=f"{chip}/{label}",
                    celsius=value,
                    high_celsius=float(high.group(1)) if high else None,
                    critical_celsius=float(crit.group(1)) if crit else None,
                )
            )

        label = None
        value = None
        extra = ""

    for raw_line in text.splitlines():

        if not raw_line.strip():
            flush()
            chip = None
            continue

        if chip is None:
            chip = raw_line.strip()
            continue

        is_continuation = raw_line[:1].isspace()

        if not is_continuation:
            flush()

            if raw_line.startswith("Adapter:"):
                continue

            match = _READING_LINE.match(raw_line)

            if match:
                label = match.group("label").strip()
                value = float(match.group("value"))
                extra = raw_line

            continue

        if label is not None:
            extra += " " + raw_line.strip()

    flush()

    return tuple(readings)

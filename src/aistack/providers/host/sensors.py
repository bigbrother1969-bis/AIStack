from __future__ import annotations

import re

from aistack.contracts.temperature_reading import TemperatureReading


_READING_LINE = re.compile(
    r"^(?P<label>[^\s:][^:]*):\s+(?P<value>[+-]?\d+\.\d+)°C"
)
_HIGH = re.compile(r"high\s*=\s*([+-]?\d+\.\d+)°C")
_CRIT = re.compile(r"crit\s*=\s*([+-]?\d+\.\d+)°C")


def parse_sensors_output(text: str) -> tuple[TemperatureReading, ...]:
    """
    `sensors`' (lm-sensors) own human-readable output, read into
    typed readings — never a subprocess call here, so this is
    tested directly against real captured text rather than only
    live, the same split `extract_dockerfile_command` already holds
    between parsing and the host-touching call around it.

    A chip's own block looks like this, read live on GIGABYTE,
    2026-09-04:

    ```
    k10temp-pci-00c3
    Adapter: PCI adapter
    temp1:        +70.5°C  (high = +70.0°C)
                           (crit = +72.0°C, hyst = +70.0°C)
    ```

    The first line of a block (after a blank line, or at the very
    start of the text) is the chip's own name; an `Adapter:` line is
    skipped; a reading is any further top-level line naming a value
    in `°C` — a fan speed or a voltage line does not match and is
    silently not recorded, since this reads temperatures only.

    **Indentation is what tells a continuation line from a new
    reading**, not blank lines — `crit`/`hyst` commonly wrap onto
    their own indented line, still describing the reading just
    above. A line that is *not* indented always starts something
    new, whether or not it turns out to be a temperature: whatever
    was pending is closed off before it is read.

    The sensor name returned combines the chip and the label
    (`k10temp-pci-00c3/temp1`) — a bare `temp1` is not unique across
    chips, and a citable reading needs to be.
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

from aistack.providers.host.sensors import parse_sensors_output


REAL_GIGABYTE_OUTPUT = (
    "k10temp-pci-00c3\n"
    "Adapter: PCI adapter\n"
    "temp1:        +70.5°C  (high = +70.0°C)\n"
    "                       (crit = +72.0°C, hyst = +70.0°C)\n"
)


def test_the_real_gigabyte_output_is_read_correctly():
    """
    Captured live, 2026-09-04, asking how the owner's own Uptime
    Kuma temperature check reads GIGABYTE (`OPS-0004`'s
    sustainability-anomaly evidence).
    """

    readings = parse_sensors_output(REAL_GIGABYTE_OUTPUT)

    assert len(readings) == 1
    reading = readings[0]
    assert reading.sensor == "k10temp-pci-00c3/temp1"
    assert reading.celsius == 70.5
    assert reading.high_celsius == 70.0
    assert reading.critical_celsius == 72.0


def test_empty_output_yields_no_readings():

    assert parse_sensors_output("") == ()


def test_a_chip_with_no_temperature_lines_yields_nothing():

    text = "nct6775-isa-0a20\nAdapter: ISA adapter\nfan1:        1234 RPM\n"

    assert parse_sensors_output(text) == ()


def test_a_reading_with_no_declared_thresholds():

    text = "acpitz-acpi-0\nAdapter: ACPI interface\ntemp1:        +45.0°C\n"

    readings = parse_sensors_output(text)

    assert len(readings) == 1
    assert readings[0].celsius == 45.0
    assert readings[0].high_celsius is None
    assert readings[0].critical_celsius is None


def test_multiple_chips_are_all_read():

    text = (
        "k10temp-pci-00c3\n"
        "Adapter: PCI adapter\n"
        "temp1:        +70.5°C  (high = +70.0°C)\n"
        "                       (crit = +72.0°C, hyst = +70.0°C)\n"
        "\n"
        "acpitz-acpi-0\n"
        "Adapter: ACPI interface\n"
        "temp1:        +45.0°C\n"
    )

    readings = parse_sensors_output(text)

    assert [r.sensor for r in readings] == [
        "k10temp-pci-00c3/temp1",
        "acpitz-acpi-0/temp1",
    ]


def test_a_fan_line_between_two_temperature_lines_does_not_leak_into_either():
    """
    A top-level line always closes whatever reading was pending,
    whether or not the line itself turns out to be a temperature —
    otherwise an unrelated fan or voltage line sitting between two
    readings could be misread as a continuation of the first.
    """

    text = (
        "chip\n"
        "Adapter: Test adapter\n"
        "temp1:        +50.0°C  (high = +70.0°C)\n"
        "fan1:         1200 RPM\n"
        "temp2:        +55.0°C  (high = +75.0°C)\n"
    )

    readings = parse_sensors_output(text)

    assert len(readings) == 2
    assert readings[0].high_celsius == 70.0
    assert readings[1].high_celsius == 75.0

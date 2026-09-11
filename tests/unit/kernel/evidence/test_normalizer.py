"""
`Normalizer[TIn, TOut]` — J4, Evidence and Observation Foundation.
"""

from __future__ import annotations

import inspect

from aistack.kernel.evidence import Evidence
from aistack.kernel.evidence.conformance import normalizes_sensor_output
from aistack.providers.docker.log_normalization import normalize_log_evidence
from aistack.providers.host.sensors import parse_sensors_output


REAL_GIGABYTE_OUTPUT = (
    "k10temp-pci-00c3\n"
    "Adapter: PCI adapter\n"
    "temp1:        +70.5°C  (high = +70.0°C)\n"
    "                       (crit = +72.0°C, hyst = +70.0°C)\n"
)


def test_the_declared_sensor_normalizer_is_the_real_unmodified_function():
    assert normalizes_sensor_output is parse_sensors_output


def test_the_declared_sensor_normalizer_produces_evidence():
    """
    Calls the real, unmodified function through the name declared
    conformant in `kernel/evidence/conformance.py`, and checks the
    result against `Evidence` — the same fixture `test_sensors.py`
    already reads (`OPS-0004`'s captured GIGABYTE output), a second
    time, for a different claim: not "is this parsed correctly" but
    "is what comes out a governed `Evidence` reading."
    """

    readings = normalizes_sensor_output(REAL_GIGABYTE_OUTPUT)

    assert len(readings) == 1
    assert all(isinstance(reading, Evidence) for reading in readings)


def test_normalize_log_evidence_does_not_conform_it_requires_context():
    """
    Mutation guard for `Normalizer`'s own documented exception:
    `normalize_log_evidence` needs `subject`/`provider`/`state`/
    `depth`/`collected_at` beyond the raw text, which is exactly why
    it is not declared conformant in `conformance.py`.
    """

    parameters = inspect.signature(normalize_log_evidence).parameters

    required = {
        name
        for name, parameter in parameters.items()
        if parameter.default is inspect.Parameter.empty
    }

    assert required == {"raw", "subject", "provider", "state", "depth", "collected_at"}

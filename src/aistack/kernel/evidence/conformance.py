"""
Which real collectors and normalizers satisfy `Collector`/
`Normalizer`, stated as assignments `mypy src` — already a hard gate
of every patch — checks structurally at every run.

This is the proof `Collector`'s and `Normalizer`'s own docstrings
promise and `aistack.conformance.structural.satisfies` cannot give:
that check compares classes for a member named `__call__`, and none
of `DockerProvider`/`HostProvider` declare one. The claim these
three assignments make is narrower and real — *this bound method*,
*this function*, has the call shape the contract declares — and
`mypy` is the tool that can actually check a call shape rather than
a member name.

Two of `DockerProvider`'s own instance methods and `HostProvider`'s
one are collectors; `HostProvider.collect_temperatures`,
`normalize_log_evidence` and the three non-conforming
`DockerProvider` methods are named and explained on `Collector`/
`Normalizer` themselves rather than repeated here — this module
holds only what does conform, so that every name below is load-
bearing.
"""

from __future__ import annotations

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.kernel.evidence.collector import Collector
from aistack.kernel.evidence.normalizer import Normalizer
from aistack.providers.docker.provider import DockerProvider
from aistack.providers.host.provider import HostProvider
from aistack.providers.host.sensors import parse_sensors_output

_docker_provider = DockerProvider()
_host_provider = HostProvider()

# `DockerProvider.collect_cpu_readings`, bound — VS-4 4.1's own read.
collects_container_cpu: Collector[ContainerCpuReading] = (
    _docker_provider.collect_cpu_readings
)

# `HostProvider.collect_temperatures`, bound — OPS-0004's own read.
collects_temperatures: Collector[TemperatureReading] = (
    _host_provider.collect_temperatures
)

# `parse_sensors_output`, unbound — a pure function needs no instance.
normalizes_sensor_output: Normalizer[str, tuple[TemperatureReading, ...]] = (
    parse_sensors_output
)

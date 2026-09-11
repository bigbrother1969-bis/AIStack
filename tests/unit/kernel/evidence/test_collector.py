"""
`Collector[T]` — J4, Evidence and Observation Foundation.

`aistack.conformance.structural.satisfies` cannot verify this
Protocol (`Collector`'s own docstring explains why: it compares
classes for a `__call__` member, and neither `DockerProvider` nor
`HostProvider` declares one). `mypy src` is what actually checks the
two conforming assignments in `kernel/evidence/conformance.py`; what
follows here checks that those assignments are the real, unmodified
methods they claim to be, and pins the boundary of what does not
conform.
"""

from __future__ import annotations

import inspect

from aistack.kernel.evidence.conformance import (
    collects_container_cpu,
    collects_temperatures,
)
from aistack.providers.docker.provider import DockerProvider
from aistack.providers.host.provider import HostProvider


def test_the_declared_cpu_collector_is_the_real_unmodified_method():
    assert collects_container_cpu.__func__ is DockerProvider.collect_cpu_readings
    assert isinstance(collects_container_cpu.__self__, DockerProvider)


def test_the_declared_temperature_collector_is_the_real_unmodified_method():
    assert collects_temperatures.__func__ is HostProvider.collect_temperatures
    assert isinstance(collects_temperatures.__self__, HostProvider)


def test_collect_logs_does_not_conform_it_requires_three_arguments():
    """
    Mutation guard for `Collector`'s own documented exception: a
    signature change that dropped `collect_logs` to zero required
    arguments would make it eligible for this contract, silently,
    with nothing here to say so.
    """

    parameters = inspect.signature(DockerProvider.collect_logs).parameters

    assert list(parameters) == ["self", "subject", "depth", "state"]


def test_collect_process_does_not_conform_it_requires_a_container_name():
    parameters = inspect.signature(DockerProvider.collect_process).parameters

    assert list(parameters) == ["self", "container"]


def test_collect_commands_does_not_conform_it_returns_raw_pre_evidence_data():
    """
    `collect_commands` is zero-argument like a real `Collector`, so
    arity alone would not catch it drifting into this contract by
    accident — its return annotation is the fact that keeps it out:
    a mapping of raw strings, not a `Sequence[Evidence]`.
    """

    return_annotation = inspect.signature(
        DockerProvider.collect_commands
    ).return_annotation

    assert return_annotation == "dict[str, str]"

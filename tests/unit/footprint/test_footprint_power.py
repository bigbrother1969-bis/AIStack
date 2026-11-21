"""The GPU power read during a call: best effort, never in the way of a question."""

from __future__ import annotations

import subprocess
import time
from types import SimpleNamespace

import pytest

from aistack.footprint import power
from aistack.footprint.power import PowerSampler, read_gpu_watts


def smi(monkeypatch, output: str = "", code: int = 0, error: Exception | None = None):
    def run(*_args, **_kwargs):
        if error:
            raise error
        return SimpleNamespace(returncode=code, stdout=output)

    monkeypatch.setattr(power.subprocess, "run", run)


def test_the_power_of_one_card_is_read(monkeypatch):
    smi(monkeypatch, "33.57\n")

    assert read_gpu_watts() == 33.57


def test_the_power_of_several_cards_is_added(monkeypatch):
    smi(monkeypatch, "33.5\n12.25\n")

    assert read_gpu_watts() == 45.75


@pytest.mark.parametrize("output", ["[N/A]\n", "", "\n"])
def test_a_card_that_does_not_report_its_power_gives_nothing(monkeypatch, output):
    smi(monkeypatch, output)

    assert read_gpu_watts() is None


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("nvidia-smi", 3)])
def test_no_tool_or_a_slow_one_gives_nothing(monkeypatch, error):
    smi(monkeypatch, error=error)

    assert read_gpu_watts() is None


def test_a_failing_tool_gives_nothing(monkeypatch):
    smi(monkeypatch, "33.0\n", code=9)

    assert read_gpu_watts() is None


def test_the_mean_is_that_of_the_readings_made_during_the_call_not_the_one_made_on_entry():
    readings = iter([5.0, 100.0, 120.0, 110.0] + [110.0] * 1000)
    sampler = PowerSampler(reader=lambda: next(readings), every=0.01)

    with sampler:
        time.sleep(0.15)

    mean = sampler.mean()
    assert mean is not None and mean > 100  # the 5 W read on entry is not in it


def test_a_power_that_cannot_be_read_leaves_no_mean_and_starts_no_thread():
    sampler = PowerSampler(reader=lambda: None, every=0.01)

    with sampler:
        time.sleep(0.03)

    assert sampler.mean() is None
    assert sampler._thread is None


def test_a_call_too_short_for_a_reading_has_no_mean():
    sampler = PowerSampler(reader=lambda: 90.0, every=5.0)

    with sampler:
        pass

    assert sampler.mean() is None


def test_a_reader_that_fails_never_reaches_the_question():
    def broken() -> float:
        raise RuntimeError("driver gone")

    sampler = PowerSampler(reader=broken, every=0.01)

    with sampler:
        time.sleep(0.03)

    assert sampler.mean() is None

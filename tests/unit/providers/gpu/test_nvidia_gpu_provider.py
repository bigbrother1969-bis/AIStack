import subprocess
from unittest.mock import patch

from aistack.providers.gpu.provider import NvidiaGpuProvider

REAL_CSV_LINE = "Quadro P400, 1, 142, 2048, 49\n"


def run(returncode: int = 0, stdout: str = "", raises: bool = False):
    if raises:

        def _raise(*args, **kwargs):
            raise OSError("nvidia-smi not found")

        return patch("subprocess.run", side_effect=_raise)

    return patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=""
        ),
    )


def test_no_nvidia_smi_binary_returns_no_readings():
    with run(raises=True):
        readings = NvidiaGpuProvider().collect_readings()

    assert readings == ()


def test_a_nonzero_return_code_returns_no_readings():
    with run(returncode=1, stdout=""):
        readings = NvidiaGpuProvider().collect_readings()

    assert readings == ()


def test_a_real_csv_line_is_parsed():
    with run(stdout=REAL_CSV_LINE):
        readings = NvidiaGpuProvider().collect_readings()

    assert len(readings) == 1
    reading = readings[0]
    assert reading.name == "Quadro P400"
    assert reading.utilization_percent == 1.0
    assert reading.memory_used_mib == 142.0
    assert reading.memory_total_mib == 2048.0
    assert reading.temperature_celsius == 49.0


def test_several_gpus_are_all_parsed():
    with run(stdout=REAL_CSV_LINE + "Tesla T4, 5, 512, 16384, 55\n"):
        readings = NvidiaGpuProvider().collect_readings()

    assert {reading.name for reading in readings} == {"Quadro P400", "Tesla T4"}


def test_blank_lines_are_skipped():
    with run(stdout=f"\n{REAL_CSV_LINE}\n"):
        readings = NvidiaGpuProvider().collect_readings()

    assert len(readings) == 1


def test_a_malformed_line_is_skipped_not_raised_on():
    with run(stdout="not, enough, fields\n"):
        readings = NvidiaGpuProvider().collect_readings()

    assert readings == ()


def test_an_na_field_is_skipped_not_raised_on():
    """
    The exact failure mode this hardware produces for `power.draw` —
    not queried here, but the same `[N/A]`-shaped text could appear in
    any field on other hardware, and this provider must not crash on
    it.
    """

    with run(stdout="Quadro P400, [N/A], 142, 2048, 49\n"):
        readings = NvidiaGpuProvider().collect_readings()

    assert readings == ()


def test_the_provider_declares_its_identity():
    assert NvidiaGpuProvider.provider_id == "aistack.provider.gpu.nvidia"

from pathlib import Path

from aistack.providers.gpu import gpu_thresholds_for_host


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_missing_definition_is_reported(tmp_path: Path):
    thresholds, note = gpu_thresholds_for_host(tmp_path / "absent.yml", "GIGABYTE")

    assert thresholds == ()
    assert "no GPU-threshold definition at" in note


def test_an_unreadable_definition_is_reported(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "hosts: [not, valid,\n")

    thresholds, note = gpu_thresholds_for_host(path, "GIGABYTE")

    assert thresholds == ()
    assert "GPU-threshold definition not readable" in note


def test_a_host_with_nothing_declared_is_reported(tmp_path: Path):
    path = write(
        tmp_path / "gpu_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - kind: temperature_celsius
                celsius: 80
        """,
    )

    thresholds, note = gpu_thresholds_for_host(path, "raspberry")

    assert thresholds == ()
    assert "no GPU thresholds declared for host 'raspberry' in" in note


def test_a_hosts_declared_thresholds_are_returned(tmp_path: Path):
    path = write(
        tmp_path / "gpu_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - kind: temperature_celsius
                celsius: 80
              - kind: utilization_percent
                percent: 90
              - kind: memory_percent
                percent: 90
        """,
    )

    thresholds, note = gpu_thresholds_for_host(path, "GIGABYTE")

    assert note == ""
    assert len(thresholds) == 3

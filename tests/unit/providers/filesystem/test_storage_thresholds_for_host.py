from pathlib import Path

from aistack.providers.filesystem import storage_thresholds_for_host


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_missing_definition_is_reported(tmp_path: Path):
    thresholds, note = storage_thresholds_for_host(
        tmp_path / "absent.yml", "gigabyte"
    )

    assert thresholds == ()
    assert "no storage-threshold definition at" in note


def test_an_unreadable_definition_is_reported(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "hosts: [not, valid,\n")

    thresholds, note = storage_thresholds_for_host(path, "gigabyte")

    assert thresholds == ()
    assert "storage-threshold definition not readable" in note


def test_a_host_with_nothing_declared_is_reported(tmp_path: Path):
    path = write(
        tmp_path / "storage_thresholds.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /
                kind: free_bytes
                free_gb: 20
        """,
    )

    thresholds, note = storage_thresholds_for_host(path, "raspberry")

    assert thresholds == ()
    assert (
        "no storage thresholds declared for host 'raspberry' in" in note
    )


def test_a_hosts_declared_thresholds_are_returned(tmp_path: Path):
    path = write(
        tmp_path / "storage_thresholds.yml",
        """
        hosts:
          - host: gigabyte
            thresholds:
              - mount: /
                kind: free_bytes
                free_gb: 20
          - host: raspberry
            thresholds:
              - mount: /
                kind: free_bytes
                free_gb: 2
        """,
    )

    thresholds, note = storage_thresholds_for_host(path, "gigabyte")

    assert note == ""
    assert len(thresholds) == 1
    assert thresholds[0].mount == "/"
    assert thresholds[0].value == 20 * 1024**3

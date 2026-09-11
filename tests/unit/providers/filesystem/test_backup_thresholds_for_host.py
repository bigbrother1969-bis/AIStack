from pathlib import Path

from aistack.providers.filesystem import backup_thresholds_for_host


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_missing_definition_is_reported(tmp_path: Path):
    thresholds, note = backup_thresholds_for_host(tmp_path / "absent.yml", "GIGABYTE")

    assert thresholds == ()
    assert "no backup-threshold definition at" in note


def test_an_unreadable_definition_is_reported(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "hosts: [not, valid,\n")

    thresholds, note = backup_thresholds_for_host(path, "GIGABYTE")

    assert thresholds == ()
    assert "backup-threshold definition not readable" in note


def test_a_host_with_nothing_declared_is_reported(tmp_path: Path):
    path = write(
        tmp_path / "backup_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - path: /media/BACKUP/wordpress/
                max_age_days: 7
        """,
    )

    thresholds, note = backup_thresholds_for_host(path, "raspberry")

    assert thresholds == ()
    assert "no backup thresholds declared for host 'raspberry' in" in note


def test_a_hosts_declared_thresholds_are_returned(tmp_path: Path):
    path = write(
        tmp_path / "backup_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - path: /media/BACKUP/wordpress/
                max_age_days: 7
        """,
    )

    thresholds, note = backup_thresholds_for_host(path, "GIGABYTE")

    assert note == ""
    assert len(thresholds) == 1
    assert thresholds[0].path == "/media/BACKUP/wordpress/"
    assert thresholds[0].max_age_hours == 7 * 24

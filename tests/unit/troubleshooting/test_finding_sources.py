"""Where the troubleshooting assistant reads the last network discovery (UAT, 2026-10-09)."""

from __future__ import annotations

from pathlib import Path

from aistack.troubleshooting import findings


def test_the_data_directory_of_the_working_directory_comes_first(tmp_path: Path, monkeypatch):
    observation = tmp_path / "reports" / "generated" / "network-docker-observation.json"
    observation.parent.mkdir(parents=True)
    observation.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert findings.FindingSources().network_docker_observation == observation


def test_without_one_the_checkout_is_read(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert findings.FindingSources().network_docker_observation == (
        findings.REPOSITORY_ROOT / "reports" / "generated" / "network-docker-observation.json"
    )

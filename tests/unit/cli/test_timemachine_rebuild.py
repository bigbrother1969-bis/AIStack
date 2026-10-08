from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

ROOT = Path(__file__).parents[3]


def _run(cwd: Path, *args: str) -> str:
    # The hosts the rebuild reads: only under the test's own data
    # directory — the shipped `hosts.yml` names the Raspberry by an
    # absolute path, which exists on the reference host (1.11).
    config = cwd / "test-config"
    config.mkdir(exist_ok=True)
    (config / "hosts.yml").write_text("hosts:\n  gigabyte:\n    directory: hosts/gigabyte\n")
    result = subprocess.run(
        [sys.executable, "-m", "aistack.cli.timemachine_rebuild", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin", "AISTACK_CONFIG_DIR": str(config)},
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_rebuild_reports_what_it_projected(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    write_artifact_with_history(
        '{"provider": {"id": "aistack.provider.docker"}}',
        generated_dir / "docker-observation.json",
    )

    output = _run(tmp_path, str(generated_dir))

    assert "Time Machine Projection" in output
    assert f"- Source: {generated_dir}" in output
    assert f"- Store: {generated_dir / 'timemachine' / 'graph'}" in output
    assert "- Streams seen: 1" in output
    assert "- Observations seen: 1" in output
    assert "- Facts written: 4" in output
    assert "- Facts dropped: 0" in output


def test_rebuild_reports_a_recorded_image_digest_observation(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    from aistack.providers.docker.digest_history import record_image_digest

    record_image_digest(
        "arrstack/gluetun", "sha256:image-digest-1", generated_dir=generated_dir
    )

    output = _run(tmp_path, str(generated_dir))

    assert "- Docker-digest subjects seen: 1" in output
    assert "- Docker-digest observations seen: 1" in output


def test_rebuild_reports_a_recorded_package_inventory_observation(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    from aistack.providers.docker.packages_history import record_package_inventory

    record_package_inventory(
        "arrstack/gluetun",
        "dpkg",
        [{"name": "curl", "version": "7.88.1-10"}],
        generated_dir=generated_dir,
    )

    output = _run(tmp_path, str(generated_dir))

    assert "- Docker-packages subjects seen: 1" in output
    assert "- Docker-packages observations seen: 1" in output


def test_rebuild_creates_the_store_directory_on_disk(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    write_artifact_with_history("{}", generated_dir / "some-stream.json")

    _run(tmp_path, str(generated_dir))

    assert (generated_dir / "timemachine" / "graph").is_dir()


def test_rebuild_is_a_no_op_on_an_empty_generated_dir(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    output = _run(tmp_path, str(generated_dir))

    assert "- Streams seen: 0" in output
    assert "- Facts written: 0" in output
    assert "- Docker-diff subjects seen: 0" in output
    assert "- Docker-diff snapshots seen: 0" in output
    assert "- Docker-digest subjects seen: 0" in output
    assert "- Docker-digest observations seen: 0" in output
    assert "- Docker-packages subjects seen: 0" in output
    assert "- Docker-packages observations seen: 0" in output
    assert "- Upgrade-correlation subjects seen: 0" in output
    assert "- Digest changes seen: 0" in output
    assert "- Upgrade correlations written: 0" in output
    assert "- Collection-gap streams seen: 0" in output
    assert "- Collection gaps seen: 0" in output


def test_rebuild_reports_a_recorded_collection_gap(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    from aistack.generators.collection_gap import record_collection_gap
    from datetime import datetime, timezone

    record_collection_gap(
        "docker-events",
        checkpoint_until="2026-09-28T10:00:00+00:00",
        now=datetime(2026, 9, 28, 10, 5, 0, tzinfo=timezone.utc),
        generated_dir=generated_dir,
    )

    output = _run(tmp_path, str(generated_dir))

    assert "- Collection-gap streams seen: 1" in output
    assert "- Collection gaps seen: 1" in output


def test_rebuild_reports_an_upgrade_correlation(tmp_path: Path, monkeypatch):
    generated_dir = tmp_path / "reports" / "generated"
    import aistack.generators.history as history_module

    from aistack.providers.docker.digest_history import record_image_digest
    from aistack.providers.docker.packages_history import record_package_inventory

    def _at(hour: int) -> type:
        class Frozen(history_module.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 28, hour, 0, 0, tzinfo=tz)

        return Frozen

    monkeypatch.setattr(history_module, "datetime", _at(8))
    record_image_digest("arrstack/gluetun", "sha256:aaa", generated_dir=generated_dir)
    monkeypatch.setattr(history_module, "datetime", _at(9))
    record_package_inventory(
        "arrstack/gluetun",
        "dpkg",
        [{"name": "curl", "version": "7.88.1-10"}],
        generated_dir=generated_dir,
    )
    monkeypatch.setattr(history_module, "datetime", _at(10))
    record_image_digest("arrstack/gluetun", "sha256:bbb", generated_dir=generated_dir)
    monkeypatch.setattr(history_module, "datetime", _at(11))
    record_package_inventory(
        "arrstack/gluetun",
        "dpkg",
        [{"name": "curl", "version": "7.90.0-1"}],
        generated_dir=generated_dir,
    )

    output = _run(tmp_path, str(generated_dir))

    assert "- Upgrade-correlation subjects seen: 1" in output
    assert "- Digest changes seen: 1" in output
    assert "- Upgrade correlations written: 1" in output


def test_rebuild_reports_a_recorded_docker_diff_snapshot(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    from aistack.providers.docker.diff_history import record_docker_diff

    record_docker_diff(
        "arrstack/gluetun",
        [{"kind": "A", "path": "/run/nginx.pid"}],
        generated_dir=generated_dir,
    )

    output = _run(tmp_path, str(generated_dir))

    assert "- Docker-diff subjects seen: 1" in output
    assert "- Docker-diff snapshots seen: 1" in output

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from aistack.cli.docker_digest_monitor import (
    USAGE,
    load_checkpoint,
    log_cycle,
    main,
    parse,
    run_cycle,
    save_checkpoint,
)

INSPECT_ENTRY = {
    "Id": "abc123",
    "Name": "/frigate",
    "Config": {"Labels": {}},
    "Mounts": [],
    "Image": "sha256:image-digest-1",
}


def _docker(ps_stdout: str = "", inspect_stdout: str = "[]"):
    def _fake_run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=ps_stdout, stderr="")
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=inspect_stdout, stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout='["frigate@sha256:repo-digest-1"]\n', stderr=""
            )
        raise AssertionError(f"unexpected call: {args}")

    return patch("subprocess.run", side_effect=_fake_run)


def test_parse_defaults():
    checkpoint_path, generated_dir, once, dry_run = parse([])

    assert checkpoint_path.name == "checkpoint.json"
    assert generated_dir == Path("reports/generated")
    assert once is False
    assert dry_run is False


def test_parse_accepts_checkpoint_and_generated_dir_overrides():
    checkpoint_path, generated_dir, _, _ = parse(
        ["--checkpoint", "/tmp/cp.json", "--generated-dir", "/tmp/generated"]
    )

    assert checkpoint_path == Path("/tmp/cp.json")
    assert generated_dir == Path("/tmp/generated")


def test_parse_accepts_once_and_dry_run_together():
    _, _, once, dry_run = parse(["--once", "--dry-run"])

    assert once is True
    assert dry_run is True


def test_parse_prints_usage_and_exits_on_help():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--help"])

    assert excinfo.value.code == 0


def test_parse_rejects_an_unknown_argument():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--nonsense"])

    assert excinfo.value.code == 2


def test_usage_names_every_flag_parse_accepts():
    for flag in ("--checkpoint", "--generated-dir", "--once", "--dry-run"):
        assert flag in USAGE


def test_load_checkpoint_is_none_when_the_file_does_not_exist(tmp_path: Path):
    assert load_checkpoint(tmp_path / "missing.json") is None


def test_load_checkpoint_is_none_on_corrupted_content(tmp_path: Path):
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text("not json", encoding="utf-8")

    assert load_checkpoint(checkpoint_path) is None


def test_save_and_load_checkpoint_round_trips(tmp_path: Path):
    checkpoint_path = tmp_path / "checkpoint.json"

    save_checkpoint(checkpoint_path, "2026-09-28T10:00:10+00:00")

    assert load_checkpoint(checkpoint_path) == "2026-09-28T10:00:10+00:00"


def test_log_cycle_is_silent_when_nothing_changed(capsys):
    log_cycle([])

    assert capsys.readouterr().out == ""


def test_log_cycle_prints_changed_subjects(capsys):
    log_cycle([{"subject": "arrstack/gluetun", "digest": "sha256:x"}])

    out = capsys.readouterr().out
    assert "changed=1" in out
    assert "arrstack/gluetun" in out


def test_log_cycle_with_the_check_label_prints_even_with_nothing_changed(capsys):
    log_cycle([], label="check")

    out = capsys.readouterr().out
    assert "check" in out
    assert "changed=0" in out


def test_log_cycle_always_prints_a_labelled_line(capsys):
    log_cycle([], label="stopping")

    assert "stopping" in capsys.readouterr().out


def test_run_cycle_records_a_changed_subject_and_advances_the_checkpoint(tmp_path: Path):
    generated_dir = tmp_path
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 10, tzinfo=timezone.utc)

    with _docker(ps_stdout="frigate\n", inspect_stdout=json.dumps([INSPECT_ENTRY])):
        changed = run_cycle(generated_dir, checkpoint_path, dry_run=False, now=now)

    assert changed == [{"subject": "frigate", "digest": "sha256:image-digest-1"}]
    recorded = generated_dir / "docker-digest" / "frigate" / "docker-digest.json"
    assert json.loads(recorded.read_text())["repo_digests"] == ["frigate@sha256:repo-digest-1"]
    remembered = generated_dir / "docker-digest" / "frigate" / "registry-digests.json"
    assert json.loads(remembered.read_text()) == {"sha256:image-digest-1": ["frigate@sha256:repo-digest-1"]}
    assert load_checkpoint(checkpoint_path) == now.isoformat()


def test_run_cycle_checkpoint_advances_even_on_a_quiet_cycle(tmp_path: Path):
    generated_dir = tmp_path
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 10, tzinfo=timezone.utc)

    with _docker():
        run_cycle(generated_dir, checkpoint_path, dry_run=False, now=now)

    assert load_checkpoint(checkpoint_path) == now.isoformat()


def test_run_cycle_does_not_record_an_unchanged_subject_twice(tmp_path: Path):
    generated_dir = tmp_path
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 10, tzinfo=timezone.utc)

    with _docker(ps_stdout="frigate\n", inspect_stdout=json.dumps([INSPECT_ENTRY])):
        run_cycle(generated_dir, checkpoint_path, dry_run=False, now=now)
        second = run_cycle(generated_dir, checkpoint_path, dry_run=False, now=now)

    assert second == []


def test_dry_run_reports_without_writing_or_advancing_the_checkpoint(tmp_path: Path):
    generated_dir = tmp_path
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 10, tzinfo=timezone.utc)

    with _docker(ps_stdout="frigate\n", inspect_stdout=json.dumps([INSPECT_ENTRY])):
        changed = run_cycle(generated_dir, checkpoint_path, dry_run=True, now=now)

    assert changed == [{"subject": "frigate", "digest": "sha256:image-digest-1"}]
    assert not (generated_dir / "docker-digest").exists()
    assert load_checkpoint(checkpoint_path) is None


def _main_args(tmp_path: Path) -> list[str]:
    return [
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--generated-dir", str(tmp_path),
        "--once",
    ]


def test_main_first_run_ever_records_no_gap(tmp_path: Path):
    with _docker():
        main(_main_args(tmp_path))

    assert not (tmp_path / "collection-gaps").exists()


def test_main_records_a_gap_on_restart_after_a_checkpoint(tmp_path: Path):
    checkpoint_path = tmp_path / "checkpoint.json"
    save_checkpoint(checkpoint_path, "2026-09-28T10:00:00+00:00")

    with _docker():
        main(_main_args(tmp_path))

    gap_path = tmp_path / "collection-gaps" / "docker-digest" / "collection-gap.json"
    assert gap_path.exists()
    written = json.loads(gap_path.read_text(encoding="utf-8"))
    assert written == {"stream": "docker-digest", "start": "2026-09-28T10:00:00+00:00"}


def test_main_dry_run_records_no_gap_even_after_a_checkpoint(tmp_path: Path):
    checkpoint_path = tmp_path / "checkpoint.json"
    save_checkpoint(checkpoint_path, "2026-09-28T10:00:00+00:00")

    with _docker():
        main(_main_args(tmp_path) + ["--dry-run"])

    assert not (tmp_path / "collection-gaps").exists()

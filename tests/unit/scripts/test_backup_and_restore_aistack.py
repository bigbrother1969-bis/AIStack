"""scripts/backup_aistack.sh and scripts/restore_aistack.sh (OPS-0010, 1.9):
AIStack's own backup, hot, and its restore into a new directory."""

from __future__ import annotations

import os
import shutil
import sqlite3
import stat
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _installation(tmp_path: Path) -> Path:
    root = tmp_path / "AIStack"
    (root / "scripts").mkdir(parents=True)
    for name in ("backup_aistack.sh", "restore_aistack.sh"):
        shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
    (root / "config").mkdir()
    (root / "config" / "pra_tests.yml").write_text("services: []\n", encoding="utf-8")
    (root / ".env").write_text("AISTACK_VERSION=dev\nAISTACK_DATA_DIR=./data\n", encoding="utf-8")
    (root / ".env.web").write_text("AISTACK_OIDC_CLIENT_SECRET=not-a-real-one\n", encoding="utf-8")
    data = root / "data"
    (data / "web").mkdir(parents=True)
    (data / "timemachine" / "graph").mkdir(parents=True)
    (data / "timemachine" / "graph" / "store").write_text("rebuilt, never saved", encoding="utf-8")
    (data / "explications" / "history" / "kernel").mkdir(parents=True)
    (data / "explications" / "history" / "kernel" / "2026-10-05T09-00-00Z.json").write_text("{}", encoding="utf-8")
    database = sqlite3.connect(data / "web" / "sessions.sqlite3")
    database.execute("CREATE TABLE sessions (id TEXT)")
    database.execute("INSERT INTO sessions VALUES ('one')")
    database.commit()
    database.close()
    return root


def _run(*command: str | Path, **environment: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        capture_output=True,
        text=True,
        env={**os.environ, **environment},
    )


def test_a_backup_holds_data_declarations_and_environment_but_not_the_graph(tmp_path: Path):
    root = _installation(tmp_path)
    destination = tmp_path / "BACKUP" / "AIStack"

    result = _run(root / "scripts" / "backup_aistack.sh", AISTACK_BACKUP_DIR=str(destination))

    assert result.returncode == 0, result.stderr
    (archive,) = destination.glob("aistack-*.tar.gz")
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    with tarfile.open(archive) as opened:
        names = set(opened.getnames())
    assert "data/explications/history/kernel/2026-10-05T09-00-00Z.json" in names
    assert "config/pra_tests.yml" in names
    assert {"env/.env", "env/.env.web", "MANIFEST", "sessions.sqlite3"} <= names
    assert not any(name.startswith("data/timemachine/graph/") for name in names)
    assert "data/web/sessions.sqlite3" not in names


def test_a_restore_goes_into_a_new_directory_and_checks_what_it_restored(tmp_path: Path):
    root = _installation(tmp_path)
    destination = tmp_path / "backup"
    _run(root / "scripts" / "backup_aistack.sh", AISTACK_BACKUP_DIR=str(destination))
    (archive,) = destination.glob("aistack-*.tar.gz")
    target = tmp_path / "restored"

    result = _run(root / "scripts" / "restore_aistack.sh", archive, target)

    assert result.returncode == 0, result.stderr
    assert "sessions database: ok" in result.stdout
    assert "explications: 1 file(s), 0 unreadable" in result.stdout
    assert "timemachine_rebuild" in result.stdout
    restored = sqlite3.connect(target / "data" / "web" / "sessions.sqlite3")
    assert restored.execute("SELECT id FROM sessions").fetchall() == [("one",)]

    again = _run(root / "scripts" / "restore_aistack.sh", archive, target)
    assert again.returncode == 1
    assert "restore into a new directory" in again.stderr

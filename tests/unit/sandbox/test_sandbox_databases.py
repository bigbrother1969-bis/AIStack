from __future__ import annotations

import hashlib
import itertools
from collections.abc import Sequence
from pathlib import Path

import pytest

from aistack.cli import sandbox as cli
from aistack.sandbox.declaration import FileSample, SandboxDeclaration, SandboxRecipe, load_sandbox_declaration
from aistack.sandbox.run import LABEL, CommandResult

PHOTO = b"a photo"


class FakeDocker:
    def __init__(self, *, checksum: str | None = None, external: int = 2) -> None:
        self.calls: list[list[str]] = []
        self.checksum = checksum or hashlib.sha1(PHOTO).hexdigest()  # noqa: S324
        self.external = external

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if args[0] == "inspect" and "{{.Image}} {{.Config.Image}}" in args:
            return CommandResult(0, f"sha256:db {args[-1]}:image\n")
        if args[0] == "inspect" and "{{json .Config.Cmd}}" in args:
            return CommandResult(0, '["postgres","-c","shared_preload_libraries=vchord.so"]\n' if "postgres" in args[-1] else "null\n")
        if args[0] == "inspect":
            return CommandResult(0, "true\n")
        if args[0] == "exec":
            query = args[-1]
            if "SELECT 1" in query:
                return CommandResult(0, "1\n")
            if "information_schema.tables WHERE table_schema='nextcloud' AND" in query:
                return CommandResult(0, "oc_appconfig\n")
            if "table_name IN ('asset', 'assets')" in query:
                return CommandResult(0, "asset\n")
            if "table_name IN ('user', 'users')" in query:
                return CommandResult(0, "user\n")
            if "installedat" in query:
                return CommandResult(0, "1690000000\n")
            if "encode(checksum" in query:
                return CommandResult(0, f"/external/photos/2024/a.jpg|{self.checksum}\n/external/photos/2024/b.jpg|{self.checksum}\n")
            if "LIKE '/external/photos/%'" in query:
                return CommandResult(0, f"{self.external}\n")
            if '"asset"' in query:
                return CommandResult(0, "5\n")
            return CommandResult(0, "7\n")
        if args[0] in ("ps",) or args[:2] == ["network", "ls"]:
            return CommandResult(0, "")
        return CommandResult(0)


class FakeHost:
    def __init__(self, *, old_duplicity: bool = False, missing: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.old_duplicity = old_duplicity
        self.missing = missing

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if self.old_duplicity and "--path-to-restore" in args:
            return CommandResult(2, "", "duplicity: error: no such option: --path-to-restore\n")
        if self.missing:
            return CommandResult(11, "", "File media/Multimedia/Photos/2024/a.jpg not found in archive\n")
        Path(args[-1]).write_bytes(PHOTO)
        return CommandResult(0)


def _dumps(tmp_path: Path, name: str) -> Path:
    directory = tmp_path / name
    directory.mkdir()
    (directory / f"{name}-2026-10-07-022009.sql.gz").write_bytes(b"old")
    (directory / f"{name}-2026-10-08-022045.sql.gz").write_bytes(b"dump")
    return directory


def _declaration(tmp_path: Path, recipe: SandboxRecipe) -> SandboxDeclaration:
    return SandboxDeclaration(run_root=tmp_path / "sandbox", margin_gib=0, expansion=4, recipes={recipe.name: recipe})


def _nextcloud(tmp_path: Path) -> SandboxDeclaration:
    return _declaration(tmp_path, SandboxRecipe(
        name="nextcloud", kind="nextcloud_mariadb", backup_dir=_dumps(tmp_path, "nextcloud"),
        database_dump="nextcloud-*.sql.gz", live_database_container="nc_db", database_timeout_seconds=30,
        not_backed_up="les fichiers n'ont pas de sauvegarde",
    ))


def _immich(tmp_path: Path) -> SandboxDeclaration:
    return _declaration(tmp_path, SandboxRecipe(
        name="immich", kind="immich_postgres", backup_dir=_dumps(tmp_path, "immich"),
        database_dump="immich-*.sql.gz", live_database_container="immich_postgres", database_timeout_seconds=30,
        file_sample=FileSample(live_prefix="/external/photos/", host_prefix="/media/Multimedia/Photos/",
                               duplicity_target=Path("/media/BACKUP/GIGABYTE_DAILY"), count=2),
        not_backed_up="les photos téléversées n'ont pas de sauvegarde",
    ))


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = itertools.count(0, 2)
    monkeypatch.setattr("aistack.sandbox.run.time.monotonic", lambda: float(next(ticks)))
    monkeypatch.setattr("aistack.sandbox.nextcloud.time.sleep", lambda seconds: None)
    monkeypatch.setattr("aistack.sandbox.immich.time.sleep", lambda seconds: None)


def _restore(name: str, declaration: SandboxDeclaration, tmp_path: Path, docker: FakeDocker, host: FakeHost | None = None):
    return cli.restore(name, declaration, tmp_path / "data", docker, host or FakeHost())

def test_nextcloud_database_is_restored_and_says_its_files_have_no_backup(tmp_path: Path):
    docker = FakeDocker()
    run, _ = _restore("nextcloud", _nextcloud(tmp_path), tmp_path, docker)

    assert run.succeeded, run.failure
    assert run.facts["backup"]["database_dump"].endswith("nextcloud-2026-10-08-022045.sql.gz")
    assert run.facts["database"]["table_prefix"] == "oc_"
    (files,) = [check for check in run.checks if check.name == "files backed up"]
    assert not files.ok and not files.required and "pas de sauvegarde" in files.observed
    (db,) = [c for c in docker.calls if c[0] == "run" and "-d" in c]
    assert any(arg.endswith(":/docker-entrypoint-initdb.d/restore.sql.gz:ro") for arg in db)
    assert f"{LABEL}={run.run_id}" in db and db[db.index("--network") + 1] == run.network
    assert not run.directory.exists()


def test_immich_database_is_restored_with_the_live_command_and_photos_match(tmp_path: Path):
    docker = FakeDocker()
    host = FakeHost()
    run, _ = _restore("immich", _immich(tmp_path), tmp_path, docker, host)

    assert run.succeeded, run.failure
    (db,) = [c for c in docker.calls if c[0] == "run" and "-d" in c]
    assert db[-3:] == ["postgres", "-c", "shared_preload_libraries=vchord.so"]
    (sample,) = [c for c in run.checks if c.name == "photos from Deja Dup match the database"]
    assert sample.ok and sample.observed.startswith("2/2")
    assert host.calls[0][:2] == ["duplicity", "restore"]
    assert "media/Multimedia/Photos/2024/a.jpg" in host.calls[0]
    assert "file:///media/BACKUP/GIGABYTE_DAILY" in host.calls[0]
    assert run.facts["database"]["uploaded_assets"] == 3
    assert "3 asset(s)" in run.facts["not_backed_up"]


def test_a_photo_whose_checksum_differs_fails_the_test(tmp_path: Path):
    run, _ = _restore("immich", _immich(tmp_path), tmp_path, FakeDocker(checksum="0" * 40))

    assert not run.succeeded
    (sample,) = [c for c in run.checks if c.name == "photos from Deja Dup match the database"]
    assert "checksum differs" in sample.observed


def test_a_photo_missing_from_the_backup_is_named(tmp_path: Path):
    run, _ = _restore("immich", _immich(tmp_path), tmp_path, FakeDocker(), FakeHost(missing=True))

    (sample,) = [c for c in run.checks if c.name == "photos from Deja Dup match the database"]
    assert not sample.ok and "not found in archive" in sample.observed


def test_an_older_duplicity_is_asked_with_its_own_option(tmp_path: Path):
    host = FakeHost(old_duplicity=True)
    run, _ = _restore("immich", _immich(tmp_path), tmp_path, FakeDocker(), host)

    assert "--file-to-restore" in host.calls[1]


def test_no_external_photo_means_no_sample_is_required(tmp_path: Path):
    run, _ = _restore("immich", _immich(tmp_path), tmp_path, FakeDocker(external=0), FakeHost(missing=True))

    assert run.succeeded, run.failure


def test_the_shipped_declaration_knows_nextcloud_and_immich():
    recipes = load_sandbox_declaration().recipes
    assert recipes["nextcloud"].kind == "nextcloud_mariadb"
    assert recipes["immich"].file_sample is not None
    assert recipes["immich"].file_sample.host_prefix == "/media/Multimedia/Photos/"
    assert recipes["immich"].not_backed_up

from __future__ import annotations

import itertools
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from aistack.cli import sandbox as cli
from aistack.sandbox.declaration import SandboxDeclaration, SandboxRecipe
from aistack.sandbox.rollback import PreviousImage, _repository, pin_instructions
from aistack.sandbox.run import CommandResult

LIVE = "sha256:new"
EARLIER = "sha256:old"


class FakeDocker:
    """A Nextcloud database container, upgraded once."""

    def __init__(self, *, earlier_on_host: bool = True, pull_fails: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.earlier_on_host = earlier_on_host
        self.pull_fails = pull_fails

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if args[0] == "inspect" and "com.docker.compose.project" in args[2]:
            return CommandResult(0, f"{LIVE}|mariadb:11|nextcloud|db|/srv/nextcloud|/srv/nextcloud/docker-compose.yml\n")
        if args[0] == "inspect" and "{{.Image}} {{.Config.Image}}" in args:
            return CommandResult(0, f"{LIVE} mariadb:11\n")
        if args[0] == "inspect" and "{{json .Config.Cmd}}" in args:
            return CommandResult(0, "null\n")
        if args[0] == "inspect":
            return CommandResult(0, "true\n")
        if args[:2] == ["image", "inspect"]:
            return CommandResult(0 if self.earlier_on_host else 1, "")
        if args[0] == "pull":
            return CommandResult(1, "", "manifest unknown\n") if self.pull_fails else CommandResult(0)
        if args[0] == "exec":
            query = args[-1]
            if "SELECT 1" in query:
                return CommandResult(0, "1\n")
            if "LIKE '%appconfig'" in query:
                return CommandResult(0, "oc_appconfig\n")
            return CommandResult(0, "7\n")
        if args[0] == "ps" or args[:2] == ["network", "ls"]:
            return CommandResult(0, "")
        return CommandResult(0)


def _history(generated: Path, records: list[dict]) -> None:
    directory = generated / "docker-digest" / "nextcloud" / "db" / "history" / "docker-digest"
    directory.mkdir(parents=True)
    for index, record in enumerate(records):
        (directory / f"2026-10-0{index + 1}T02-00-00Z.json").write_text(json.dumps(record), encoding="utf-8")


def _declaration(tmp_path: Path) -> SandboxDeclaration:
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    (dumps / "nextcloud-2026-10-08.sql.gz").write_bytes(b"dump")
    recipe = SandboxRecipe(
        name="nextcloud", kind="nextcloud_mariadb", backup_dir=dumps, database_dump="nextcloud-*.sql.gz",
        live_database_container="nc_db", database_timeout_seconds=30,
    )
    return SandboxDeclaration(run_root=tmp_path / "sandbox", margin_gib=0, expansion=4, recipes={"nextcloud": recipe})


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = itertools.count(0, 2)
    monkeypatch.setattr("aistack.sandbox.run.time.monotonic", lambda: float(next(ticks)))
    monkeypatch.setattr("aistack.sandbox.nextcloud.time.sleep", lambda seconds: None)


def _rollback(tmp_path: Path, docker: FakeDocker, **kwargs):
    return cli.restore("nextcloud", _declaration(tmp_path), tmp_path / "data", docker, rollback=True, **kwargs)


def test_the_earlier_image_is_rehearsed_and_the_pin_is_printed(tmp_path: Path):
    _history(tmp_path / "data", [
        {"subject": "nextcloud/db", "digest": EARLIER, "image": "mariadb:11",
         "repo_digests": ["mariadb@sha256:aaa"]},
        {"subject": "nextcloud/db", "digest": LIVE},
    ])
    docker = FakeDocker()

    run, _ = _rollback(tmp_path, docker)

    assert run.succeeded, run.failure
    (db,) = [c for c in docker.calls if c[0] == "run" and "-d" in c]
    assert db[-1] == EARLIER
    assert run.proposed_entry() == ""
    text = cli.summary(run)
    assert text.startswith("Répétition du retour arrière")
    assert "image: mariadb@sha256:aaa" in text
    assert "cd /srv/nextcloud && docker compose up -d db" in text
    assert not [c for c in docker.calls if c[0] == "pull"]


def test_an_earlier_image_gone_from_the_host_is_pulled_by_its_registry_digest(tmp_path: Path):
    _history(tmp_path / "data", [
        {"subject": "nextcloud/db", "digest": EARLIER, "repo_digests": ["mariadb@sha256:aaa"]},
        {"subject": "nextcloud/db", "digest": LIVE},
    ])
    docker = FakeDocker(earlier_on_host=False)

    run, _ = _rollback(tmp_path, docker)

    assert ["pull", "mariadb@sha256:aaa"] in docker.calls
    (db,) = [c for c in docker.calls if c[0] == "run" and "-d" in c]
    assert db[-1] == "mariadb@sha256:aaa"
    assert run.succeeded


def test_an_earlier_image_gone_and_never_given_a_registry_digest_is_said_so(tmp_path: Path):
    _history(tmp_path / "data", [{"subject": "nextcloud/db", "digest": EARLIER}, {"subject": "nextcloud/db", "digest": LIVE}])

    run, _ = _rollback(tmp_path, FakeDocker(earlier_on_host=False))

    assert "cannot be fetched again" in run.failure
    assert not [c for c in run.steps if c.name == "start database"]


def test_no_upgrade_recorded_means_nothing_to_rehearse(tmp_path: Path):
    _history(tmp_path / "data", [{"subject": "nextcloud/db", "digest": LIVE}])

    run, _ = _rollback(tmp_path, FakeDocker())

    assert run.failure.startswith("no earlier image recorded for nc_db")


def test_a_container_outside_the_recipe_is_refused(tmp_path: Path):
    run, _ = _rollback(tmp_path, FakeDocker(), only="wp_app")

    assert "is not a container of the nextcloud recipe" in run.failure


def test_repository_names_drop_the_tag_not_the_registry_port():
    assert _repository("wordpress:latest") == "wordpress"
    assert _repository("ghcr.io/immich-app/immich-server:v2.7.5") == "ghcr.io/immich-app/immich-server"
    assert _repository("registry:5000/team/app:1") == "registry:5000/team/app"


def test_without_a_registry_digest_the_local_image_is_tagged_to_be_pinned():
    previous = PreviousImage(
        container="wp_app", subject="wordpress/wordpress", image_name="wordpress:latest",
        current=LIVE, previous=EARLIER, upgraded_at="2026-10-07T03-00-00Z",
        compose_dir="/srv/wordpress", compose_service="wordpress",
    )
    lines = pin_instructions(previous)

    assert f"  docker tag {EARLIER} wordpress:rollback" in lines
    assert "    image: wordpress:rollback" in lines

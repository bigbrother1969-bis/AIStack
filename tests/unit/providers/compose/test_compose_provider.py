"""
`ComposeProvider`'s own `depends_on:` reading, added 2026-09-12
(`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, third gap).

No dedicated test file existed for `ComposeProvider` before this —
it was exercised only through `test_compose_runtime_catalog.py`
(against a raw observation dict) and
`test_the_provider_commands_run.py` (a stubbed provider standing in
for the real one). This file is the first to drive
`ComposeProvider.collect()` itself, because the new behaviour —
reading a real file off disk — is exactly the part neither of those
exercises: a raw-observation test never calls `collect()`, and a
stubbed provider never runs the real one's code at all.

`DockerProvider` is stubbed the same way `test_the_provider_commands_
run.py` already stubs it (a fake `collect()`, no real daemon); the
compose file itself is real, written to `tmp_path` — the same
"exercise the real thing, not a mock of it" reasoning
`BeszelProvider`'s own tests use a real HTTP server for.
"""

from __future__ import annotations

from pathlib import Path

from aistack.providers.compose import ComposeProvider
from aistack.providers.compose import provider as compose_module


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def container(
    name: str,
    project: str,
    service: str,
    config_files: str,
    working_dir: str = "/srv/project",
) -> dict:
    labels = (
        f"com.docker.compose.project={project},"
        f"com.docker.compose.service={service},"
        f"com.docker.compose.project.working_dir={working_dir},"
        f"com.docker.compose.project.config_files={config_files}"
    )
    return {
        "Names": name,
        "Image": f"{name}:latest",
        "State": "running",
        "Status": "Up 2 hours",
        "Ports": "",
        "Labels": labels,
    }


class FakeDockerProvider:
    def __init__(self, containers: list[dict]):
        self._containers = containers

    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.docker"},
            "collected_at": "2026-09-12T12:00:00+00:00",
            "docker": {"containers": self._containers},
        }


def stub_docker(monkeypatch, containers: list[dict]) -> None:
    monkeypatch.setattr(
        compose_module, "DockerProvider", lambda: FakeDockerProvider(containers)
    )


def services_of(observation: dict, project: str) -> dict:
    for item in observation["compose"]["projects"]:
        if item["name"] == project:
            return item["services"]
    raise AssertionError(f"project {project!r} not observed")


# --------------------------------------------------------------------
# The plain-list form — most of GIGABYTE's real files use this
# --------------------------------------------------------------------


def test_a_plain_list_depends_on_is_read(tmp_path: Path, monkeypatch):
    compose_file = write(
        tmp_path / "docker-compose.yml",
        """
        services:
          bookstack:
            image: lscr.io/linuxserver/bookstack
            depends_on:
              - bookstack_db
          bookstack_db:
            image: mariadb
        """,
    )

    stub_docker(
        monkeypatch,
        [
            container("bookstack", "bookstack", "bookstack", str(compose_file)),
            container("bookstack_db", "bookstack", "bookstack_db", str(compose_file)),
        ],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "bookstack")

    assert services["bookstack"]["depends_on"] == ["bookstack_db"]
    assert "depends_on" not in services["bookstack_db"]


# --------------------------------------------------------------------
# The mapping-with-condition form — GIGABYTE's `booklore`/`romm`
# --------------------------------------------------------------------


def test_a_mapping_with_condition_depends_on_is_read_as_just_the_names(
    tmp_path: Path, monkeypatch
):
    compose_file = write(
        tmp_path / "docker-compose.yml",
        """
        services:
          romm:
            image: rommapp/romm
            depends_on:
              romm-db:
                condition: service_healthy
          romm-db:
            image: mariadb
        """,
    )

    stub_docker(
        monkeypatch,
        [
            container("romm", "romm", "romm", str(compose_file)),
            container("romm-db", "romm", "romm-db", str(compose_file)),
        ],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "romm")

    assert services["romm"]["depends_on"] == ["romm-db"]


# --------------------------------------------------------------------
# Tolerance — a real file on disk, not a hand-written governed YAML
# --------------------------------------------------------------------


def test_a_missing_compose_file_does_not_raise(tmp_path: Path, monkeypatch):
    missing_path = str(tmp_path / "does-not-exist.yml")

    stub_docker(
        monkeypatch,
        [container("web", "ghost-project", "web", missing_path)],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "ghost-project")

    assert "depends_on" not in services["web"]


def test_a_malformed_yaml_file_does_not_raise(tmp_path: Path, monkeypatch):
    compose_file = write(tmp_path / "docker-compose.yml", "services: [this is not a mapping\n")

    stub_docker(
        monkeypatch,
        [container("web", "broken-project", "web", str(compose_file))],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "broken-project")

    assert "depends_on" not in services["web"]


def test_a_compose_file_whose_top_level_is_not_a_mapping_does_not_raise(
    tmp_path: Path, monkeypatch
):
    compose_file = write(tmp_path / "docker-compose.yml", "- one\n- two\n")

    stub_docker(
        monkeypatch,
        [container("web", "list-project", "web", str(compose_file))],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "list-project")

    assert "depends_on" not in services["web"]


def test_a_service_with_no_depends_on_key_carries_none(tmp_path: Path, monkeypatch):
    compose_file = write(
        tmp_path / "docker-compose.yml",
        """
        services:
          solo:
            image: whatever
        """,
    )

    stub_docker(
        monkeypatch,
        [container("solo", "solo-project", "solo", str(compose_file))],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "solo-project")

    assert "depends_on" not in services["solo"]


def test_a_depends_on_entry_that_is_not_a_string_is_skipped(
    tmp_path: Path, monkeypatch
):
    compose_file = write(
        tmp_path / "docker-compose.yml",
        """
        services:
          web:
            image: whatever
            depends_on:
              - 42
              - db
          db:
            image: mariadb
        """,
    )

    stub_docker(
        monkeypatch,
        [
            container("web", "mixed-project", "web", str(compose_file)),
            container("db", "mixed-project", "db", str(compose_file)),
        ],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "mixed-project")

    assert services["web"]["depends_on"] == ["db"]


def test_no_config_files_label_at_all_does_not_raise(tmp_path: Path, monkeypatch):
    labels = "com.docker.compose.project=no-config,com.docker.compose.service=web"
    stub_docker(
        monkeypatch,
        [
            {
                "Names": "web",
                "Image": "web:latest",
                "State": "running",
                "Status": "Up",
                "Ports": "",
                "Labels": labels,
            }
        ],
    )

    observation = ComposeProvider().collect()
    services = services_of(observation, "no-config")

    assert "depends_on" not in services["web"]


# --------------------------------------------------------------------
# Multiple config files — Compose's own `-f` merge order
#
# Exercised directly against `_read_depends_on`, not through
# `collect()`'s full container/label path: `_parse_labels` itself
# splits the whole `Labels` string on `,`, so a `config_files` value
# that is itself comma-separated (Compose's own multi-`-f` form)
# cannot round-trip through a synthetic `Labels` string in a test
# without colliding with that same separator — a pre-existing
# limitation of `_parse_labels`, not something this feature changes,
# and moot in practice: GIGABYTE's own 33 real projects (checked
# 2026-09-12) never produced more than one path.
# --------------------------------------------------------------------


def test_a_later_config_file_overrides_an_earlier_ones_depends_on(tmp_path: Path):
    base = write(
        tmp_path / "docker-compose.yml",
        """
        services:
          web:
            image: whatever
            depends_on:
              - db
          db:
            image: mariadb
          cache:
            image: redis
        """,
    )
    override = write(
        tmp_path / "docker-compose.override.yml",
        """
        services:
          web:
            depends_on:
              - cache
        """,
    )

    depends_on = ComposeProvider()._read_depends_on(f"{base},{override}")

    assert depends_on["web"] == ("cache",)


# --------------------------------------------------------------------
# Unrelated projects are unaffected by one project's broken file
# --------------------------------------------------------------------


def test_one_projects_unreadable_file_does_not_affect_another_project(
    tmp_path: Path, monkeypatch
):
    good_file = write(
        tmp_path / "good" / "docker-compose.yml",
        """
        services:
          web:
            image: whatever
            depends_on:
              - db
          db:
            image: mariadb
        """,
    )
    missing_path = str(tmp_path / "bad" / "docker-compose.yml")

    stub_docker(
        monkeypatch,
        [
            container("good-web", "good-project", "web", str(good_file)),
            container("good-db", "good-project", "db", str(good_file)),
            container("bad-web", "bad-project", "web", missing_path),
        ],
    )

    observation = ComposeProvider().collect()

    good_services = services_of(observation, "good-project")
    bad_services = services_of(observation, "bad-project")

    assert good_services["web"]["depends_on"] == ["db"]
    assert "depends_on" not in bad_services["web"]

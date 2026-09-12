"""
`aistack.cli.architecture_render` — the dependency-graph wiring added
2026-09-12 (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, third gap).

Driven directly against `main(environ=...)`, the same way
`test_architecture_render_beszel.py` drives the Beszel wiring: Docker
and Compose are stubbed the same way `test_the_provider_commands_run.py`
already stubs them, but here the fake Compose observation carries a
real `depends_on:` reading (a service dict shaped exactly like
`ComposeProvider.collect()` produces once its own new `depends_on:`
reading ran) — the one piece of this feature no other test file
drives end to end through `main()` itself.

What is under test here is the wiring `architecture_render.py` adds:
no additional provider call is made (`build_dependency_graph` reads
straight off the already-built `compose_catalog`), and the resulting
`DependencyGraph` reaches `render_html` as its `dependency_graph`
argument. The renderer's own behaviour (the extra `<select>` option,
the embedded Mermaid definition, "nothing observed, nothing
rendered") is already exhaustively covered at `render_html`'s own
level (`test_html.py`); this file is only about the CLI reaching that
point correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.cli import architecture_render


OBSERVED_AT = "2026-09-12T12:00:00+00:00"


class FakeDockerProvider:
    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.docker"},
            "collected_at": OBSERVED_AT,
            "docker": {"containers": [], "images": [], "networks": [], "volumes": []},
        }


class FakeComposeProvider:
    """
    Its `collect()` return value is shaped exactly like the real
    `ComposeProvider.collect()`'s own output once its `depends_on:`
    reading ran — this file does not exercise that reading itself
    (`test_compose_provider.py` already does), it stands in for its
    *result* so `architecture_render.main()`'s own wiring can be
    driven without a real Docker daemon or a real compose file on
    disk.
    """

    def __init__(self, projects: list[dict]):
        self._projects = projects

    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.compose"},
            "collected_at": OBSERVED_AT,
            "compose": {"projects": self._projects},
        }


def bookstack_project() -> dict:
    return {
        "name": "bookstack",
        "working_dir": "/srv/bookstack",
        "config_files": "docker-compose.yml",
        "services": {
            "bookstack": {
                "container_name": "bookstack",
                "depends_on": ["bookstack_db"],
            },
            "bookstack_db": {"container_name": "bookstack_db"},
        },
    }


def jellyfin_project_with_no_depends_on() -> dict:
    return {
        "name": "jellyfin",
        "working_dir": "/srv/jellyfin",
        "config_files": "docker-compose.yml",
        "services": {"jellyfin": {"container_name": "jellyfin"}},
    }


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def stub_providers(monkeypatch, compose_projects: list[dict]) -> None:
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.DockerProvider", FakeDockerProvider
    )
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.ComposeProvider",
        lambda: FakeComposeProvider(compose_projects),
    )


# --------------------------------------------------------------------
# A project with a real depends_on: reaches the rendered page
# --------------------------------------------------------------------


def test_a_real_dependency_edge_reaches_the_rendered_page(monkeypatch, workspace):
    stub_providers(monkeypatch, [bookstack_project()])

    architecture_render.main(environ={})

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")

    assert '<option value="dependencies">Dépendances (Docker)</option>' in document
    assert "bookstack" in document
    assert "bookstack_db" in document


# --------------------------------------------------------------------
# No depends_on: anywhere — no additional provider call, no section
# --------------------------------------------------------------------


def test_a_project_with_no_depends_on_adds_no_dependencies_option(
    monkeypatch, workspace
):
    stub_providers(monkeypatch, [jellyfin_project_with_no_depends_on()])

    architecture_render.main(environ={})

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")

    assert 'value="dependencies"' not in document


def test_no_compose_projects_at_all_adds_no_dependencies_option(
    monkeypatch, workspace
):
    stub_providers(monkeypatch, [])

    architecture_render.main(environ={})

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")

    assert document.startswith("<!doctype html>")
    assert 'value="dependencies"' not in document

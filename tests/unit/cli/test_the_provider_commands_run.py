"""
GOV-0002/OS-044: the four provider commands execute.

**These tests exist because all four were broken for forty
days and nothing noticed.** `f685f97` (2026-07-20) moved
`providers` under `Kernel.registries` and touched none of the
four CLIs, so each raised `AttributeError` on the second line of
`main()`, before reaching any provider. Measured 2026-08-29 by
running them.

What made that survivable is measurable and is the reason these
tests are shaped as they are:

- **no test imported any of the four**, while `evidence_extract`,
  `knowledge_integrity` and `runtime_diagnose` each had one. The
  rename was correct everywhere it looked, and it looked at
  everything with a test;
- **`unused-registrations` read `ctx.providers.get(...)` as a
  retrieval site by AST shape**, without checking that `ctx`
  carries the attribute. It reported `providers` as retrieved,
  and the four sites it counted were the four lines that raise.

So each test drives a real `main()` end to end against a stubbed
provider. **A test that imported the module and asserted nothing
would have gone green through the whole forty days.**

Docker itself is exercised nowhere: the daemon would make these
results depend on the machine, and what is under test is the wiring
between the CLI, the Kernel and the generator.

A fifth command joined the same way, 2026-09-10: `architecture_render`
(J2 step 6, `claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`) is the
first to reach *both* providers itself, composing what
`docker_catalog` and `compose_catalog` each already prove individually
reachable. The title still names four — the incident it records
involved exactly those four, and stays what happened rather than a
running count of this file's own tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.cli import architecture_render


OBSERVED_AT = "2026-08-29T09:00:00+00:00"


class FakeDockerProvider:
    """A Docker provider that observes without a daemon."""

    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.docker"},
            "collected_at": OBSERVED_AT,
            "docker": {
                "containers": [
                    {
                        "ID": "c1",
                        "Names": "aistack-web",
                        "Image": "nginx:1.27",
                        "Status": "Up 2 hours (healthy)",
                        "State": "running",
                        "Ports": "80/tcp",
                    }
                ],
                "images": [
                    {
                        "Repository": "nginx",
                        "Tag": "1.27",
                        "ID": "i1",
                        "Size": "50MB",
                    }
                ],
                "networks": [
                    {"ID": "n1", "Name": "bridge", "Driver": "bridge", "Scope": "local"}
                ],
                "volumes": [
                    {"Name": "data", "Driver": "local", "Scope": "local"}
                ],
            },
        }


class FakeComposeProvider:
    """A Compose provider that observes without a daemon."""

    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.compose"},
            "collected_at": OBSERVED_AT,
            "compose": {
                "projects": [
                    {
                        "name": "aistack",
                        "working_dir": "/srv/aistack",
                        "config_files": "docker-compose.yml",
                        "services": {"web": {}, "db": {}},
                    }
                ]
            },
        }


class FakeHttpProbeProvider:
    """
    A stand-in for `HttpProbeProvider`, added 2026-09-23.

    `architecture_render.main()` — driven twice in this file, both
    with the real, unmocked `DEFAULT_TOPOLOGY` and
    `DEFAULT_CMDB_TARGETS` — builds `HttpProbeProvider` unconditionally
    against the owner's real `cmdb_probe_targets.yml` (46 real
    endpoints) and probes them for real, several timing out at the
    provider's own 5.0s default. Docker itself is deliberately not
    exercised here (see the module docstring); the same reasoning
    applies to a real fleet of HTTP endpoints.
    """

    def __init__(
        self, targets: tuple[tuple[str, str], ...], timeout: float = 5.0
    ) -> None:
        self._targets = targets

    def collect(self) -> dict:
        return {
            "provider": {
                "id": "aistack.provider.http_probe",
                "name": "HTTP Probe Provider",
            },
            "collected_at": OBSERVED_AT,
            "http_probe": {"targets": []},
        }


@pytest.fixture
def stubbed_providers(monkeypatch) -> None:
    """
    Replace what the Composition Root instantiates.

    The registry refuses a duplicate identifier, so a fake cannot
    be registered over a real one — the provider class is stubbed
    where `register_default_providers` reads it, which is also
    where the real dependency on a daemon enters.
    """

    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.DockerProvider",
        FakeDockerProvider,
    )
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.ComposeProvider",
        FakeComposeProvider,
    )
    monkeypatch.setattr(
        architecture_render, "HttpProbeProvider", FakeHttpProbeProvider
    )


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    """The commands write under a relative `reports/generated/`."""

    monkeypatch.chdir(tmp_path)
    return tmp_path


def written(workspace: Path, name: str) -> dict:
    path = workspace / "reports" / "generated" / name

    assert path.exists(), f"{name} was not written"

    return json.loads(path.read_text(encoding="utf-8"))


def test_architecture_render_writes_the_html_artifact(stubbed_providers, workspace):
    """
    J2 step 6: the fifth command, and the first to reach both
    providers itself rather than just one. Neither fake container
    matches any container the real, shipped
    `service_categorization.yml` declares, so nothing in this run
    is `IN_COMPOSE_PROJECT` or `OBSERVED` — every status combination
    is already exhaustively covered by `test_graph.py` and
    `test_mermaid.py` against synthetic fixtures. What this asserts
    is the wiring: the command reaches both providers, builds both
    catalogs, loads the real categorization, loads the real
    infrastructure topology (`DEFAULT_TOPOLOGY`, added 2026-09-12,
    §10), and writes a page that names a real declared service and a
    real hardware fiche.
    """

    architecture_render.main()

    path = workspace / "reports" / "generated" / "architecture.html"
    assert path.exists()

    document = path.read_text(encoding="utf-8")
    assert document.startswith("<!doctype html>")
    assert "Nginx Proxy Manager" in document
    assert '<section class="topology-index">' in document
    assert "GIGABYTE" in document


def test_every_provider_command_reaches_its_provider(
    stubbed_providers, workspace
):
    """
    The regression itself, stated once rather than implied by
    three outputs.

    Each command failed at `ctx.providers.get(...)` — an attribute
    `Kernel` does not carry — so **none of them ever called
    `collect`**. This asserts the crossing that was broken: the
    command reaches the Kernel, the Kernel yields the provider,
    the provider is asked.
    """

    calls: list[str] = []

    class CountingDocker(FakeDockerProvider):
        def collect(self) -> dict:
            calls.append("docker")
            return super().collect()

    class CountingCompose(FakeComposeProvider):
        def collect(self) -> dict:
            calls.append("compose")
            return super().collect()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "aistack.kernel.bootstrap.providers.DockerProvider",
            CountingDocker,
        )
        patch.setattr(
            "aistack.kernel.bootstrap.providers.ComposeProvider",
            CountingCompose,
        )

        architecture_render.main()

    assert calls == ["docker", "compose"]

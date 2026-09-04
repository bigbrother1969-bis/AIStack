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
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.cli import (
    compose_catalog,
    docker_catalog,
    docker_discover,
    docker_selection_catalog,
)


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


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    """The commands write under a relative `reports/generated/`."""

    monkeypatch.chdir(tmp_path)
    return tmp_path


def written(workspace: Path, name: str) -> dict:
    path = workspace / "reports" / "generated" / name

    assert path.exists(), f"{name} was not written"

    return json.loads(path.read_text(encoding="utf-8"))


def test_docker_catalog_writes_a_catalog(stubbed_providers, workspace):
    docker_catalog.main()

    catalog = written(workspace, "docker-runtime-catalog.json")

    assert catalog["catalog_id"] == "docker-runtime"
    assert [item["kind"] for item in catalog["items"]] == [
        "container",
        "image",
        "network",
        "volume",
    ]


def test_docker_catalog_writes_the_explanation_alongside_it(
    stubbed_providers, workspace
):
    """
    `STD-0300` VS-1 criterion 1.4: the explanation is generated in
    the same run as the catalog it explains, from the same
    observation — added 2026-09-04.
    """

    docker_catalog.main()

    path = workspace / "reports" / "generated" / "docker-runtime-explanation.txt"

    assert path.exists()
    assert "aistack-web" in path.read_text(encoding="utf-8")


def test_docker_discover_writes_the_observation(stubbed_providers, workspace):
    docker_discover.main()

    observation = written(workspace, "docker-provider-observation.json")

    assert observation["provider"]["id"] == "aistack.provider.docker"
    assert observation["collected_at"] == OBSERVED_AT


def test_compose_catalog_writes_a_catalog(stubbed_providers, workspace):
    compose_catalog.main()

    catalog = written(workspace, "compose-runtime-catalog.json")

    assert catalog["catalog_id"] == "compose-runtime"
    assert catalog["items"]


def test_docker_selection_catalog_writes_its_artifact(
    stubbed_providers, workspace
):
    """
    The fourth command, asserted on what it writes today.

    Its output changed shape in the commit that repaired
    GOV-0002/OS-042: the path produces a `CatalogView` and no
    longer a `SelectionCatalog`. **The first version of this
    assertion was written against the artifact of the day
    before** — a test shaped for the destination would have
    passed before the work and proved nothing about the defect
    this file exists for.

    `view_id` and `source_catalog_id` are the pair the retired
    type did not carry, and they are what makes a view traceable
    to the catalog it derives from.
    """

    docker_selection_catalog.main()

    view = written(workspace, "docker-selection-catalog.json")

    assert view["view_id"] == "docker-containers"
    assert view["source_catalog_id"] == "docker-runtime"
    assert [item["label"] for item in view["items"]] == ["aistack-web"]


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

        docker_catalog.main()
        docker_discover.main()
        docker_selection_catalog.main()
        compose_catalog.main()

    assert calls == ["docker", "docker", "docker", "compose"]

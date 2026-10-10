"""
Each generator wired into Observation History
(`write_artifact_with_history`, 2026-09-03 for Docker/Compose,
extended to Jellyfin the same day), asserted through its own
`generate()` — not through the shared `write_artifact_with_history`
tests (`test_history.py`, which never import a generator) and not
only through `tests/unit/cli/test_the_provider_commands_run.py`
(which drives the four Docker/Compose generators end to end via
their CLI `main()`s, but its `written()` helper only reads
`reports/generated/<name>.json`, never `history/<stem>/`).

**Why this file exists.** `test_the_provider_commands_run.py`'s own
docstring names the failure this project institutionalised testing
against: all four provider CLIs raised on their second line for
forty days, unnoticed, because nothing imported them. Nothing in
the suite currently would notice the same class of regression for
Observation History specifically — one generator reverted to a
bare `write_text`, or wired to the wrong stem — since the CLI tests
never look at `history/`. This file is that missing assertion, one
test per generator: "cave au grenier" per generator, not just at
the shared utility and at the CLI's front door.
"""

from __future__ import annotations

import json
from pathlib import Path

from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.views import build_all_views
from aistack.contracts.console_link import ConsoleLink
from aistack.generators.architecture import ArchitectureHtmlArtifactGenerator
from aistack.generators.docker.catalog_artifact import DockerCatalogArtifactGenerator
from aistack.generators.filesystem.media_library_artifact import (
    MediaLibraryObservationArtifactGenerator,
)
from aistack.generators.console import ConsoleHtmlArtifactGenerator
from aistack.generators.health import HealthHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.generators.network_docker.observation_artifact import (
    NetworkDockerObservationArtifactGenerator,
)
from aistack.generators.docker.observation_artifact import (
    DockerObservationArtifactGenerator,
)
from aistack.kernel.catalog import Catalog, CatalogItem


def _history_files(output_path: Path) -> list[Path]:
    history_dir = output_path.parent / "history" / output_path.stem
    return sorted(history_dir.glob("*"))


def test_docker_observation_artifact_generator_keeps_history(tmp_path: Path):
    generator = DockerObservationArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "docker-provider-observation.json"
    observation = {"provider": {"id": "aistack.provider.docker"}, "docker": {}}

    generator.generate(observation=observation, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert json.loads(history_files[0].read_text(encoding="utf-8")) == observation
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_docker_catalog_artifact_generator_keeps_history(tmp_path: Path):
    generator = DockerCatalogArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"
    catalog = Catalog(
        catalog_id="docker-runtime",
        title="Docker Runtime Catalog",
        items=(CatalogItem(id="c1", label="aistack-web", kind="container"),),
    )

    generator.generate(catalog=catalog, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert json.loads(history_files[0].read_text(encoding="utf-8"))["catalog_id"] == (
        "docker-runtime"
    )
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_network_docker_observation_artifact_generator_keeps_history(tmp_path: Path):
    generator = NetworkDockerObservationArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "network-docker-observation.json"
    observation = {
        "provider": {"id": "aistack.provider.network_docker"},
        "network_docker": {"cidr": "192.168.1.0/24", "hosts": []},
    }

    generator.generate(observation=observation, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert json.loads(history_files[0].read_text(encoding="utf-8")) == observation
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_architecture_html_artifact_generator_keeps_history(tmp_path: Path):
    generator = ArchitectureHtmlArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "architecture.html"
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision",
                services=(
                    ServiceNode(
                        name="Beszel",
                        category="Supervision",
                        container="beszel",
                        status=ServiceStatus.OBSERVED,
                    ),
                ),
            ),
        )
    )
    views = build_all_views(graph)

    generator.generate(views=views, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert history_files[0].read_text(encoding="utf-8").startswith("<!doctype html>")
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_health_html_artifact_generator_keeps_history(tmp_path: Path):
    generator = HealthHtmlArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "health.html"
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True),
            HealthDomain(name="GPU", instrumented=False, note="pas encore"),
        )
    )

    generator.generate(cockpit=cockpit, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert history_files[0].read_text(encoding="utf-8").startswith("<!doctype html>")
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_console_html_artifact_generator_keeps_history(tmp_path: Path):
    generator = ConsoleHtmlArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "console.html"
    links = (
        ConsoleLink(
            name="Selection UI",
            description="Sélection des candidats",
            url="http://GIGABYTE:8181",
            scope="lan",
        ),
    )

    generator.generate(links=links, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert history_files[0].read_text(encoding="utf-8").startswith("<!doctype html>")
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_media_library_observation_artifact_generator_keeps_history(tmp_path: Path):
    generator = MediaLibraryObservationArtifactGenerator()
    output_path = (
        tmp_path
        / "reports"
        / "generated"
        / "music_android-media-library-observation.json"
    )
    observation = {
        "provider": {"id": "aistack.provider.filesystem.media-library"},
        "library": {},
    }

    generator.generate(observation=observation, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert json.loads(history_files[0].read_text(encoding="utf-8")) == observation
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )

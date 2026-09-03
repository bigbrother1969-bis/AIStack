"""
Each of the four generators wired into Observation History
(`write_artifact_with_history`, 2026-09-03), asserted through its
own `generate()` — not through the shared `write_artifact_with_history`
tests (`test_history.py`, which never import a generator) and not
only through `tests/unit/cli/test_the_provider_commands_run.py`
(which drives these same generators end to end via the four CLI
`main()`s, but its `written()` helper only reads
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

from aistack.generators.catalog_view import CatalogViewArtifactGenerator
from aistack.generators.compose.catalog_artifact import ComposeCatalogArtifactGenerator
from aistack.generators.docker.catalog_artifact import DockerCatalogArtifactGenerator
from aistack.generators.docker.observation_artifact import (
    DockerObservationArtifactGenerator,
)
from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.kernel.catalog.views import CatalogView, CatalogViewItem


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


def test_compose_catalog_artifact_generator_keeps_history(tmp_path: Path):
    generator = ComposeCatalogArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "compose-runtime-catalog.json"
    catalog = Catalog(
        catalog_id="compose-runtime",
        title="Compose Runtime Catalog",
        items=(CatalogItem(id="p1", label="aistack", kind="project"),),
    )

    generator.generate(catalog=catalog, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert json.loads(history_files[0].read_text(encoding="utf-8"))["catalog_id"] == (
        "compose-runtime"
    )
    # ComposeCatalogArtifactGenerator deliberately writes no trailing
    # newline (pre-existing behaviour, kept unchanged) — the history
    # copy must be byte-identical to the latest copy, not merely
    # equal after parsing.
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_catalog_view_artifact_generator_keeps_history(tmp_path: Path):
    generator = CatalogViewArtifactGenerator()
    output_path = tmp_path / "reports" / "generated" / "docker-selection-catalog.json"
    view = CatalogView(
        view_id="docker-containers",
        source_catalog_id="docker-runtime",
        title="Docker Containers",
        items=[CatalogViewItem(id="c1", label="aistack-web")],
    )

    generator.generate(view=view, output_path=output_path)

    history_files = _history_files(output_path)
    assert len(history_files) == 1
    assert json.loads(history_files[0].read_text(encoding="utf-8"))["view_id"] == (
        "docker-containers"
    )
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )

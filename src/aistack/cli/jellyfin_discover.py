from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from aistack.generators.jellyfin import JellyfinObservationArtifactGenerator
from aistack.priority.definition import (
    JellyfinDetectorDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.providers.jellyfin import JellyfinProvider


# The one governed place a Jellyfin URL and API key env var name are
# already declared — resource_priority.yml's own
# JellyfinDetectorDefinition (`priority/definition.py`), read today
# by `aistack.cli.resource_priority_monitor`. This command reads the
# same file rather than opening a second configuration surface for
# one fact that already has a governed home — same default path the
# monitor uses.
DEFAULT_DEFINITION = (
    Path(__file__).resolve().parents[1]
    / "priority"
    / "definitions"
    / "resource_priority.yml"
)

USAGE = (
    "usage: python -m aistack.cli.jellyfin_discover [--definition PATH]\n"
    "\n"
    "  Asks Jellyfin's own /Sessions endpoint what it currently\n"
    "  knows and writes the observation, keeping Observation\n"
    "  History alongside it — the same shape as docker_discover,\n"
    "  run on demand rather than on the CPU monitor's 5-second poll.\n"
    "\n"
    "  --definition  path to the governed resource-priority YAML\n"
    "                that names the Jellyfin URL and API key env\n"
    "                var (default: the real one this repository\n"
    "                ships).\n"
)


def parse(argv: list[str]) -> Path:

    definition_path = DEFAULT_DEFINITION
    rest = list(argv)

    while rest:
        argument = rest.pop(0)

        if argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)

        if argument == "--definition":
            if not rest:
                print("--definition expects a path")
                raise SystemExit(2)
            definition_path = Path(rest.pop(0))
            continue

        print(f"unrecognised argument: {argument}")
        raise SystemExit(2)

    return definition_path


def find_jellyfin_detector(
    definition: ResourcePriorityDefinition,
) -> JellyfinDetectorDefinition:
    """
    The one `JellyfinDetectorDefinition` a priority app declares, if
    any. Several detector types can appear in `priority[]`
    (`CpuThresholdDetectorDefinition` among them, since 2026-09-03's
    move to a pluggable detector abstraction —
    `aistack.priority.detectors.factory`) — this command needs the
    Jellyfin one specifically, wherever it sits in the list.
    """

    for app in definition.priority:
        if isinstance(app.detector, JellyfinDetectorDefinition):
            return app.detector

    print(
        "No priority app in the definition declares a Jellyfin "
        "detector — nothing to observe."
    )
    raise SystemExit(2)


def main(
    argv: list[str] | None = None, environ: Mapping[str, str] | None = None
) -> None:

    environ = os.environ if environ is None else environ
    definition_path = parse(sys.argv[1:] if argv is None else argv)

    definition = load_resource_priority_yaml(definition_path)
    detector = find_jellyfin_detector(definition)

    # GOV-P-001, same handling as the CPU monitor's own detector
    # factory: the env var name is read from the governed
    # definition, never the key itself.
    api_key = environ.get(detector.api_key_env, "") if detector.api_key_env else ""

    provider = JellyfinProvider(
        detector.url, api_key, timeout=detector.timeout_seconds
    )
    observation = provider.collect()

    output_path = JellyfinObservationArtifactGenerator().generate(
        observation=observation,
        output_path=Path("reports/generated/jellyfin-observation.json"),
    )

    print(f"Jellyfin observation written to {output_path}")


if __name__ == "__main__":
    main()

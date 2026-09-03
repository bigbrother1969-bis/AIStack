from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from aistack.application.yaml import load_application_definition_yaml
from aistack.generators.syncthing import SyncthingObservationArtifactGenerator
from aistack.providers.syncthing import SyncthingProvider


# The one governed place a Selection UI instance's Syncthing folder
# and API-key env var name are already declared — its own
# ApplicationDefinition, the same file `selection_ui/app.py` reads
# on every page view (`selection_ui/definitions/music_android.yml`
# today; "a second instance of the family should differ only by
# which YAML it is handed", per that definition's own docstring).
# This command reads the same file rather than opening a second
# configuration surface for facts that already have a governed home.
DEFAULT_DEFINITION = (
    Path(__file__).resolve().parents[3]
    / "selection_ui"
    / "definitions"
    / "music_android.yml"
)

USAGE = (
    "usage: python -m aistack.cli.syncthing_discover [--definition PATH]\n"
    "\n"
    "  Asks Syncthing's own /rest/db/status and /rest/db/completion\n"
    "  what they currently know about one Selection UI instance's\n"
    "  folder and writes the observation, keeping Observation\n"
    "  History alongside it — run on demand rather than on\n"
    "  selection_ui's own per-page-view call.\n"
    "\n"
    "  --definition  path to the governed Application Definition\n"
    "                that names the Syncthing folder and API key\n"
    "                env var (default: the real one this\n"
    "                repository ships, music_android.yml).\n"
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


def main(
    argv: list[str] | None = None, environ: Mapping[str, str] | None = None
) -> None:

    environ = os.environ if environ is None else environ
    definition_path = parse(sys.argv[1:] if argv is None else argv)

    definition = load_application_definition_yaml(definition_path)

    if definition.syncthing is None:
        print(
            f"{definition.app_id!r} declares no Syncthing configuration "
            "— nothing to observe."
        )
        raise SystemExit(2)

    syncthing = definition.syncthing

    # GOV-P-001, same handling as `selection_ui.app._syncthing_status`:
    # the env var name is read from the governed definition, never
    # the key itself.
    api_key = environ.get(syncthing.api_key_env, "") if syncthing.api_key_env else ""

    provider = SyncthingProvider(
        url=syncthing.url,
        api_key=api_key,
        folder_id=syncthing.folder_id,
        device_id=syncthing.device_id,
        timeout=syncthing.timeout_seconds,
    )
    observation = provider.collect()

    # Prefixed with `app_id`, matching `selection_ui.app.
    # _last_generation_path`'s own convention — this family is
    # explicitly meant to run more than one instance from different
    # definitions, and their artifacts must not collide.
    output_path = SyncthingObservationArtifactGenerator().generate(
        observation=observation,
        output_path=Path(
            f"reports/generated/{definition.app_id}-syncthing-observation.json"
        ),
    )

    print(f"Syncthing observation written to {output_path}")


if __name__ == "__main__":
    main()

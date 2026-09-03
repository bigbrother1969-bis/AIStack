from __future__ import annotations

import sys
from pathlib import Path

from aistack.application.yaml import load_application_definition_yaml
from aistack.generators.filesystem import MediaLibraryObservationArtifactGenerator
from aistack.providers.filesystem import MediaLibraryProvider


# The one governed place a Selection UI instance's media-library
# root is already declared — its own ApplicationDefinition, the
# same file `selection_ui/app.py` reads on every page view
# (`selection_ui/definitions/music_android.yml` today). This
# command reads the same file rather than opening a second
# configuration surface for a fact that already has a governed home.
DEFAULT_DEFINITION = (
    Path(__file__).resolve().parents[3]
    / "selection_ui"
    / "definitions"
    / "music_android.yml"
)

USAGE = (
    "usage: python -m aistack.cli.media_library_discover [--definition PATH]\n"
    "\n"
    "  Walks one Selection UI instance's media library and writes\n"
    "  the observation, keeping Observation History alongside it —\n"
    "  run on demand rather than on selection_ui's own\n"
    "  per-page-view call. Costs on the order of 1,4 s on the\n"
    "  owner's real library (MediaLibraryProvider's own\n"
    "  measurement).\n"
    "\n"
    "  --definition  path to the governed Application Definition\n"
    "                that names the library's root (default: the\n"
    "                real one this repository ships,\n"
    "                music_android.yml).\n"
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


def main(argv: list[str] | None = None) -> None:

    definition_path = parse(sys.argv[1:] if argv is None else argv)
    definition = load_application_definition_yaml(definition_path)

    provider = MediaLibraryProvider(Path(definition.source_root))
    observation = provider.collect()

    # Prefixed with `app_id`, matching `selection_ui.app.
    # _last_generation_path`'s own convention — this family is
    # explicitly meant to run more than one instance from different
    # definitions, and their artifacts must not collide.
    output_path = MediaLibraryObservationArtifactGenerator().generate(
        observation=observation,
        output_path=Path(
            f"reports/generated/{definition.app_id}-media-library-observation.json"
        ),
    )

    print(f"Media library observation written to {output_path}")


if __name__ == "__main__":
    main()

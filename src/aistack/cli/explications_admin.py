"""
`python -m aistack.cli.explications_admin` — what the development phase
allows on Explications from the host itself (`ADR-0016`):

    python -m aistack.cli.explications_admin purge wordpress
    python -m aistack.cli.explications_admin validate-declared

`purge` deletes every version of one subject's Explication — test
entries made while AIStack is set up; `validate-declared` validates
every person's text still waiting for a second person. Both refuse
outside the development phase (`instance_config.yml`'s `phase`), and
both are seen by the graph at the next `timemachine_rebuild`.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from aistack.explications.human import ExplicationRefused, Person, purge, validate_declared
from aistack.instance.yaml.store import load_instance_config_yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_CONFIG = PACKAGE_ROOT / "instance" / "definitions" / "instance_config.yml"
EXPLICATIONS_DIR = Path("reports/generated/explications")


def main(
    argv: list[str] | None = None,
    instance_config: Path = INSTANCE_CONFIG,
    explications_dir: Path = EXPLICATIONS_DIR,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.explications_admin")
    commands = parser.add_subparsers(dest="command", required=True)
    purge_parser = commands.add_parser("purge", help="delete every version of one subject's Explication")
    purge_parser.add_argument("subject")
    commands.add_parser("validate-declared", help="validate every person's text still waiting")
    arguments = parser.parse_args(argv)

    config = load_instance_config_yaml(instance_config)
    if not config.in_development:
        print(
            f"Refused: the instance is in its {config.phase} phase (instance_config.yml); "
            "these acts exist only in development (ADR-0016).",
            file=sys.stderr,
        )
        return 1

    try:
        if arguments.command == "purge":
            removed = purge(arguments.subject, explications_dir)
            print(f"{arguments.subject}: {removed} version(s) deleted.")
        else:
            user = getpass.getuser()
            done = validate_declared(Person(source=f"host:{user}", name=user), explications_dir)
            print(f"{len(done)} subject(s) validated" + (f": {', '.join(done)}" if done else "."))
    except ExplicationRefused as error:
        print(f"Refused: {error.reason}", file=sys.stderr)
        return 1

    print("The graph sees it at the next: python -m aistack.cli.timemachine_rebuild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

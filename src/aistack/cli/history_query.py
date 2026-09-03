from __future__ import annotations

import sys
from pathlib import Path

from aistack.history import (
    available_instants,
    available_stems,
    format_instant,
    observation_at,
    parse_instant,
)


GENERATED_DIR = Path("reports/generated")


def main() -> None:
    args = sys.argv[1:]

    if len(args) == 0:
        _print_stems()
        return

    stem = args[0]

    if len(args) == 1:
        _print_instants(stem)
        return

    _print_observation(stem, args[1])


def _print_stems() -> None:
    stems = available_stems(GENERATED_DIR)

    if not stems:
        print(f"No Observation History under {GENERATED_DIR}.")
        return

    print("Artifacts with Observation History:")
    for stem in stems:
        instants = available_instants(GENERATED_DIR, stem)
        print(f"- {stem} ({len(instants)} observed)")


def _print_instants(stem: str) -> None:
    instants = available_instants(GENERATED_DIR, stem)

    if not instants:
        print(f"No Observation History for {stem!r} under {GENERATED_DIR}.")
        raise SystemExit(2)

    print(f"{stem} was observed at:")
    for instant in instants:
        print(f"- {format_instant(instant)}")


def _print_observation(stem: str, raw_at: str) -> None:
    try:
        at = parse_instant(raw_at)
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(2) from None

    result = observation_at(GENERATED_DIR, stem, at)

    if result is None:
        print(
            f"No observation of {stem!r} at or before "
            f"{format_instant(at)} under {GENERATED_DIR}."
        )
        raise SystemExit(1)

    print(f"# {stem} as observed at {format_instant(result.observed_at)}")
    print(f"# (asked for at-or-before {format_instant(at)})")
    print(result.read())


if __name__ == "__main__":
    main()

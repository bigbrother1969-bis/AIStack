from __future__ import annotations

from collections.abc import Mapping

from aistack.contracts.development_flag import (
    DevelopmentFlagFinding,
    DevelopmentFlagPattern,
)


# The one pattern this heritage has actually observed.
#
# `aistack-selection-ui` ran permanently with Uvicorn's `--reload`,
# a flag meant to watch a mounted source tree for changes on a
# developer's own machine — measured live, 2026-09-03, as the root
# cause of the CPU incident `STD-0300` § VS-4 takes as its reference.
#
# A second pattern belongs here once a second real case names one,
# per `GOV-P-001` — not guessed at now to make this list look more
# complete than what has happened.
KNOWN_DEVELOPMENT_FLAGS = (
    DevelopmentFlagPattern(
        identifier="DEV-FLAG-001",
        pattern="--reload",
        interpretation=(
            "Uvicorn's development auto-reload flag is enabled — it "
            "watches the filesystem continuously, which is what "
            "consumed CPU while aistack-selection-ui was idle."
        ),
    ),
)


def find_development_flags(
    commands: Mapping[str, str],
    patterns: tuple[DevelopmentFlagPattern, ...] = KNOWN_DEVELOPMENT_FLAGS,
) -> tuple[DevelopmentFlagFinding, ...]:
    """
    Which containers' own launch command carries a declared
    development-only option.

    `STD-0300` § VS-4 criterion 4.3, read literally: "the
    development option enabled in a permanent service." Nothing
    here judges which service is "permanent" — that reading is the
    same one `qualify()` leaves to whoever reads a finding, not a
    filter applied before one exists. Every container's command is
    checked alike; a one-off container caught by this is a true
    reading of what its command contains, whatever a human later
    decides it means.

    A container can carry more than one declared pattern, and each
    produces its own finding — the same "one finding per rule that
    fired" `qualify()` already establishes, not one finding per
    container that merges what fired into a single line.

    Pure: `commands` and `patterns` are both already collected: no
    filesystem, no subprocess, nothing this function reads that was
    not handed to it.
    """

    return tuple(
        DevelopmentFlagFinding(
            container=container,
            pattern=candidate.pattern,
            interpretation=candidate.interpretation,
            command=command,
        )
        for container, command in commands.items()
        for candidate in patterns
        if candidate.pattern in command
    )

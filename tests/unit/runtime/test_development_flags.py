import pytest

from aistack.contracts.development_flag import (
    DevelopmentFlagFinding,
    DevelopmentFlagPattern,
)
from aistack.runtime.development_flags import (
    KNOWN_DEVELOPMENT_FLAGS,
    find_development_flags,
)


RELOAD = DevelopmentFlagPattern(
    identifier="DEV-FLAG-001",
    pattern="--reload",
    interpretation="Uvicorn's development auto-reload flag is enabled.",
)


# --------------------------------------------------------------------
# `DevelopmentFlagPattern` / `DevelopmentFlagFinding` themselves
# --------------------------------------------------------------------


def test_a_pattern_requires_every_field():

    with pytest.raises(ValueError, match="empty"):
        DevelopmentFlagPattern(identifier="X", pattern="", interpretation="y")


def test_a_finding_requires_its_pattern_present_in_its_own_command():
    """
    The same reasoning `RuntimeFinding` enforces non-empty evidence
    at construction: a finding that cites evidence it does not
    actually carry is worse than one that fails to construct.
    """

    with pytest.raises(ValueError, match="is not present"):
        DevelopmentFlagFinding(
            container="x",
            pattern="--reload",
            interpretation="y",
            command="/init",
        )


# --------------------------------------------------------------------
# `find_development_flags`
# --------------------------------------------------------------------


def test_a_command_carrying_the_pattern_is_flagged():

    findings = find_development_flags(
        {"aistack-selection-ui": "python3 -m uvicorn app:app --reload"},
        (RELOAD,),
    )

    assert len(findings) == 1
    assert findings[0].container == "aistack-selection-ui"
    assert findings[0].pattern == "--reload"


def test_a_command_without_the_pattern_is_not_flagged():

    findings = find_development_flags({"sonarr": "/init"}, (RELOAD,))

    assert findings == ()


def test_only_the_matching_container_in_a_batch_is_flagged():

    findings = find_development_flags(
        {
            "sonarr": "/init",
            "aistack-selection-ui": "uvicorn app:app --reload",
        },
        (RELOAD,),
    )

    assert [f.container for f in findings] == ["aistack-selection-ui"]


def test_a_container_matching_two_declared_patterns_produces_two_findings():

    debug = DevelopmentFlagPattern(
        identifier="DEV-FLAG-002",
        pattern="--debug",
        interpretation="A debug flag is enabled.",
    )

    findings = find_development_flags(
        {"x": "app --reload --debug"}, (RELOAD, debug)
    )

    assert {f.pattern for f in findings} == {"--reload", "--debug"}


def test_an_empty_command_set_flags_nothing():

    assert find_development_flags({}, (RELOAD,)) == ()


def test_the_known_patterns_are_used_by_default():

    findings = find_development_flags(
        {"aistack-selection-ui": "uvicorn app:app --reload"}
    )

    assert len(findings) == 1
    assert findings[0].pattern == KNOWN_DEVELOPMENT_FLAGS[0].pattern


def test_the_finding_carries_the_full_command_as_evidence():

    command = "python3 -m uvicorn app:app --host 0.0.0.0 --reload"

    findings = find_development_flags({"x": command}, (RELOAD,))

    assert findings[0].command == command

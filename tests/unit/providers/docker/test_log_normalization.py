from datetime import datetime, timezone

import pytest

from aistack.providers.docker import DockerProvider
from aistack.providers.docker.log_normalization import (
    normalize_log_evidence,
)


NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


def normalize(raw: str, depth: int = 100):
    return normalize_log_evidence(
        raw,
        subject="gluetun",
        provider="aistack.provider.docker",
        depth=depth,
        collected_at=NOW,
    )


def test_offsets_count_back_from_the_newest_line():
    """
    A reader asks how far back something appeared, not which
    index it held in a window whose start moves with every new
    line.
    """

    observation = normalize("oldest\nmiddle\nnewest\n")

    assert [(e.offset, e.text) for e in observation.entries] == [
        (2, "oldest"),
        (1, "middle"),
        (0, "newest"),
    ]


def test_the_terminating_newline_is_not_a_line():
    """
    `docker logs` ends its output with a newline. Splitting on it
    yields a trailing empty element no container ever printed.
    """

    assert len(normalize("one\ntwo\n").entries) == 2
    assert len(normalize("one\ntwo").entries) == 2


def test_no_output_yields_an_observation_with_no_entries():
    """
    "Nothing was printed" is a fact about the subject. Returning
    nothing would make it indistinguishable from "nothing was
    looked at".
    """

    observation = normalize("")

    assert observation.entries == ()
    assert observation.subject == "gluetun"
    assert observation.depth == 100


def test_lines_are_kept_verbatim():
    """
    No trimming, no case folding, no filtering. A signature that
    matched a line the pipeline had reworded would cite something
    that never appeared on the host — and comparison is the
    qualifier's business, declared per rule by
    `Signature.case_sensitive`.
    """

    raw = "  Your credentials might be WRONG  \n\tTLS Error\n"

    assert [e.text for e in normalize(raw).entries] == [
        "  Your credentials might be WRONG  ",
        "\tTLS Error",
    ]


def test_an_empty_line_between_two_others_is_a_line():

    observation = normalize("first\n\nthird\n")

    assert [e.text for e in observation.entries] == ["first", "", "third"]


def test_the_observation_carries_the_depth_that_was_asked_for():
    """
    A signature declaring a window deeper than what was collected
    cannot fire. Without the depth travelling alongside, *absent*
    and *out of range* would be the same result.
    """

    assert normalize("one\n", depth=2000).depth == 2000


def test_more_lines_than_depth_is_refused_by_the_contract():
    """
    `docker logs --tail N` returns at most N lines. If it ever
    returned more, the observation would be describing a window
    it did not read, and the contract refuses to exist.
    """

    with pytest.raises(ValueError, match="depth"):
        normalize("one\ntwo\nthree\n", depth=2)


def test_collecting_no_lines_is_refused_before_docker_is_called():
    """
    Reached without a Docker daemon: the guard precedes the
    subprocess call.
    """

    with pytest.raises(ValueError, match="observes nothing"):
        DockerProvider().collect_logs("gluetun", 0)


def test_the_observation_names_the_provider_that_produced_it():

    assert normalize("x\n").provider == "aistack.provider.docker"

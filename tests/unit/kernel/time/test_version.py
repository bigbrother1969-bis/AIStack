from dataclasses import FrozenInstanceError

import pytest

from aistack.kernel.time import VersionId, VersionSequence


def test_version_id_carries_subject_and_sequence() -> None:
    version = VersionId(subject="jellyfin.cpu-decision", sequence=1)

    assert version.subject == "jellyfin.cpu-decision"
    assert version.sequence == 1


def test_version_id_is_immutable() -> None:
    version = VersionId(subject="s", sequence=1)

    with pytest.raises(FrozenInstanceError):
        version.sequence = 2


def test_version_sequence_starts_at_one_and_is_monotonic_per_subject() -> None:
    sequence = VersionSequence()

    first = sequence.next("jellyfin.cpu-decision")
    second = sequence.next("jellyfin.cpu-decision")

    assert first == VersionId(subject="jellyfin.cpu-decision", sequence=1)
    assert second == VersionId(subject="jellyfin.cpu-decision", sequence=2)


def test_version_sequence_scopes_subjects_independently() -> None:
    """
    Two unrelated subjects must not advance each other's counter —
    the reason `VersionId` is scoped by `subject` rather than drawn
    from one global sequence.
    """

    sequence = VersionSequence()

    sequence.next("jellyfin.cpu-decision")
    sequence.next("jellyfin.cpu-decision")
    first_trace_version = sequence.next("request-001.trace")

    assert first_trace_version == VersionId(subject="request-001.trace", sequence=1)

"""
`aistack.history.subject_names` — a subject becomes one file name
inside its stream's directory, whatever it holds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.history.subject_names import stem_for_subject, subject_for_stem

SUBJECTS = [
    "booklore_db",
    "gpu",
    "/media/BACKUP/nextcloud",
    "../../etc/passwd",
    ".",
    "..",
    "a%2Fb",
    "100%",
    "C:\\data",
]


@pytest.mark.parametrize("subject", SUBJECTS)
def test_a_subject_becomes_one_name_inside_the_directory(tmp_path: Path, subject: str):
    stem = stem_for_subject(subject)

    path = tmp_path / f"{stem}.json"

    assert path.parent == tmp_path
    assert stem not in {".", ".."}
    assert "/" not in stem


@pytest.mark.parametrize("subject", SUBJECTS)
def test_the_stem_gives_its_subject_back(subject: str):
    assert subject_for_stem(stem_for_subject(subject)) == subject


def test_a_plain_name_keeps_the_file_it_always_had():
    assert stem_for_subject("booklore_db") == "booklore_db"
    assert stem_for_subject("immich-server.1") == "immich-server.1"


def test_an_empty_subject_is_refused():
    with pytest.raises(ValueError):
        stem_for_subject("")

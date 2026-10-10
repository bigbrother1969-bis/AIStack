"""
One subject, one file name — never a path.

Some histories keep one file per subject, `<output_dir>/<subject>.json`.
A subject can be a filesystem path (`/media/BACKUP/nextcloud`); joined as
is, an absolute subject replaces `output_dir` (`Path("a") / "/media/x"`
is `/media/x`) and `/` or `..` escapes it.

A plain name is kept unchanged; only `%`, `/`, `\\` (and a stem that
would be `.` or `..`) are percent-encoded, which `subject_for_stem`
reverses.
"""

from __future__ import annotations

import re

_ENCODED = re.compile(r"%(25|2F|5C|2E)")
_DECODED = {"25": "%", "2F": "/", "5C": "\\", "2E": "."}


def stem_for_subject(subject: str) -> str:
    """The single path component a subject's history is stored under."""

    if not subject:
        raise ValueError("a history subject cannot be empty")

    stem = subject.replace("%", "%25").replace("/", "%2F").replace("\\", "%5C")
    if stem in {".", ".."}:
        stem = stem.replace(".", "%2E")
    return stem


def subject_for_stem(stem: str) -> str:
    """The subject a stem was made from (`stem_for_subject`'s inverse)."""

    return _ENCODED.sub(lambda match: _DECODED[match.group(1)], stem)

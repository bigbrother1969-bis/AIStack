"""
One subject, one file name — never a path.

AI Reasoning History and the Explications stream keep one file per
subject, `<output_dir>/<subject>.json`. A subject is whatever a
finding names: a container (`booklore_db`), but also a filesystem
path (`/media/BACKUP/nextcloud` for a backup finding). Joined as is,
an absolute subject replaces `output_dir` altogether
(`Path("a") / "/media/x.json"` is `/media/x.json`), and a subject
holding `/` or `..` lands outside it — found 2026-10-03 when the
suite, on GIGABYTE, tried to write `/media/BACKUP/nextcloud.json`.

The stem keeps every subject that was already a plain name exactly as
it was, so existing histories keep their file; only `%` and `/` (and
a stem that would be `.` or `..`) are percent-encoded, which
`subject_for_stem` reverses.
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

"""Reading what the tripwires recorded (`OPS-0012`)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aistack.quarantine.tripwire import HITS


@dataclass(frozen=True)
class Hit:
    at: str
    kind: str
    target: str
    caller: str
    program: str = ""


def read_hits(path: Path = HITS) -> tuple[Hit, ...]:
    """Every recorded use, oldest first; a line that cannot be read is skipped."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ()
    hits = []
    for line in text.splitlines():
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if not isinstance(data, dict) or not data.get("target"):
            continue
        hits.append(
            Hit(
                at=str(data.get("at") or ""),
                kind=str(data.get("kind") or ""),
                target=str(data["target"]),
                caller=str(data.get("caller") or ""),
                program=str(data.get("program") or ""),
            )
        )
    return tuple(hits)

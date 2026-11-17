"""
A declaration edited by hand on the host is observed and recorded
(`ADR-0027` § 12).

The owner edits the files of the configuration directory with an editor:
nothing says who, why, or what the file held before. For each declaration
the package ships, the host keeps a snapshot of the file as it was last seen,
under `declarations/seen/` in the data directory. A file whose digest is no
longer the snapshot's was edited since:

- *reference*: no snapshot yet. The file as it is becomes the reference; no
  change is invented.
- *follow*: the digest is the one `declaration.write` recorded last for that
  file (a screen wrote it, and `declaration-change` says so): the snapshot
  follows, nothing is recorded twice.
- *edited*: anything else. The snapshot moves to the new content, the
  previous one is kept as `<name>.avant-observe-<date>` beside it, and the
  change is recorded in the stream `declaration-observed` (when, file, both
  digests, the copy). **Never the content.**

`observe` reads and decides; `apply` writes, through the Kernel's
transaction service.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from aistack.declaration.change import write_declaration
from aistack.declaration.validate import last_valid_copy, problem
from aistack.generators.history import write_artifact_with_history
from aistack.instance.first_start import fingerprint
from aistack.kernel.services.transactions import TransactionServices

SEEN = Path("declarations") / "seen"
RECORD = "declaration-observed.json"
CHANGE_STREAM = Path("history") / "declaration-change"
AUTHOR = "by hand on the host"

REFERENCE = "reference"
FOLLOW = "follow"
EDITED = "edited"


@dataclass(frozen=True)
class Observed:
    """One declaration whose file is not what the snapshot holds. Digests only."""

    name: str
    kind: str
    before: str
    after: str


def seen_path(generated_dir: Path, name: str) -> Path:
    return generated_dir / SEEN / name


def observe(config_dir: Path, generated_dir: Path, shipped: list[Path]) -> list[Observed]:
    """What changed in `config_dir` since the snapshots. Writes nothing."""

    governed = _governed(generated_dir)
    found: list[Observed] = []

    for source in shipped:
        name = source.name
        current = config_dir / name

        if not current.is_file():
            continue

        digest = fingerprint(current)
        snapshot = seen_path(generated_dir, name)

        if not snapshot.is_file():
            found.append(Observed(name, REFERENCE, "", digest))
            continue

        before = fingerprint(snapshot)

        if before == digest:
            continue

        kind = FOLLOW if governed.get(name) == digest else EDITED
        found.append(Observed(name, kind, before, digest))

    return found


def apply(
    transactions: TransactionServices,
    config_dir: Path,
    generated_dir: Path,
    observed: list[Observed],
) -> tuple[list[dict[str, object]], list[str]]:
    """
    Move the snapshots to what was observed and record the hand edits.
    Returns the records written and the problems. A file that changed again
    since it was observed is left to the next pass; one that is not UTF-8
    is a problem, and is left as it is.
    """

    records: list[dict[str, object]] = []
    problems: list[str] = []

    for item in observed:
        current = config_dir / item.name

        if not current.is_file() or fingerprint(current) != item.after:
            continue

        try:
            content = current.read_bytes().decode("utf-8")

        except UnicodeDecodeError:
            problems.append(f"{item.name}: not UTF-8, not observed")
            continue

        reason = {
            REFERENCE: "first observation: the file as it is becomes the reference",
            FOLLOW: "written by declaration.write: already recorded there",
            EDITED: "edited by hand: the file differs from the snapshot",
        }[item.kind]

        result = write_declaration(
            transactions,
            generated_dir,
            seen_path(generated_dir, item.name),
            content,
            AUTHOR,
            reason,
            copy_label="observe",
            record=False,
        )

        if item.kind != EDITED:
            continue

        error = problem(item.name, current, generated_dir)
        record: dict[str, object] = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "author": AUTHOR,
            "name": item.name,
            "path": str(current),
            "before": item.before,
            "after": item.after,
            "copy": result["copy"],
            "valid": not error,
            "error": error,
            "last_valid_copy": last_valid_copy(generated_dir, item.name, seen_path(generated_dir, item.name).parent) if error else "",
        }
        write_artifact_with_history(json.dumps(record, ensure_ascii=False, indent=2) + "\n", generated_dir / RECORD)
        records.append(record)

    return records, problems


def _governed(generated_dir: Path) -> dict[str, str]:
    """For each file name, the digest `declaration.write` wrote last."""

    last: dict[str, tuple[str, str]] = {}

    for path in sorted((generated_dir / CHANGE_STREAM).glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))

        except (OSError, ValueError):
            continue

        if not isinstance(record, dict) or not record.get("path") or not record.get("after"):
            continue

        name = Path(str(record["path"])).name
        at = str(record.get("at", ""))

        if name not in last or at >= last[name][0]:
            last[name] = (at, str(record["after"]))

    return {name: digest for name, (_, digest) in last.items()}

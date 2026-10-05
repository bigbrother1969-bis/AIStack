"""
`python -m aistack.cli.quarantine_report` — where the quarantine stands
(`OPS-0012`): each item, its state, the uses its tripwires recorded,
its review date and what to amend when it is deleted.

Reads `src/aistack/quarantine/register.yml` and
`reports/generated/quarantine/hits.jsonl` (run it from the checkout, or
with `docker compose exec web`); changes nothing.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from aistack.contracts.quarantine_reading import READY, USED
from aistack.quarantine.status import read_statuses

LABELS = {USED: "UTILISÉ", READY: "PRÊT À EFFACER"}


def report(today: date, root: Path | None = None) -> str:
    lines = [f"Quarantaine (OPS-0012) au {today.isoformat()}"]
    found = read_statuses(today)
    for status in found:
        entry = status.entry
        label = LABELS.get(status.state, f"surveillé jusqu'au {entry.review_after.isoformat()}")
        lines.append("")
        lines.append(f"{entry.id}  {label}  —  {len(status.hits)} utilisation(s)")
        for path in entry.paths:
            missing = root is not None and not (root / path).exists()
            lines.append(f"    {path}{'   (ABSENT)' if missing else ''}")
        for hit in status.hits[-3:]:
            lines.append(f"    ! {hit.at}  {hit.target}  par {hit.caller}  ({hit.program})")
        if entry.amend:
            lines.append(f"    à amender à l'effacement : {', '.join(entry.amend)}")
    used = sum(1 for status in found if status.state == USED)
    ready = sum(1 for status in found if status.state == READY)
    lines.append("")
    lines.append(f"{len(found)} élément(s) : {used} utilisé(s), {ready} prêt(s) à effacer")
    return "\n".join(lines)


def main() -> None:
    root = Path.cwd()
    print(report(date.today(), root if (root / ".git").exists() else None))


if __name__ == "__main__":
    main()

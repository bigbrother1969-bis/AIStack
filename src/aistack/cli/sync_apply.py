"""
`python -m aistack.cli.sync_apply` — the generalized sync's host executor (ADR-0022 § 6).

    python -m aistack.cli.sync_apply                 apply every pair whose selection changed,
                                                     and every hour the others
    python -m aistack.cli.sync_apply music--phone    apply this pair now
    python -m aistack.cli.sync_apply --dry-run ...   say what it would do
    python -m aistack.cli.sync_apply --list          every pair and its last application

Run on the host, from the checkout, by the account that owns the
content disks: `aistack-sync.timer` starts it every two minutes
(`deploy/systemd/aistack-sync.service`). A pair with no recorded
selection is never touched. One executor at a time.
"""

from __future__ import annotations

import argparse
import fcntl
import sys
from datetime import datetime, timezone
from pathlib import Path

from aistack.cli.sandbox import data_dir
from aistack.sync.declaration import SYNCTHING, load_sync_declaration, split_pair
from aistack.sync.screen import apply_pair, due, read_applied, selection_file, waiting


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.sync_apply", description=__doc__.split("\n\n")[0])
    parser.add_argument("pairs", nargs="*", help="content--destination, now")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    declaration = load_sync_declaration()
    generated = data_dir(root or Path.cwd())
    now = datetime.now(timezone.utc)
    syncthing_pairs = [
        pair for pair in declaration.pair_ids()
        if declaration.destinations[split_pair(pair)[1]].kind == SYNCTHING
    ]

    if args.list:
        for pair in syncthing_pairs:
            if not selection_file(generated, pair).exists():
                continue
            record = read_applied(generated, pair) or {}
            state = "en attente" if waiting(generated, pair) else "appliquée"
            print(
                f"{pair:<24} {state:<11} {record.get('at', '-'):<26} "
                f"+{record.get('linked', 0)} -{record.get('removed', 0)} "
                f"{int(record.get('selected_bytes') or 0) / 1e9:.1f} Go"
                + (f"  refus : {record['refused']}" if record.get("refused") else "")
            )
        return 0

    unknown = [pair for pair in args.pairs if pair not in syncthing_pairs]
    if unknown:
        print(f"Unknown pair(s): {', '.join(unknown)} (known: {', '.join(syncthing_pairs)})")
        return 2
    chosen = args.pairs or [pair for pair in syncthing_pairs if due(generated, pair, now)]
    if not chosen:
        return 0

    lock = generated / "sync" / "executor.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another sync executor is running.")
            return 0
        problems = 0
        for pair in chosen:
            if not selection_file(generated, pair).exists():
                print(f"{pair}: no selection recorded, left as it is")
                continue
            record = apply_pair(declaration, generated, pair, now, dry_run=args.dry_run)
            line = (
                f"{pair}: +{record['linked']} ~{record['relinked']} -{record['removed']} "
                f"={record['unchanged']} ({record['seconds']} s)"
            )
            if record.get("refused"):
                line += f" — refused: {record['refused']}"
                problems += 1
            if record.get("failed"):
                line += f" — {len(record['failed'])} failure(s), first: {record['failed'][0]}"
                problems += 1
            print(line, flush=True)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

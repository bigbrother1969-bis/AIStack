"""
`python -m aistack.cli.data_budget` — AIStack's data against its disk budget (ADR-0021).

    python -m aistack.cli.data_budget                       what the data takes, by directory,
                                                            its pace, and when the budget is reached
    python -m aistack.cli.data_budget --compress --dry-run  what compressing the old observations
                                                            would gain
    python -m aistack.cli.data_budget --compress            compress them now (nothing is deleted)

The vigil compresses once a day on its own. In the Docker installation:
`docker compose exec web python -m aistack.cli.data_budget`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aistack.data_budget.budget import compress_old, human_size, load_data_budget, measure

GENERATED_DIR = Path("reports/generated")


def main(argv: list[str] | None = None, generated: Path = GENERATED_DIR) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.data_budget", description=__doc__.split("\n\n")[0])
    parser.add_argument("--compress", action="store_true", help="compress the observations older than the window")
    parser.add_argument("--dry-run", action="store_true", help="with --compress: say what it would gain, change nothing")
    args = parser.parse_args(argv)

    budget = load_data_budget()
    reading = measure(generated, budget)
    print(
        f"Données d'AIStack ({reading.directory}) : {human_size(reading.used_bytes)} sur "
        f"{human_size(reading.budget_bytes)} ({reading.percent} %), {reading.files} fichiers"
    )
    if reading.daily_bytes is not None:
        print(f"  rythme des 7 derniers jours : {human_size(reading.daily_bytes)} par jour")
    if reading.days_left is not None:
        print(f"  budget atteint dans environ {reading.days_left} jour(s) à ce rythme")
    for name, size in reading.largest:
        print(f"  {name:<28} {human_size(size):>10}")

    if args.compress:
        done = compress_old(generated, budget, dry_run=args.dry_run)
        verb = "à compresser" if args.dry_run else "compressées"
        print(
            f"Observations de plus de {budget.compress_after.days} jours {verb} : {done.files} "
            f"({human_size(done.before)} → {human_size(done.after)})"
        )
        for problem in done.problems:
            print(f"  problème : {problem}")
        return 1 if done.problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

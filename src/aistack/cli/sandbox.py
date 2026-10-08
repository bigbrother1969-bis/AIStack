"""
`python -m aistack.cli.sandbox` — sandbox restore (`ADR-0018`).

    python -m aistack.cli.sandbox recipes            the services it knows
    python -m aistack.cli.sandbox restore wordpress  restore, check, time, remove
    python -m aistack.cli.sandbox cleanup            what an interrupted run left

Run on the host, from the checkout (`source scripts/dev-env.sh`), by a
user allowed to run `docker`. Never touches a live container: it reads
their image, nothing else. The report is written to the data directory
(`AISTACK_DATA_DIR` from `.env`, else `reports/generated`), under
`sandbox/`, and printed with the `pra_tests.yml` entry it proposes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aistack.sandbox.declaration import SandboxDeclaration, load_sandbox_declaration
from aistack.sandbox.run import Runner, SandboxRun, StepFailed, cleanup, docker_runner
from aistack.sandbox.aistack_archive import restore_aistack
from aistack.sandbox.wordpress import restore_wordpress

RECIPES = {"wordpress_mariadb": restore_wordpress, "aistack_archive": restore_aistack}


def data_dir(root: Path) -> Path:
    """The data directory as `scripts/backup_aistack.sh` finds it."""

    value = ""
    env = root / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("AISTACK_DATA_DIR="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not value:
        return root / "reports" / "generated"
    path = Path(value)
    return path if path.is_absolute() else root / value.removeprefix("./")


def restore(
    service: str,
    declaration: SandboxDeclaration,
    generated_dir: Path,
    runner: Runner = docker_runner,
) -> tuple[SandboxRun, Path]:
    recipe = declaration.recipes.get(service)
    if recipe is None:
        known = ", ".join(sorted(declaration.recipes)) or "none"
        raise SystemExit(f"No sandbox recipe for `{service}` (known: {known}).")
    run = SandboxRun(service, declaration.run_root, runner)
    try:
        RECIPES[recipe.kind](run, recipe, expansion=declaration.expansion, margin_gib=declaration.margin_gib)
    except StepFailed as error:
        run.failure = str(error)
    except KeyboardInterrupt:
        run.failure = "interrupted"
    finally:
        run.teardown()
    return run, run.write_report(generated_dir)


def summary(run: SandboxRun) -> str:
    lines = [f"Sandbox {run.run_id}: {'SUCCÈS' if run.succeeded else 'ÉCHEC'}"]
    if run.failure:
        lines.append(f"  arrêt : {run.failure}")
    for step in run.steps:
        lines.append(f"  [{'ok' if step.ok else 'KO'}] {step.name} ({step.seconds:g} s){' — ' + step.detail if step.detail else ''}")
    for check in run.checks:
        mark = "ok" if check.ok else ("KO" if check.required else "--")
        lines.append(f"  [{mark}] {check.name}: {check.observed}")
    if run.recovery_seconds is not None:
        lines.append(f"  temps de reprise mesuré : {run.recovery_seconds:g} s")
    lines.append("")
    lines.append("Entrée proposée pour pra_tests.yml (à copier si tu la valides) :")
    lines.append(run.proposed_entry())
    return "\n".join(lines)


def main(argv: list[str] | None = None, runner: Runner = docker_runner, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.sandbox", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("recipes")
    one = sub.add_parser("restore")
    one.add_argument("service")
    sub.add_parser("cleanup")
    args = parser.parse_args(argv)

    declaration = load_sandbox_declaration()
    if args.command == "recipes":
        for name, recipe in sorted(declaration.recipes.items()):
            print(f"{name}  ({recipe.kind})  {recipe.backup_dir}")
        return 0
    if args.command == "cleanup":
        done = cleanup(declaration.run_root, runner)
        print("\n".join(done) if done else "Nothing left by a sandbox run.")
        return 0

    run, report = restore(args.service, declaration, data_dir(root or Path.cwd()), runner)
    print(summary(run))
    print(f"\nRapport : {report}")
    return 0 if run.succeeded else 1


if __name__ == "__main__":
    sys.exit(main())

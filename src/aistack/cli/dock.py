"""
`python -m aistack.cli.dock` — the dock executor (`ADR-0019` § 3–5).

    python -m aistack.cli.dock run         execute the validated proposals, oldest first
    python -m aistack.cli.dock list        every proposal and its state
    python -m aistack.cli.dock show <id>   one proposal: its why, its history, its operations

Run on the host, from the checkout, by the account AIStack runs as —
`aistack-dock.timer` starts `run` every two minutes
(`deploy/systemd/aistack-dock.service`). One executor at a time: a
second `run` while one works says so and leaves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aistack.cli.sandbox import data_dir, restore
from aistack.dock import proposals as store
from aistack.dock.declaration import load_dock_declaration
from aistack.dock.executor import Dock, exclusive
from aistack.kernel.bootstrap.default import create_kernel
from aistack.sandbox.declaration import load_sandbox_declaration
from aistack.sandbox.run import Runner, docker_runner


def describe(proposal: store.Proposal) -> str:
    lines = [
        f"{proposal.id} — {proposal.service} — {proposal.status}",
        f"  pourquoi : {proposal.why}",
        f"  proposé par {proposal.proposed_by} le {proposal.proposed_at}"
        + (f", décidé par {proposal.decided_by} le {proposal.decided_at}" if proposal.decided_by else ""),
    ]
    for change in proposal.changes:
        lines.append(f"  {change.container} : {change.image} {change.from_digest[:19]}… → {change.to_digest[:19]}…")
    if proposal.operations:
        lines.append("  opérations :")
        for operation in proposal.operations:
            mark = {"done": "ok", "failed": "KO"}.get(str(operation.get("status")), "..")
            detail = f" — {operation['detail']}" if operation.get("detail") else ""
            lines.append(f"    [{mark}] {operation['name']} ({operation.get('seconds', 0):g} s){detail}")
    if proposal.history:
        last = proposal.history[-1]
        lines.append(f"  dernier événement : {last['event']} ({last['at']}){' — ' + last['detail'] if last.get('detail') else ''}")
    return "\n".join(lines)


def main(argv: list[str] | None = None, runner: Runner = docker_runner, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.dock", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    sub.add_parser("list")
    one = sub.add_parser("show")
    one.add_argument("proposal")
    args = parser.parse_args(argv)

    generated_dir = data_dir(root or Path.cwd())
    if args.command == "list":
        found = store.all_proposals(generated_dir)
        for proposal in found:
            print(f"{proposal.id}  {proposal.status}  {proposal.why[:60]}")
        if not found:
            print("Aucune proposition.")
        return 0
    if args.command == "show":
        try:
            print(describe(store.load(generated_dir, args.proposal)))
        except store.ProposalRefused:
            print(f"Pas de proposition `{args.proposal}`.")
            return 1
        return 0

    with exclusive(generated_dir) as mine:
        if not mine:
            print("Un autre exécuteur du quai est déjà au travail.")
            return 0
        dock = Dock(
            generated_dir=generated_dir,
            services=load_dock_declaration(),
            sandbox=load_sandbox_declaration(),
            restorer=restore,
            runner=runner,
            # The kernel's transaction service: the change runs through
            # its executor, its operations registered by kind (ADR-0019 § 6).
            transactions=create_kernel().services.transactions,
            progress=lambda line: print(line, flush=True),
        )
        for closed in dock.close_interrupted():
            print(f"{closed} : interrompue lors d'une exécution précédente, close en échec.")
        done = dock.run_all()
    for proposal in done:
        print()
        print(describe(proposal))
    return 0 if all(p.status == store.APPLIED for p in done) else 1


if __name__ == "__main__":
    sys.exit(main())

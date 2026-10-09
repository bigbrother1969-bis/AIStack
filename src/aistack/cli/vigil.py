"""
`python -m aistack.cli.vigil` — the vigil (2.0, tranche 2).

    python -m aistack.cli.vigil                one pass
    python -m aistack.cli.vigil --every 900    a pass every 15 minutes, for ever
    python -m aistack.cli.vigil --dry-run      one pass, the message printed, not sent
    python -m aistack.cli.vigil --test         send a test message to Gotify

A pass renders the health cockpit and the console again (so their score
is never older than one pass), compares the health and the dock's
proposals with the previous pass, and sends what changed to Gotify in
one message (`aistack.vigil.notify`). In the Docker installation it is
the `vigil` service, run every 15 minutes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from aistack.api_keys import apply_to_environ
from aistack.data_budget.budget import compact_if_due, human_size, load_data_budget
from aistack.dock import proposals as store
from aistack.i18n import default_languages, translator_for
from aistack.instance.yaml import load_instance_config_yaml
from aistack.config import configured
from aistack.vigil import notify, snapshot

GENERATED_DIR = Path("reports/generated")
INSTANCE_CONFIG = configured(Path(__file__).resolve().parents[1] / "instance" / "definitions" / "instance_config.yml")
RENDERS = ("aistack.cli.health_render", "aistack.cli.console_render")


def _render() -> None:
    for module in RENDERS:
        done = subprocess.run([sys.executable, "-m", module], capture_output=True, text=True, timeout=900)
        if done.returncode != 0:
            print(f"{module}: exit {done.returncode}: {(done.stderr or done.stdout).strip()[-400:]}", flush=True)


def _compact(generated: Path) -> None:
    """Once a day, the observations older than the data budget's window
    are compressed (ADR-0021)."""

    try:
        done = compact_if_due(generated, load_data_budget())
    except (OSError, ValueError) as error:
        print(f"vigil: compaction skipped ({error})", flush=True)
        return
    if done is not None and (done.files or done.problems):
        print(
            f"vigil: {done.files} old observation(s) compressed "
            f"({human_size(done.before)} → {human_size(done.after)})"
            + (f", {len(done.problems)} problem(s): {done.problems[0]}" if done.problems else ""),
            flush=True,
        )


def _console_url() -> str:
    try:
        return load_instance_config_yaml(INSTANCE_CONFIG).service_url("web_lan") + "/console.html"
    except (OSError, ValueError):
        return ""


def one_pass(generated: Path, gotify: notify.Gotify | None, dry_run: bool, render: bool = True) -> int:
    _compact(generated)
    if render:
        _render()
    t = translator_for(default_languages().reference)
    previous = notify.read_state(generated)
    found, current = notify.events(t, previous, snapshot.read(generated), store.all_proposals(generated))
    message = notify.compose(t, found)
    if message is None:
        print("vigil: nothing new" + ("" if previous.known else " (first pass: what is there is noted)"), flush=True)
    elif dry_run or gotify is None:
        print(f"vigil: {message.title}\n{message.body}", flush=True)
        if gotify is None and not dry_run:
            print(f"vigil: notifications off ({notify.URL_VARIABLE} / {notify.TOKEN_VARIABLE} not set)", flush=True)
    else:
        try:
            gotify.send(message, click=_console_url())
            print(f"vigil: sent — {message.title}", flush=True)
        except OSError as error:
            # Not noted: the same events are tried again at the next pass.
            print(f"vigil: Gotify did not answer ({error}); tried again next pass", flush=True)
            return 1
    if not dry_run:
        notify.write_state(generated, current)
    return 0


def main(argv: list[str] | None = None, generated: Path = GENERATED_DIR) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.vigil", description=__doc__.split("\n\n")[0])
    parser.add_argument("--every", type=int, default=0, help="seconds between passes; one pass when absent")
    parser.add_argument("--dry-run", action="store_true", help="print the message instead of sending it")
    parser.add_argument("--test", action="store_true", help="send a test message")
    parser.add_argument("--no-render", action="store_true", help="compare only, without rendering again")
    args = parser.parse_args(argv)

    # The keys entered from Settings (2026-10-09), then each pass again.
    apply_to_environ(generated)
    gotify = notify.Gotify.from_environment()
    if args.test:
        if gotify is None:
            print(f"{notify.URL_VARIABLE} and {notify.TOKEN_VARIABLE} are not set (.env.web).")
            return 2
        t = translator_for(default_languages().reference)
        try:
            gotify.send(notify.Message("AIStack", t("notify.test"), notify.NORMAL), click=_console_url())
        except OSError as error:
            print(f"Gotify did not take the message: {error}")
            return 1
        print("Test message sent.")
        return 0

    if not args.every:
        return one_pass(generated, gotify, args.dry_run, render=not args.no_render)
    while True:
        apply_to_environ(generated)
        one_pass(generated, notify.Gotify.from_environment(), args.dry_run, render=not args.no_render)
        time.sleep(args.every)


if __name__ == "__main__":
    sys.exit(main())

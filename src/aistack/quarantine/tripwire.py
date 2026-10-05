"""
The tripwire every quarantined Python module calls on import
(`OPS-0012`): one line in its header,

    from aistack.quarantine.tripwire import tripwire; tripwire(__name__)

**It never stops anything.** A quarantined module is in quarantine
because nothing seemed to use it; if something does, the use is
recorded and a warning printed, and the program goes on exactly as it
would have — finding out, not breaking, is the point of the quarantine.

**An inventory is not a use either.** `conformance.inventory` imports
every module of the package to read its contracts, and the context
bundle export runs it: inside `inspecting()`, nothing is recorded.

**Imports made by the test suite are not uses.** The tests of a
quarantined module stay until the module is deleted, and they import it
every run; what the quarantine watches is the application, the CLIs and
the scripts. A process that has loaded pytest records nothing.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

HITS = Path("reports/generated/quarantine/hits.jsonl")

_inspecting = 0


@contextmanager
def inspecting() -> Iterator[None]:
    """Import everything for a look at the code, not to use it."""

    global _inspecting
    _inspecting += 1
    try:
        yield
    finally:
        _inspecting -= 1


class QuarantinedCodeUsed(UserWarning):
    """Code in quarantine was used: it is not dead after all."""


def _caller() -> str:
    """Who imported the quarantined module: the first frame, outside the
    import machinery, below the module's own."""

    frames = [
        frame
        for frame in reversed(traceback.extract_stack())
        if "importlib" not in frame.filename
        and not frame.filename.startswith("<frozen")
        and not frame.filename.endswith("tripwire.py")
    ]
    # frames[0] is the quarantined module calling its tripwire.
    if len(frames) < 2:
        return "command line"
    return f"{frames[1].filename}:{frames[1].lineno}"


def record(target: str, kind: str, caller: str, hits: Path = HITS) -> None:
    """Append one use of `target` to the hits file; never raise."""

    line = {
        "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "kind": kind,
        "target": target,
        "caller": caller,
        "program": " ".join(sys.argv)[:200] or sys.executable,
        "pid": os.getpid(),
    }
    try:
        hits.parent.mkdir(parents=True, exist_ok=True)
        with hits.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _run_as_program() -> tuple[str, str]:
    """What `__main__` is: the module `python -m` ran, else the file."""

    main = sys.modules.get("__main__")
    spec = getattr(main, "__spec__", None)
    if spec is not None and spec.name:
        return spec.name, "module"
    path = Path(getattr(main, "__file__", "") or "unknown")
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve())), "script"
    except ValueError:
        return str(path), "script"


def tripwire(module: str, hits: Path = HITS) -> None:
    if "pytest" in sys.modules or _inspecting:
        return
    kind = "module"
    if module == "__main__":
        module, kind = _run_as_program()
    caller = _caller()
    warnings.warn(
        f"{module} is in quarantine (OPS-0012) and was just imported by {caller}: "
        f"it is not dead code — take it out of src/aistack/quarantine/register.yml",
        QuarantinedCodeUsed,
        stacklevel=3,
    )
    record(module, kind, caller, hits)

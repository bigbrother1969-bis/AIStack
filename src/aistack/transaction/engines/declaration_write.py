"""
Knowledge Transaction - the engine of `declaration.write`.

A declaration a person changes is written whole, beside its final name
and moved into place, so a reader never opens half a file. When the
file already holds something else, that is kept beside it first, as
`<name>.avant-<UTC date>-<time>`. Nothing is written when the content
is the one the file already holds.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from aistack.transaction.contracts.declaration_write import DeclarationWrite
from aistack.transaction.interfaces.operation_engine import OperationEngine


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DeclarationWriteEngine(OperationEngine):
    """Returns what was done, in plain values: path, changed, copy and both digests."""

    def __init__(self, clock: Callable[[], datetime] = _now) -> None:
        self._clock = clock

    def execute(self, payload: object) -> object:
        if not isinstance(payload, DeclarationWrite):
            raise TypeError("DeclarationWriteEngine expects a DeclarationWrite payload.")

        path = payload.path
        after = payload.content.encode("utf-8")
        before = path.read_bytes() if path.exists() else None

        if before == after:
            return {"path": str(path), "changed": False, "copy": "", "before": _digest(after), "after": _digest(after)}

        path.parent.mkdir(parents=True, exist_ok=True)
        kept = self._keep(path, payload.copy_label) if before is not None else None

        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_bytes(after)
            if before is not None:
                shutil.copymode(path, temporary)
            temporary.replace(path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

        return {
            "path": str(path),
            "changed": True,
            "copy": str(kept) if kept is not None else "",
            "before": _digest(before) if before is not None else "",
            "after": _digest(after),
        }

    def _keep(self, path: Path, label: str) -> Path:
        stamp = self._clock().strftime("%Y%m%d-%H%M%S")
        head = f"{path.name}.avant-{label}-{stamp}" if label else f"{path.name}.avant-{stamp}"
        copy = path.with_name(head)
        suffix = 1
        while copy.exists():
            copy = path.with_name(f"{head}-{suffix}")
            suffix += 1
        shutil.copy2(path, copy)
        return copy

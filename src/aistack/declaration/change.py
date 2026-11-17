"""
Write a declaration through the Kernel's transaction service, and keep a
record of the change.

The record is one file per change, in the stream `declaration-change`
under the data directory (`declaration-change.json`, the latest, and
`history/declaration-change/`, every one): when, who, why, which file,
the digest of the file before and after, and the copy kept. It holds
neither the content nor anything secret: the digests say that it changed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.services.transactions import TransactionServices
from aistack.transaction.contracts.declaration_write import KIND, DeclarationWrite
from aistack.transaction.contracts.operation import Operation
from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.contracts.transaction_status import TransactionStatus

RECORD = "declaration-change.json"


class DeclarationNotWritten(RuntimeError):
    """The transaction failed: `error` is what the operation said."""

    def __init__(self, path: Path, error: str) -> None:
        super().__init__(f"{path} was not written: {error}")
        self.path = path
        self.error = error


def write_declaration(
    transactions: TransactionServices,
    generated_dir: Path,
    path: Path,
    content: str | None,
    author: str,
    reason: str,
    copy_label: str = "",
    record: bool = True,
) -> dict[str, object]:
    """
    Write `content` to `path` (`None`: take the file away, keeping the
    previous one) as one `declaration.write` operation; return what the
    operation did. A change that changed nothing leaves no record, and
    `record=False` leaves none for a change that did (a caller that keeps its
    own, as `aistack.declaration.observe` does).
    """

    operation = Operation(
        name=f"{'write' if content is not None else 'remove'} {path.name}",
        kind=KIND,
        payload=DeclarationWrite(
            path=path, content=content, author=author, reason=reason, copy_label=copy_label
        ),
    )
    transaction = transactions.executor.execute(Transaction(operations=[operation]))

    if transaction.status is not TransactionStatus.SUCCEEDED:
        raise DeclarationNotWritten(path, operation.error)

    result = operation.result
    assert isinstance(result, dict)

    if result["changed"] and record:
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "author": author,
            "reason": reason,
            **result,
        }
        write_artifact_with_history(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", generated_dir / RECORD)

    return result

"""
Bring a device's folder to a selection through the Kernel's transaction
service (`selection.materialise`, `ADR-0027` § 11).
"""

from __future__ import annotations

from pathlib import Path

from aistack.generators.filesystem.hardlink import MaterialisationReport
from aistack.kernel.catalog import Catalog
from aistack.kernel.services.transactions import TransactionServices
from aistack.selection.capacity import CapacityVerdict
from aistack.selection.subtree import SubtreeResolution
from aistack.transaction.contracts.operation import Operation
from aistack.transaction.contracts.selection_materialise import KIND, SelectionMaterialise
from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.contracts.transaction_status import TransactionStatus


class MaterialisationFailed(RuntimeError):
    """The transaction failed: `error` is what the operation said."""

    def __init__(self, target_root: Path, error: str) -> None:
        super().__init__(f"{target_root} was not materialised: {error}")
        self.target_root = target_root
        self.error = error


def materialise_selection(
    transactions: TransactionServices,
    catalog: Catalog,
    resolution: SubtreeResolution,
    capacity: CapacityVerdict,
    target_root: Path,
    media_extensions: frozenset[str],
) -> MaterialisationReport:
    """Run one `selection.materialise` operation and return its report."""

    operation = Operation(
        name=f"materialise {target_root.name}",
        kind=KIND,
        payload=SelectionMaterialise(
            catalog=catalog,
            resolution=resolution,
            capacity=capacity,
            target_root=target_root,
            media_extensions=media_extensions,
        ),
    )
    transaction = transactions.executor.execute(Transaction(operations=[operation]))

    if transaction.status is not TransactionStatus.SUCCEEDED:
        raise MaterialisationFailed(target_root, operation.error)

    report = operation.result
    assert isinstance(report, MaterialisationReport)

    return report

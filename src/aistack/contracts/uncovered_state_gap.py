from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration


@dataclass(frozen=True)
class UncoveredStateGap:
    """
    One declared service already found to hold persistent state with
    no known backup engine covering it — `OPS-0010`'s own "état
    persistant non couvert" constat (R9).

    Mirrors `PraTestGap`/`BackupGap`: constructed only once
    `find_uncovered_state` (`aistack.runtime.uncovered_state_gap`) has
    already confirmed the condition; it does not re-derive "has state,
    not covered" from a bare declaration handed to it from elsewhere.
    """

    declaration: BackupStrategyDeclaration

    def __post_init__(self) -> None:
        if not self.declaration.has_state:
            raise ValueError(
                f"{self.declaration.service} declares no persistent "
                f"state — never an uncovered-state gap"
            )

        if self.declaration.covered:
            raise ValueError(
                f"{self.declaration.service} is already covered by "
                f"{len(self.declaration.engines)} declared engine(s) — "
                f"not a gap"
            )

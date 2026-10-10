from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration


@dataclass(frozen=True)
class UncoveredStateGap:
    """
    A service declared stateful with no backup engine covering it
    (OPS-0010). The constructor checks the declaration.
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

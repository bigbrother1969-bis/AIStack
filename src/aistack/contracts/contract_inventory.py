from __future__ import annotations

from dataclasses import dataclass, field


PROTOCOL = "protocol"
ABSTRACT = "abstract"


@dataclass(frozen=True)
class DeclaredContract:
    """
    One declared contract (a `Protocol` or a class with abstract
    methods) and what satisfies it.

    `satisfied_by`: concrete classes that structurally satisfy it; empty
    means orphan. `declared_by`: classes that name it as a base. The two
    are measured separately because Python's ABC machinery never checks
    signatures, so a class can inherit a contract without honouring it.

    An orphan is a fact, not a fault: a contract may be written ahead of
    its implementation. There is no verdict field.
    """

    name: str
    module: str
    kind: str
    members: tuple[str, ...] = field(default_factory=tuple)
    satisfied_by: tuple[str, ...] = field(default_factory=tuple)
    declared_by: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.kind not in (PROTOCOL, ABSTRACT):
            raise ValueError(
                f"{self.name} declares kind {self.kind!r}; a contract "
                f"is {PROTOCOL!r} or {ABSTRACT!r}"
            )

        if not self.name or not self.module:
            raise ValueError(
                "a contract is named by its module and its class; "
                f"got {self.module!r}.{self.name!r}"
            )

    @property
    def qualified_name(self) -> str:
        return f"{self.module}.{self.name}"

    @property
    def is_orphan(self) -> bool:
        return not self.satisfied_by

    @property
    def falsely_declared_by(self) -> tuple[str, ...]:
        """Classes naming this contract as a base without satisfying it, in `declared_by` order."""

        satisfied = set(self.satisfied_by)

        return tuple(
            name
            for name in self.declared_by
            if name not in satisfied
        )


@dataclass(frozen=True)
class ContractInventory:
    """
    The contract architecture of a package, from which technical debt
    is derived.

    `unreadable` lists modules that could not be imported; they may hold
    the class satisfying an "orphan", so such an inventory is partial.
    """

    package: str
    modules: int
    implementations: int
    contracts: tuple[DeclaredContract, ...] = field(default_factory=tuple)
    unreadable: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    declarations_measured: bool = False

    def __post_init__(self) -> None:
        if not self.package:
            raise ValueError(
                "an inventory names the package it walked"
            )

        if self.modules < 0 or self.implementations < 0:
            raise ValueError(
                f"counts are numbers of things observed: "
                f"{self.modules}, {self.implementations}"
            )

        seen: set[str] = set()

        for contract in self.contracts:
            if contract.qualified_name in seen:
                raise ValueError(
                    f"{contract.qualified_name} appears twice; a "
                    f"contract is counted once or the debt is inflated"
                )
            seen.add(contract.qualified_name)

    @property
    def orphans(self) -> tuple[DeclaredContract, ...]:
        return tuple(c for c in self.contracts if c.is_orphan)

    @property
    def false_declarations(self) -> tuple[tuple[str, str], ...]:
        """
        Every (class, contract) pair where the class declares and does
        not satisfy. Empty with `declarations_measured` False means
        nothing was asked, not that nothing was found.
        """

        return tuple(
            (implementation, contract.qualified_name)
            for contract in self.contracts
            for implementation in contract.falsely_declared_by
        )

    @property
    def declaring(self) -> int:
        """How many (class, contract) declarations were observed."""

        return sum(
            len(contract.declared_by) for contract in self.contracts
        )

    @property
    def is_partial(self) -> bool:
        """Whether a module could not be imported; orphans are then an upper bound."""

        return bool(self.unreadable)

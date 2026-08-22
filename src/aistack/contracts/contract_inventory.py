from __future__ import annotations

from dataclasses import dataclass, field


PROTOCOL = "protocol"
ABSTRACT = "abstract"


@dataclass(frozen=True)
class DeclaredContract:
    """
    One contract the heritage declares, and what satisfies it.

    A contract is a `Protocol` or a class carrying unimplemented
    abstract methods. Both express the same thing — *this is what
    an implementation must provide* — and a measurement that
    understood only one of them would report seven integrity
    checks as orphans while they implement an ABC.

    `satisfied_by` holds the qualified names of the concrete
    classes that structurally satisfy it. Empty means orphan.

    **An orphan contract is a fact, not a fault.** `STD-P-002`
    makes a contract written ahead of its implementation the
    prescribed order. Which orphans are planned and which are
    abandoned is a qualification, and `GOV-P-001` places it with
    the owner. This model therefore states the fact and offers no
    verdict field.
    """

    name: str
    module: str
    kind: str
    members: tuple[str, ...] = field(default_factory=tuple)
    satisfied_by: tuple[str, ...] = field(default_factory=tuple)

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


@dataclass(frozen=True)
class ContractInventory:
    """
    What the contract architecture of a package looks like.

    FDN-0011 makes technical debt a property of the contracts and
    requires it to be *derived from violations of the contract
    architecture rather than from subjective code reviews*. This
    is the derivation's output.

    `unreadable` is the field that keeps the rest honest. A module
    that could not be imported may hold the very class that
    satisfies a contract counted as orphan here, so an inventory
    with unreadable modules is **partial**, and says so rather
    than publishing a count that reads as exhaustive.

    That distinction has already cost this heritage twice: two
    earlier measurements walked past `src/aistack/integrity/`
    because package discovery could not descend into it, and
    reported a complete inventory of a tree they could not see.
    """

    package: str
    modules: int
    implementations: int
    contracts: tuple[DeclaredContract, ...] = field(default_factory=tuple)
    unreadable: tuple[tuple[str, str], ...] = field(default_factory=tuple)

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
    def is_partial(self) -> bool:
        """
        Whether a module escaped the walk.

        A partial inventory reporting orphans is reporting them
        *at most*: the class that satisfies one of them may sit in
        a module that did not import.
        """

        return bool(self.unreadable)

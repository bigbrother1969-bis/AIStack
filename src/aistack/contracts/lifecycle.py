from dataclasses import dataclass, field


CONTINUOUS = "continuous"
INTERMITTENT = "intermittent"

DECLARED_EXPECTATIONS = frozenset({CONTINUOUS, INTERMITTENT})


@dataclass(frozen=True)
class LifecycleDeclaration:
    """
    Whether one container is expected to run continuously, or is
    stopped and started by the owner's own choice.

    `OPS-0001` names the gap this closes without being able to close
    it: "the heritage cannot tell 'stopped because broken' from
    'stopped on purpose', because nothing declares which containers
    are expected to run." That sentence is the contract. `expected`
    is the field the sentence says does not exist yet.

    **This is not a health signal, and it is not derived.** Nothing
    here watches a container and infers its pattern — that would be
    exactly the psychological profiling this heritage refuses to do
    of its own logs (`FDN-0003` Article 12: the undeclared stays
    declared as such, never replaced by a plausible guess). A
    declaration exists only where the owner has stated one, per
    `GOV-P-001`: the owner states operational knowledge, the system
    records what was said.

    `reason` carries the owner's own account of *why* — not a
    classification the system chose, the sentence the owner gave.
    Fabrice, 2026-09-04, on `frigate`: he stops it most of the time
    because it consumes more resources than he needs running
    permanently, and starts it back up when he wants it. That
    sentence is `reason` for that one declaration; it is not a
    template for any other container until its owner says one.
    """

    container: str
    expected: str
    reason: str

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError(
                "a lifecycle declaration names the container it is "
                "about; this one names none"
            )

        if self.expected not in DECLARED_EXPECTATIONS:
            raise ValueError(
                f"{self.container} declares `expected` as "
                f"{self.expected!r}; it is one of "
                f"{sorted(DECLARED_EXPECTATIONS)}"
            )

        if not self.reason.strip():
            raise ValueError(
                f"{self.container} declares no `reason` — an "
                f"intermittent container without one is a guess "
                f"wearing a field, and `continuous` is the default "
                f"already, so declaring it says nothing a silence "
                f"did not already say"
            )


@dataclass(frozen=True)
class LifecycleRegister:
    """
    The lifecycle declarations one governed artifact carries.

    Mirrors `SignatureCatalogue`'s shape on purpose: an `artifact`
    identifier findings can cite, a tuple of entries, and the one
    invariant a register of policies cannot do without — no two
    declarations name the same container, because a name that
    designated two answers would designate neither.

    **Absence is a state, not a gap to fill.** A container with no
    declaration here is not asserted `continuous` — nothing is
    asserted about it at all. `for_container` returns `None` for it,
    and a caller that treats `None` as `continuous` is making that
    default itself, in code that can be read and changed; this
    register never makes it silently.
    """

    artifact: str
    declarations: tuple[LifecycleDeclaration, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.artifact.strip():
            raise ValueError(
                "a register is declared by an artifact, and a "
                "grounded finding cites it through that artifact's "
                "identifier"
            )

        seen: set[str] = set()

        for declaration in self.declarations:
            if declaration.container in seen:
                raise ValueError(
                    f"{declaration.container} is declared twice in "
                    f"{self.artifact}; a cited name must designate "
                    f"one answer"
                )
            seen.add(declaration.container)

    def for_container(self, container: str) -> LifecycleDeclaration | None:
        """The declaration naming `container`, or `None` if none does."""

        for declaration in self.declarations:
            if declaration.container == container:
                return declaration

        return None

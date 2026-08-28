from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegisteredEntry:
    """One thing the bootstrap put into a Kernel registry."""

    registry: str
    identifier: str
    entry: str

    def __post_init__(self) -> None:
        if not self.registry or not self.identifier:
            raise ValueError(
                "a registration is named by its registry and its "
                f"identifier; got {self.registry!r}, "
                f"{self.identifier!r}"
            )

    @property
    def qualified_name(self) -> str:
        return f"{self.registry}/{self.identifier}"


@dataclass(frozen=True)
class RetrievalSite:
    """
    One place that asks a Kernel registry for something.

    `identifier` is the literal the site names, or `None` when the
    site computes it — `self.tasks.get(context.request.task_id)`.
    A computed identifier is **not an absence**: it is a
    retrieval whose target this measurement cannot name, and
    recording it as `None` is what keeps *nothing retrieves this*
    apart from *something might*.
    """

    registry: str
    identifier: str | None
    site: str
    in_tests: bool = False

    def __post_init__(self) -> None:
        if not self.registry or not self.site:
            raise ValueError(
                "a retrieval is named by its registry and its "
                f"site; got {self.registry!r}, {self.site!r}"
            )

    @property
    def is_computed(self) -> bool:
        return self.identifier is None


@dataclass(frozen=True)
class RegistryInventory:
    """
    What the Kernel registers at bootstrap, and what asks for it.

    ADR-0004 § *Discovery Model*, restated by ARCH-0007: *the
    Kernel is extended by registration, not by modification*, and
    *application code requests capabilities from the Kernel
    Context instead of instantiating implementations directly*.
    Both halves of that sentence are facts about running code, and
    until 2026-08-28 nothing in this heritage measured either.

    GOV-0002/OS-001 named three dimensions that place a contract —
    what implements it, what consumes it, what governs it — and
    said any one alone gives a confident wrong answer. The
    contract inventory measures the first. **This measures the
    second**, for the one form of consumption the Kernel makes
    explicit: a capability registered under an identifier and
    resolved by that identifier.

    `measured` is separate from every list being empty, for the
    reason `ContractInventory.declarations_measured` is: a
    projection taken before this existed carries nothing, and
    *nobody looked* must not print as *nothing found*.

    **What it does not see is stated rather than discovered.** A
    registry bound to a local name before being asked
    (`r = kernel.registries.providers; r.get("docker")`) is
    invisible to it, and an attribute that merely shares a
    registry's name is counted. Both are consequences of reading
    the source rather than running it, and running it would
    measure one execution instead of the repository.
    """

    registries: tuple[str, ...] = field(default_factory=tuple)
    registered: tuple[RegisteredEntry, ...] = field(default_factory=tuple)
    retrievals: tuple[RetrievalSite, ...] = field(default_factory=tuple)
    sources: int = 0
    unreadable: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    measured: bool = False

    def __post_init__(self) -> None:
        if self.sources < 0:
            raise ValueError(
                f"sources is a number of files parsed: {self.sources}"
            )

        for entry in self.registered:
            if entry.registry not in self.registries:
                raise ValueError(
                    f"{entry.qualified_name} is registered into "
                    f"{entry.registry!r}, which the Kernel Context "
                    f"does not carry"
                )

    @property
    def is_partial(self) -> bool:
        """Whether a source file escaped the parse."""

        return bool(self.unreadable)

    @property
    def computed_registries(self) -> frozenset[str]:
        """
        Registries some site asks with a computed identifier.

        Anything registered there is beyond this measurement: the
        site may resolve it and may not, and the difference is not
        in the source.
        """

        return frozenset(
            retrieval.registry
            for retrieval in self.retrievals
            if retrieval.is_computed
        )

    @property
    def empty_registries(self) -> tuple[str, ...]:
        """
        Registries the Kernel Context carries and bootstrap leaves
        empty.

        `TaskRegistry` was one on 2026-08-27, with a resolver
        asking it at every request: GOV-0002/OS-041 — *the
        dimension is not merely uncalled, it has nothing to
        execute*.
        """

        filled = {entry.registry for entry in self.registered}

        return tuple(
            registry
            for registry in self.registries
            if registry not in filled
        )

    @property
    def unretrieved(self) -> tuple[RegisteredEntry, ...]:
        """
        Registrations no site names.

        A registry asked with a computed identifier is left out
        entirely: nothing there can be called unretrieved without
        asserting what that site resolves to.
        """

        named = {
            (retrieval.registry, retrieval.identifier)
            for retrieval in self.retrievals
            if not retrieval.is_computed
        }

        computed = self.computed_registries

        return tuple(
            entry
            for entry in self.registered
            if entry.registry not in computed
            and (entry.registry, entry.identifier) not in named
        )

    @property
    def retrieved_only_in_tests(self) -> tuple[RegisteredEntry, ...]:
        """
        Registrations named by tests and by nothing that ships.

        *0 callers, 0 tests* and *0 callers, tests only* are
        different conditions, and GOV-0002/OS-041 turns on the
        difference: `KernelRuntime.boot()` is called by tests, and
        the entry says so rather than saying it is dead.
        """

        shipped = {
            (retrieval.registry, retrieval.identifier)
            for retrieval in self.retrievals
            if not retrieval.is_computed and not retrieval.in_tests
        }

        tested = {
            (retrieval.registry, retrieval.identifier)
            for retrieval in self.retrievals
            if not retrieval.is_computed and retrieval.in_tests
        }

        computed = self.computed_registries

        return tuple(
            entry
            for entry in self.registered
            if entry.registry not in computed
            and (entry.registry, entry.identifier) in tested
            and (entry.registry, entry.identifier) not in shipped
        )

    @property
    def computed_sites(self) -> tuple[RetrievalSite, ...]:
        return tuple(
            retrieval
            for retrieval in self.retrievals
            if retrieval.is_computed
        )

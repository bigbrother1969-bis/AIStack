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

    `identifier` is the literal the site names, or `None` when the site
    computes it (`self.tasks.get(context.request.task_id)`): a retrieval
    whose target cannot be named statically, not an absence.
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
    What the Kernel registers at bootstrap, and which source sites ask
    for it (ADR-0004 § Discovery Model: extension by registration).

    `measured` is separate from the lists being empty, so "nobody
    looked" never reads as "nothing found".

    Measured by reading source, not running it: a registry bound to a
    local name first (`r = kernel.registries.providers; r.get("docker")`)
    is missed, and an attribute that merely shares a registry's name is
    counted.
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
        Registries some site asks with a computed identifier; their
        entries cannot be judged retrieved or not.
        """

        return frozenset(
            retrieval.registry
            for retrieval in self.retrievals
            if retrieval.is_computed
        )

    @property
    def empty_registries(self) -> tuple[str, ...]:
        """Registries the Kernel Context carries and bootstrap leaves empty."""

        filled = {entry.registry for entry in self.registered}

        return tuple(
            registry
            for registry in self.registries
            if registry not in filled
        )

    @property
    def unretrieved(self) -> tuple[RegisteredEntry, ...]:
        """
        Registrations no site names. Registries asked with a computed
        identifier are left out.
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
        Registrations named by tests and by nothing that ships, kept
        apart from registrations nothing names at all.
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

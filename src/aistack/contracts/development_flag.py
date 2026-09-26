from dataclasses import dataclass

from aistack.contracts.undeclared import UNDECLARED


@dataclass(frozen=True)
class DevelopmentFlagPattern:
    """
    One declared development-only option, and what it means when a
    running container's own launch command carries it.

    `STD-0300` § VS-4 criterion 4.3: "It identifies the development
    option enabled in a permanent service." The reference incident is
    the one fact this heritage has: `aistack-selection-ui` ran with
    Uvicorn's `--reload`, meant for a developer's own machine, left
    on in a container nothing ever stops. `identifier` and
    `pattern` mirror `Signature`'s own shape deliberately — this is
    the same kind of declared rule, read against a container's
    command instead of its logs.

    **One declared pattern today, because one is what has been
    observed.** `GOV-P-001` applies here the same way it does to
    `OPS-0001`'s own signatures: a second pattern is added when a
    second real case names one, not guessed at in advance to make
    the list look more complete than what has actually happened.
    """

    identifier: str
    pattern: str
    interpretation: str

    def __post_init__(self) -> None:
        for name in ("identifier", "pattern", "interpretation"):
            if not getattr(self, name).strip():
                raise ValueError(
                    f"a development-flag pattern declares its {name}; "
                    f"this one is empty"
                )


@dataclass(frozen=True)
class DevelopmentFlagFinding:
    """
    One container whose own launch command carries a declared
    development-only option.

    `command` is kept alongside the match, the same reasoning
    `MatchedLine` carries a log line rather than only a position:
    a reader deciding whether this matters needs to see the command
    that fired the rule, not only the rule's name.

    **`grounding` mirrors `RuntimeFinding.grounding` on purpose.**
    `STD-0300` § VS-4 criterion 4.3 asks whether the option is enabled
    "in a permanent service" — a question this finding does not answer
    by itself, the same way `OPS-0001`'s own signatures do not answer
    whether their subject is stopped on purpose. `aistack.runtime
    .grounding.ground_development_flags` is `ground_findings`'s
    counterpart for this finding type: it reads `OPS-0003` and cites
    it here where the owner has declared this container one way or
    the other. `UNDECLARED` — not `False`, not "permanent" assumed —
    is what a container carries until then: absence is a state, the
    same reading `LifecycleRegister.for_container` already gives.
    """

    container: str
    pattern: str
    interpretation: str
    command: str
    grounding: str = UNDECLARED

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError(
                "a development-flag finding names the container it "
                "is about; this one names none"
            )

        if self.pattern not in self.command:
            raise ValueError(
                f"{self.container}: {self.pattern!r} is not present "
                f"in the command cited as evidence: {self.command!r}"
            )

from dataclasses import dataclass


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
    """

    container: str
    pattern: str
    interpretation: str
    command: str

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

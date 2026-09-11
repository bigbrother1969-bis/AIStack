from dataclasses import dataclass

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_observation import LogEntry
from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.temperature_reading import TemperatureReading


# STD-0300 § VS-4 criterion 4.5's own vocabulary, authored by the
# owner in `OPS-0004` and closed there — "no more may be added
# without the owner naming a fifth." Declared here, next to the type
# that cites it, rather than in `aistack.runtime.evaluate`, so every
# caller validates against the one list rather than trusting each
# other to spell it the same way.
#
# Each entry is a citation, `{register}/{term}` — the same shape
# `ground_findings` already writes for `grounding`
# (`OPS-0003/frigate`) — not the bare English term, so a
# `RuntimeFinding.qualifications` entry is traceable to where it was
# authored on sight, the same discipline `signature` already holds
# for the rule that produced the finding.
QUALIFICATIONS = (
    "OPS-0004/technical-debt",
    "OPS-0004/energy-inefficiency",
    "OPS-0004/sustainability-anomaly",
    "OPS-0004/deployment-misconfiguration",
)


@dataclass(frozen=True)
class MatchedLine:
    """
    One log line, and where in it the signature was found.

    The position lives here rather than on `LogEntry` because it
    is not a property of the line. It is a property of the
    *encounter* between a declared rule and that line: the same
    line matched by two signatures has two positions, and a line
    a provider collected has none at all. `ARC-P-012` puts the
    provider on the far side of that boundary — it observes and
    concludes nothing, so it has nothing to say about a match.

    **`match_at` may be `None`, and it means one specific
    thing:** the pattern was found and its position in the
    original text could not be determined. That happens when a
    case-insensitive comparison folds characters whose folded
    length differs from the original — `ß` folds to `ss` — so an
    index into the folded text points somewhere else in the line
    the container printed. Reporting that index would centre an
    extract on the wrong characters and call it evidence.

    It is `None` rather than zero, because zero is a real
    position. FDN-0003 Article 12: the undetermined is declared,
    not replaced by a plausible default.
    """

    entry: LogEntry
    match_at: int | None = None

    def __post_init__(self) -> None:
        if self.match_at is not None and self.match_at < 0:
            raise ValueError(
                f"a match position is an index into the line: "
                f"{self.match_at}; use None when it could not be "
                f"determined"
            )

        if (
            self.match_at is not None
            and self.match_at > len(self.entry.text)
        ):
            raise ValueError(
                f"a match at {self.match_at} in a line of "
                f"{len(self.entry.text)} characters points outside "
                f"the evidence it cites"
            )


@dataclass(frozen=True)
class CitedReading:
    """
    One reading — CPU or temperature — cited as technical evidence
    for a `RuntimeFinding`, from a source that is not a log line.

    J5 — `evaluate`, the Evidence and Observation Foundation's first
    real consumer (`claude/PLAN-TRAJECTOIRE-2026-09-04.md`). STD-0300
    § VS-4 criterion 4.4 asks for technical evidence "collected and
    attached to the finding, down to system-call level or
    equivalent." `MatchedLine` already satisfies that for a log line
    — the line itself, and where in it a pattern was found.
    `CitedReading` is the same discipline for a reading
    `DockerProvider.collect_cpu_readings` or `HostProvider
    .collect_temperatures` produced: `provider` names which one, the
    same `provider_id` convention `RuntimeObservation` already
    carries, so a finding cites exactly what collected the evidence
    — `docker stats`, `sensors` — not a description of what it means.

    `reading` is one of three named types — `ContainerCpuReading`,
    `TemperatureReading`, and, since `PLAN-J7`'s storage domain,
    `StorageReading` — spelled out directly rather than imported from
    `aistack.kernel.evidence.Evidence`: `aistack.contracts` is the
    heritage's foundational layer, and importing `aistack.kernel
    .evidence` from it would read the dependency backwards —
    `kernel.evidence` is built on these contracts, not the other way
    round.

    **`Evidence` itself still names only the first two.** Nothing in
    the Kernel Runtime's collection pipeline touches storage yet —
    the same reason `aistack.runtime.evaluate` is a plain function
    outside that machinery, per its own docstring, and
    `aistack.runtime.evaluate_storage` keeps the same scope. Widening
    `CitedReading` here is the narrower, accurate claim: a finding
    cites a `StorageReading` directly; a separate claim — that
    storage capacity is `Evidence` in the Kernel Runtime's sense —
    is not made by this change.
    """

    provider: str
    reading: ContainerCpuReading | TemperatureReading | StorageReading

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError(
                "a cited reading names the provider that collected "
                "it; this one names none"
            )


@dataclass(frozen=True)
class RuntimeFinding:
    """
    One qualified statement about a running subject.

    This is not an `IntegrityFinding`, and the difference is not
    symmetry. An `IntegrityFinding` speaks about the governed
    heritage, counts artifacts, and its contract states that "it
    proposes no remediation". A runtime finding speaks about the
    system the heritage describes, and STD-0300 § VS-4 criterion
    4.7 *requires* it to recommend one. Reusing the first would
    have broken its own declared contract.

    **`evidence` may not be empty, and that is enforced here
    rather than asked for.** Criterion 4.9 — no finding without
    at least one evidence reference — is a property of the type,
    so a finding that cannot cite what it saw cannot be
    constructed. This heritage spent two days on rules that were
    declared and enforced by nothing; this one is enforced by the
    constructor.

    `signature` carries the identifier of the rule that produced
    the finding — `OPS-0001/S-003`. That is criterion 4.7's
    citation, and it is why the rule had to be declared and
    identified rather than written into a function.

    Each piece of evidence is a `MatchedLine`: the line, and
    where the pattern was found in it. The position exists so a
    report can show what fired the rule. On 2026-08-22 the first
    complete run produced eleven `frigate` lines carrying three
    timestamps each, and the report's extract stopped before
    `connection refused` — everything about the evidence except
    what it proved.

    `interpretation` and `remediation` are copied from the
    signature at the moment of qualification, not looked up
    later. A finding read six months from now states what the
    rule said when it fired, not what the rule says today.

    **`qualifications` classifies the finding, revised from the
    account above.** Until J5 (`claude/PLAN-TRAJECTOIRE-2026-09-04
    .md`) nothing here classified the finding four ways, and that
    paragraph said inventing the vocabulary would be authoring
    governed knowledge GOV-P-001 forbids. The vocabulary has since
    been authored — by the owner, in `OPS-0004`, closed at four
    terms — so citing it here is no longer inventing it; `evaluate`
    (`aistack.runtime.evaluate`) is its first producer.
    `QUALIFICATIONS` (module level, this file) is the closed list
    `__post_init__` validates against, each entry a citation —
    `OPS-0004/energy-inefficiency`, not the bare term — the same
    shape `grounding` already writes. Defaults to `()`: a
    log-signature finding from `qualify()` carries none, and that
    is a true, ungoverned-by-this-field state, not an omission.
    STD-0300 § VS-4 criterion 4.5: more than one qualification found
    together is what makes a finding derived knowledge rather than
    an opinion about severity — this field is where that is stated.

    `evidence` widened the same day, from `tuple[MatchedLine, ...]`
    alone to `tuple[MatchedLine | CitedReading, ...]` — a
    `CitedReading` (this module) is a reading, not a log line, cited
    the same way STD-0300 § VS-4 criterion 4.4 asks for. Existing
    `MatchedLine` evidence is untouched; this adds a second kind
    rather than replacing the first.
    """

    subject: str
    signature: str
    interpretation: str
    remediation: str
    confidence: str
    grounding: str
    evidence: tuple[MatchedLine | CitedReading, ...]
    qualifications: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError(
                "a finding is about a subject; this one names none"
            )

        if not self.signature.strip():
            raise ValueError(
                "a finding cites the signature that produced it "
                "(STD-0300 § VS-4, criterion 4.7)"
            )

        if not self.evidence:
            raise ValueError(
                f"{self.signature} produced a finding about "
                f"{self.subject!r} citing no evidence; STD-0300 § VS-4 "
                f"criterion 4.9 forbids it"
            )

        # An annotation is not a check. `tuple[MatchedLine, ...]`
        # accepted bare `LogEntry` objects without complaint when
        # this type changed on 2026-08-23, and every caller that
        # had not been updated kept passing — a declaration that
        # asserts a protection and delivers none, in the contract
        # written to stop exactly that.
        wrong = [
            type(item).__name__
            for item in self.evidence
            if not isinstance(item, (MatchedLine, CitedReading))
        ]

        if wrong:
            raise ValueError(
                f"{self.signature} cites evidence of type "
                f"{sorted(set(wrong))}; a finding cites MatchedLine "
                f"or CitedReading, which carry what was seen and "
                f"where it came from"
            )

        if len(set(self.qualifications)) != len(self.qualifications):
            raise ValueError(
                f"{self.signature} cites the same qualification more "
                f"than once in {self.qualifications}; a repeated "
                f"citation does not make the finding more qualified"
            )

        unknown = [
            qualification
            for qualification in self.qualifications
            if qualification not in QUALIFICATIONS
        ]

        if unknown:
            raise ValueError(
                f"{self.signature} cites {unknown} as a "
                f"qualification; OPS-0004 closes the vocabulary at "
                f"{QUALIFICATIONS} and forbids more without the "
                f"owner naming a fifth"
            )

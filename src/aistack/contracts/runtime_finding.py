from dataclasses import dataclass

from aistack.contracts.finding_message import FindingMessage

from aistack.contracts.backup_reading import BackupReading
from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.contracts.data_usage import DataUsageReading
from aistack.contracts.host_silence import HostSilence
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.inventory_gap import InventoryGap
from aistack.contracts.pra_test_reading import PraTestReading
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.restart_loop import RestartLoop
from aistack.contracts.runtime_observation import LogEntry
from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.temperature_reading import TemperatureReading


# The closed qualification vocabulary declared in OPS-0004. Each entry
# is a citation `{register}/{term}`, so it is traceable to its source.
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

    The position belongs to the match, not the line: two signatures
    can match one line at two positions.

    `match_at` is `None` when the pattern was found but its position in
    the original text is unknown: case folding can change length (`ß`
    folds to `ss`), so an index into folded text would point elsewhere.
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
    A reading (not a log line) cited as evidence for a `RuntimeFinding`.

    `provider` names what collected it (e.g. `docker stats`, `sensors`).
    `reading` is one of the reading or declaration types listed in the
    annotation below.
    """

    provider: str
    reading: (
        ContainerCpuReading
        | TemperatureReading
        | StorageReading
        | ContainerStateReading
        | BackupReading
        | GpuReading
        | PraTestReading
        | BackupStrategyDeclaration
        | InventoryGap
        | RestartLoop
        | HostSilence
        | DataUsageReading
    )

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError(
                "a cited reading names the provider that collected "
                "it; this one names none"
            )


@dataclass(frozen=True)
class RuntimeFinding:
    """
    One qualified statement about a running subject, with a
    recommended remediation.

    `evidence` must not be empty; the constructor enforces it, and each
    item must be a `MatchedLine` or a `CitedReading`. `signature` is the
    identifier of the rule that produced the finding (e.g.
    `OPS-0001/S-003`).

    `interpretation` and `remediation` are copied from the rule when it
    fires, so the finding states what the rule said then.
    `qualifications` cites entries of `QUALIFICATIONS`; a log-signature
    finding carries none.
    """

    subject: str
    signature: str
    interpretation: str
    remediation: str
    confidence: str
    grounding: str
    evidence: tuple[MatchedLine | CitedReading, ...]
    qualifications: tuple[str, ...] = ()
    # The same two sentences as catalog keys, for a page rendered in the
    # reader's language (`aistack.contracts.finding_message`). `None`:
    # the English text is shown as is.
    message: FindingMessage | None = None

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError(
                "a finding is about a subject; this one names none"
            )

        if not self.signature.strip():
            raise ValueError(
                "a finding cites the signature that produced it"
            )

        if not self.evidence:
            raise ValueError(
                f"{self.signature} produced a finding about "
                f"{self.subject!r} citing no evidence; a finding always "
                f"cites one"
            )

        # The annotation alone does not reject a bare `LogEntry`.
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

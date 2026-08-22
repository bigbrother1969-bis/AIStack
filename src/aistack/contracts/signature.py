from dataclasses import dataclass, field

from aistack.contracts.undeclared import UNDECLARED


@dataclass(frozen=True)
class Signature:
    """
    One declared rule for interpreting an observation.

    FDN-0002 defines a *Knowledge Policy* as "a governed rule
    defining how knowledge is evaluated, qualified or
    interpreted", explicit and versioned. A signature is exactly
    that, and ADR-0009 § 3 records the consequence: a catalogue
    of signatures is a policy register, and a finding citing the
    signature that produced it satisfies STD-0300 § VS-4
    criterion 4.7 by construction.

    Every field below is required. None has a default except
    `grounding`, and that exception is the point of it.

    `case_sensitive` has no default either, and the reason is
    concrete. The experimenter compared three patterns against
    the log text as written and the fourth against
    `logs.lower()`. That difference is a property of each rule,
    and it was invisible until someone tried to transcribe the
    rules into a form that had to state them. A default would
    have made three signatures declare a comparison they never
    chose.

    `depth` is a property of the signature and not a parameter of
    the call. The experimenter read a hundred lines for every
    rule; a rule whose useful window is longer would never have
    fired, and nothing would have said so.

    `applies_to` names the subject states in which the rule means
    something. The literal `any` stands for every state and may
    not be mixed with others.

    It exists because of a false positive on 2026-08-22, the
    first day this chain ran for real. `frigate` is stopped on
    purpose — it is started on demand and shut down after — and
    its last hundred lines held eleven connection refusals, which
    are what an nginx prints while its backend goes away. The
    detection was exact; the remediation was meaningless. A rule
    that only means something on a running container has to be
    able to say so.

    That case also names a deeper gap: the heritage cannot tell
    "stopped because broken" from "stopped on purpose", because
    nothing declares which containers are expected to run.

    `grounding` names the policy that makes the *remediation* the
    right one — not the policy the signature is, which is itself.
    "Check the VPN credentials used by the container" is only
    actionable if those credentials have a declared location.
    Where no such rule exists, the field is `unknown`: a governed
    state under FDN-0003 Article 12, and a countable one. The
    owner's position, recorded 2026-08-22: a well-founded and
    explainable system is the target, and some ancillary rules
    may stand without an explicit policy.
    """

    identifier: str
    pattern: str
    case_sensitive: bool
    applies_to: tuple[str, ...]
    interpretation: str
    remediation: str
    depth: int
    confidence: str
    grounding: str = UNDECLARED

    def __post_init__(self) -> None:
        if not isinstance(self.applies_to, tuple):
            raise ValueError(
                f"{self.identifier} declares `applies_to` as "
                f"{type(self.applies_to).__name__}; this contract is "
                f"frozen, and a mutable field would make that word "
                f"mean nothing"
            )

        if not self.applies_to:
            raise ValueError(
                f"{self.identifier} names no state it applies to; a "
                f"rule that means something everywhere says `any`"
            )

        if not all(
            isinstance(s, str) and s.strip() for s in self.applies_to
        ):
            raise ValueError(
                f"{self.identifier} names a state that is empty or is "
                f"not text: {list(self.applies_to)}"
            )

        if "any" in self.applies_to and len(self.applies_to) > 1:
            raise ValueError(
                f"{self.identifier} declares `any` beside "
                f"{sorted(set(self.applies_to) - {'any'})}: `any` is "
                f"every state, and the rest would say nothing"
            )

        for name in ("identifier", "pattern", "interpretation", "remediation"):
            if not getattr(self, name).strip():
                raise ValueError(
                    f"a signature declares its {name}; this one is empty"
                )

        if self.depth <= 0:
            raise ValueError(
                f"a signature declares the window in which it has "
                f"meaning: {self.depth}"
            )

        if not self.confidence.strip():
            raise ValueError(
                "a signature declares its confidence; STD-0100 makes "
                "the scale an act, and an unstated act is not one"
            )


    def applies(self, state: str) -> bool:
        """
        Whether this rule means anything for a subject in `state`.

        `any` is the declared way of saying every state. It is a
        value, not a default: a signature that named nothing would
        be silently universal, which is how the frigate false
        positive happened.
        """

        return "any" in self.applies_to or state in self.applies_to


@dataclass(frozen=True)
class SignatureCatalogue:
    """
    The signatures declared by one governed artifact.

    `artifact` is the identifier of the document that declares
    them — `OPS-0001` today. A signature is named by a fragment
    of it, per ADR-0009 § 3.2: it is not a governed object
    citable from anywhere, it exists inside the catalogue that
    declares it.

    The catalogue enforces one thing only, and it is the one a
    register of policies cannot do without: no two signatures
    share an identifier. A finding cites a signature by name, and
    a name that designates two rules designates neither.
    """

    artifact: str
    signatures: tuple[Signature, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.artifact.strip():
            raise ValueError(
                "a catalogue is declared by an artifact, and findings "
                "cite it through that artifact's identifier"
            )

        seen: set[str] = set()

        for signature in self.signatures:
            if signature.identifier in seen:
                raise ValueError(
                    f"{signature.identifier} names two signatures in "
                    f"{self.artifact}; a cited name must designate one rule"
                )
            seen.add(signature.identifier)

    @property
    def deepest(self) -> int:
        """
        The window a collection must read to give every signature
        its chance.

        Collection happens once at this depth; each signature then
        evaluates its own. One Docker call, not one per rule.
        """

        return max((s.depth for s in self.signatures), default=0)

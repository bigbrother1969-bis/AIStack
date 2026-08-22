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

    `depth` is a property of the signature and not a parameter of
    the call. The experimenter read a hundred lines for every
    rule; a rule whose useful window is longer would never have
    fired, and nothing would have said so.

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
    interpretation: str
    remediation: str
    depth: int
    confidence: str
    grounding: str = UNDECLARED

    def __post_init__(self) -> None:
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

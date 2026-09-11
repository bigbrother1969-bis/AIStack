from __future__ import annotations

from dataclasses import dataclass

# The three buckets `OPS-0008` declares for a computed score — no more
# without the owner naming a fourth, the same closed-vocabulary
# discipline `OPS-0004`'s four qualifications and `OPS-0007`'s three
# threshold kinds already hold.
EXCELLENT = "excellent"
TO_WATCH = "à surveiller"
ACTION_REQUIRED = "action requise"

BUCKETS = (EXCELLENT, TO_WATCH, ACTION_REQUIRED)


@dataclass(frozen=True)
class DomainWeight:
    """
    One domain's own declared cost, in points, for each
    `RuntimeFinding` it carries — `OPS-0008`, not a number this
    heritage invented. `GOV-P-001`: the owner states the weight; this
    type only shapes it so `aistack.health.score.compute_health_score`
    can turn a `HealthDomain`'s finding count into a penalty without
    guessing how much a stale backup should cost relative to a hot
    GPU.
    """

    domain: str
    points: int

    def __post_init__(self) -> None:
        if not self.domain.strip():
            raise ValueError("a domain weight names no domain")

        if self.points <= 0:
            raise ValueError(
                f"{self.domain} declares a non-positive weight: {self.points}"
            )


@dataclass(frozen=True)
class HealthScoreWeights:
    """
    Every domain's declared weight, as `OPS-0008`'s YAML file loads it
    (`aistack.health.yaml.load_health_score_weights_yaml`).

    `for_domain` mirrors `GpuThresholdRegister.for_host` in shape —
    a pure lookup over data already held — but not in meaning: a
    domain absent here is not `FDN-0003` Article 12's kind of
    declared absence (nothing to check yet), it is a configuration
    gap `compute_health_score` treats as a defect and raises on,
    since `PLAN-J7`'s four domains are a closed set this register is
    expected to cover completely.
    """

    weights: tuple[DomainWeight, ...]

    def for_domain(self, name: str) -> int | None:
        for entry in self.weights:
            if entry.domain == name:
                return entry.points

        return None


@dataclass(frozen=True)
class HealthScore:
    """
    One computed health-score snapshot — `aistack.health.score
    .compute_health_score`'s own result, never constructed by hand
    outside a test, the same convention `RuntimeFinding` holds.

    `measured_domains`/`total_domains` keep the score honest about
    partial coverage (`OPS-0008` § *Formula*): a 100 computed while
    only one of four domains is instrumented is not the same claim as
    a 100 computed across all four, and a caller reading `value` alone
    without these two fields would not be able to tell them apart.
    """

    value: int
    measured_domains: int
    total_domains: int
    bucket: str

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            raise ValueError(f"a health score must be within 0-100: {self.value}")

        if self.measured_domains < 0 or self.total_domains < 0:
            raise ValueError(
                f"a health score cannot count negative domains: "
                f"{self.measured_domains}/{self.total_domains}"
            )

        if self.measured_domains > self.total_domains:
            raise ValueError(
                f"a health score cannot measure more domains than it "
                f"names: {self.measured_domains}/{self.total_domains}"
            )

        if self.bucket not in BUCKETS:
            raise ValueError(
                f"unknown health-score bucket {self.bucket!r}; OPS-0008 "
                f"declares only {BUCKETS}"
            )

from __future__ import annotations

from dataclasses import dataclass

# The closed set of score buckets OPS-0008 declares.
EXCELLENT = "excellent"
TO_WATCH = "à surveiller"
ACTION_REQUIRED = "action requise"

BUCKETS = (EXCELLENT, TO_WATCH, ACTION_REQUIRED)


@dataclass(frozen=True)
class DomainWeight:
    """
    One domain's declared cost, in points, per `RuntimeFinding` it
    carries (OPS-0008). Used by `aistack.health.score.compute_health_score`.
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
    Every domain's declared weight, as loaded by
    `aistack.health.yaml.load_health_score_weights_yaml`.

    `for_domain` returns `None` for an absent domain;
    `compute_health_score` treats that as a configuration error.
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
    One computed health score, produced by
    `aistack.health.score.compute_health_score`.

    `measured_domains`/`total_domains` state partial coverage: a 100
    over one measured domain is not a 100 over all of them (OPS-0008).
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

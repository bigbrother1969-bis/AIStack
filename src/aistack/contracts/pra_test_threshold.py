from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PraTestThreshold:
    """
    One service's restore-test staleness threshold (OPS-0009).

    The YAML declares one value for all services; `load_pra_tests_yaml`
    copies it into one entry per service, leaving room for per-service
    values.
    """

    service: str
    max_age_days: float

    def __post_init__(self) -> None:
        if not self.service.strip():
            raise ValueError(
                "a PRA test threshold is about one service; this one "
                "names none"
            )

        if self.max_age_days <= 0:
            raise ValueError(
                f"{self.service} declares a non-positive staleness "
                f"threshold: {self.max_age_days} days"
            )


@dataclass(frozen=True)
class PraTestThresholdRegister:
    """
    Every service's restore-test threshold, as loaded by
    `aistack.pra.yaml.load_pra_tests_yaml`. `for_service` returns
    `None` for a service that is not checked.
    """

    thresholds: tuple[PraTestThreshold, ...]

    def for_service(self, name: str) -> PraTestThreshold | None:
        for entry in self.thresholds:
            if entry.service == name:
                return entry

        return None

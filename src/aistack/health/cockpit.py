from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.runtime_finding import RuntimeFinding


@dataclass(frozen=True)
class HealthDomain:
    """
    One domain of the health cockpit and what AIStack knows about it.

    `instrumented` separates "not checked" from "checked and clean", and
    the constructor enforces it:

    - `instrumented=False`: nothing was checked this run. It carries no
      `findings` and must carry a `note` saying why, shown instead of a
      false "healthy".
    - `instrumented=True`: `findings` is the real result; `()` means
      checked and nothing wrong.
    """

    name: str
    instrumented: bool
    findings: tuple[RuntimeFinding, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a health domain names no domain")

        if not self.instrumented and self.findings:
            raise ValueError(
                f"{self.name} is declared not instrumented but carries "
                f"{len(self.findings)} finding(s); only an instrumented "
                f"domain can have findings"
            )

        if not self.instrumented and not self.note.strip():
            raise ValueError(
                f"{self.name} is declared not instrumented without "
                f"saying why; the absence must be named"
            )


@dataclass(frozen=True)
class HealthCockpit:
    """
    The whole health cockpit, one snapshot: every domain, instrumented or
    not. Data only; `aistack.renderers.health.html.render_html` renders it.
    """

    domains: tuple[HealthDomain, ...] = ()

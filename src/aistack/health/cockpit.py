from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.runtime_finding import RuntimeFinding


@dataclass(frozen=True)
class HealthDomain:
    """
    One domain of the health cockpit, and what AIStack currently
    knows about it.

    `PLAN-J7` § 1 (`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`)
    closes the domain vocabulary at four — stockage, services,
    backup/PRA, GPU — named by the owner before any code, on the same
    "the owner names it, the qualification vocabulary follows"
    discipline `OPS-0004`'s four qualifications already hold. This
    type does not enforce that closure the way `RuntimeFinding
    .qualifications` enforces `QUALIFICATIONS`: the cockpit's own
    caller (`aistack.cli.health_render`) is the one place that
    constructs a `HealthDomain`, and it is what names the four —
    widening it is a decision for that call site, the same way
    `evaluate_storage`'s own scope is decided by its caller rather
    than by this contract.

    **`instrumented` decides what the other two fields may say, and
    the constructor enforces it — not left to the caller to get
    right.** `FDN-0003` Article 12: a domain nothing observes yet is
    a governed absence, not the same state as a domain that was
    checked and found clean. Conflating the two — rendering "no
    findings" the same way whether or not anything looked — is
    exactly the silent healing Article 12 forbids, so:

    - `instrumented=False` means nothing here was checked this run.
      It may carry no `findings` (there is nothing to have found),
      and it must carry a `note` — the reason nothing checked it,
      shown instead of a false "healthy".
    - `instrumented=True` means this run did check, and `findings`
      is the true, possibly-empty result — `()` here is a real,
      positive statement ("checked, nothing wrong"), not an absence.

    Mirrors `RuntimeFinding`'s own discipline of validating the
    property in `__post_init__` rather than trusting every caller to
    hold it (`RuntimeFinding`'s own docstring: "this heritage spent
    two days on rules that were declared and enforced by nothing").
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
                f"saying why; FDN-0003 Article 12 requires the absence "
                f"to be named, never silent"
            )


@dataclass(frozen=True)
class HealthCockpit:
    """
    The whole health cockpit, one snapshot — every domain
    `aistack.cli.health_render` knows to name this run, instrumented
    or not.

    Structured, not rendered — the same split `ArchitectureGraph`
    holds against `render_mermaid`/`render_html`: this is testable on
    its own ("is Stockage instrumented" is an assertion about data,
    not about HTML), and `aistack.renderers.health.html.render_html`
    is what turns it into a page.
    """

    domains: tuple[HealthDomain, ...] = ()

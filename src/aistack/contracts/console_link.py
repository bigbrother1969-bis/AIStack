from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsoleLink:
    """
    One entry point the console page links to — `PLAN-J11`'s v1 scope
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` § 2), decided by the
    owner, not discovered: `GOV-P-001`, the same split
    `ServiceCategorizationDefinition` already holds for "which category
    a service belongs to" — nothing here is a fact any provider could
    observe, it is the owner naming what the console should point at
    and how.

    **`url` travels exactly as the owner stated it, absolute LAN
    address or relative path alike** (`http://GIGABYTE:8181` for
    Selection UI, `/health.html` for the cockpit generated beside the
    console itself) — this dataclass validates it is not empty and
    starts with a scheme AIStack's own reverse-proxy story
    (`PLAN-J11` § 4) actually reaches, never rewrites or normalizes
    it, the same "ported, not designed" discipline
    `ServiceDefinition.container` already holds for a name.
    """

    name: str
    description: str
    url: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a console link names no service")

        if not self.description.strip():
            raise ValueError(f"{self.name} declares no description")

        if not self.url.strip():
            raise ValueError(f"{self.name} declares no url")

        if not (
            self.url.startswith("http://")
            or self.url.startswith("https://")
            or self.url.startswith("/")
        ):
            raise ValueError(
                f"{self.name} declares a url this console cannot link to: "
                f"{self.url!r} — expected http://, https:// or a relative "
                f"/path"
            )

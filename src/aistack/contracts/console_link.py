from __future__ import annotations

from dataclasses import dataclass

# The two network reaches a console card can declare — closed, the
# same two-way split `console_links.yml`'s own header comment has
# narrated by hand since 2026-09-18 (the day the owner closed
# Selection UI and Priorité CPU down to LAN-only, "y compris pour
# selection et priority") and again since ADR-0011 §1.3 (Time
# Machine, "LAN-only... regardless of how the other four mini-apps'
# own LAN choices evolve"): every card is either reachable only on the
# owner's own LAN, or reachable from the public internet through the
# reverse proxy. No third reach exists in this heritage today — the
# same closed-vocabulary discipline `aistack.contracts.health_score`'s
# `BUCKETS` already holds for a computed score's three buckets.
LAN = "lan"
PUBLIC = "public"

SCOPES = (LAN, PUBLIC)


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

    **`url` travels exactly as it arrives here, absolute LAN address
    or relative path alike** (`http://GIGABYTE:8181` for Selection UI,
    `/health.html` for the cockpit generated beside the console
    itself) — this dataclass validates it is not empty and starts
    with a scheme AIStack's own reverse-proxy story (`PLAN-J11` § 4)
    actually reaches, never rewrites or normalizes it, the same
    "ported, not designed" discipline `ServiceDefinition.container`
    already holds for a name.

    **Since 2026-09-30 (R10), a LAN card's `url` may be *resolved*
    before it reaches this dataclass, never guessed once it does** —
    `load_console_links_yaml` turns `console_links.yml`'s own
    `service:` field into a concrete address through
    `InstanceConfig.service_url` (the owner's own declared LAN host
    and port, `instance_config.yml`, not this file typing
    `http://GIGABYTE:8181` by hand six times over). The resolution
    happens once, in the loader, from a fact the owner still declares
    (which port a service answers on) — this dataclass itself never
    sees `service`, never resolves anything, and still never rewrites
    the `url` it is handed. A public card (`/health.html`) is
    unaffected: it keeps declaring `url` directly, the same as always.

    **`scope`, added 2026-09-30** (the owner: "un bandeau de couleur
    différent pour les cartes accessibles sur le réseau local ou
    depuis internet"): an explicit declaration, one of `LAN`/`PUBLIC`,
    never inferred from `url`'s own shape — the same "never guessed"
    discipline `url` itself already holds above. `console_links.yml`
    already narrated which of its seven cards is which, by hand, in
    its own header comments, well before this field existed; `scope`
    only turns that existing narration into something this renderer
    can read instead of a human alone.
    """

    name: str
    description: str
    url: str
    scope: str

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

        if self.scope not in SCOPES:
            raise ValueError(
                f"{self.name} declares a scope this console does not know: "
                f"{self.scope!r} — expected one of {', '.join(SCOPES)}"
            )

from __future__ import annotations

from dataclasses import dataclass

# Where a console card is reachable: only on the LAN, or from the
# internet through the reverse proxy.
LAN = "lan"
PUBLIC = "public"

SCOPES = (LAN, PUBLIC)


@dataclass(frozen=True)
class ConsoleLink:
    """
    One entry point the console page links to, declared by the owner.

    `url` is an absolute http(s) address or a relative `/path`, kept as
    given, never rewritten. A LAN card's `url` may already have been
    resolved by `load_console_links_yaml` from its `service:` field via
    `InstanceConfig.service_url`. `scope` is declared (`LAN`/`PUBLIC`),
    never inferred from the url.
    """

    name: str
    description: str
    url: str
    scope: str
    # What the screen asks of AI, shown on its card. Empty: no AI.
    ai: str = ""

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

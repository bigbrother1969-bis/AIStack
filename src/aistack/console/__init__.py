"""
The console — AIStack's own front door, `PLAN-J11`
(`claude/PLAN-J11-CONSOLE-2026-09-11.md`).

Not a fifth domain and not a new observation surface: every fact a
`ConsoleLink` carries is the owner's own declared routing decision
(`GOV-P-001`), the same split `aistack.architecture`'s categorization
holds for "which category a service belongs to" — nothing here is
observed from Docker, Compose, or any provider. This module starts
with the one input the console page needs before it can render
anything: `console_links.yml`, the closed v1 scope the owner named
2026-09-11 (Selection UI, Priorité CPU, Page Architecture, Cockpit
Santé) — the renderer and generator that turn it into
`console.html` follow as later steps of the same plan.
"""

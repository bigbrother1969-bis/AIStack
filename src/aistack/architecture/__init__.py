"""
Reconstructing `architecture.html` — a topology diagram of the whole
homelab, in the Kernel Runtime's own terms.

Started 2026-09-10 for jalon J2 of
`claude/PLAN-TRAJECTOIRE-2026-09-04.md`, scoped by
`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md` to the topology
diagram alone — the health cockpit and technical-debt block the
pre-AIStack system also drew are `evaluate`-shaped, not
`render`-shaped, and wait for jalon J5.

This module starts with the one input Docker and Compose cannot
supply themselves: which category each service belongs to
(`categorization`). The graph built from it, its per-category views,
and the HTML it renders into all follow as later steps of the same
plan.
"""

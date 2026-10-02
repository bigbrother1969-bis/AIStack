"""
AIStack's one web application (`ADR-0012`).

The console and, one patch at a time through 1.7's first tranche, the
five screens that used to run as separate FastAPI processes at the
repository root. Every route lives here, under `src/`, and the governed
suite exercises each one in process (`ENG-TEST-0001` § *Scope*,
`GOV-0002/OS-084`).
"""

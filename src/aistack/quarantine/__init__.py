"""
Dead code in quarantine before it is deleted (`OPS-0012`, decided by
the owner 2026-10-05).

A file found unused is not deleted on sight: it enters the register
(`register.yml`, next to this module), stays where it is for the period
the register states, and carries a tripwire that records any use of it
(`reports/generated/quarantine/hits.jsonl`). At the review date, what
was never used is deleted, with the amendments the register lists; what
was used leaves the quarantine.

Until it is deleted, quarantined code is technical debt: the health
page counts it in its "Dette technique" card (`OPS-0004`'s eighth
reference case).
"""

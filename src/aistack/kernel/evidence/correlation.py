"""
Governed `Correlation` contract — J4, Evidence and Observation
Foundation.

The place `CorrelatedFinding` already occupies: several independent
pieces of `Evidence`, stitched into one finding, each citing where it
was read (`STD-0300` § VS-4 criterion 4.2). Named as a type alias for
the same reason `Evidence` and `Observation` are — see
`kernel/evidence/evidence.py`.

`aistack.runtime.correlation.correlate_findings` is this contract's
recognized producer, declared around it rather than rewritten: its
own docstring already states it was "built for VS-4 alone, not as a
socle function," and its return type,
`tuple[CorrelatedFinding, ...]`, already matches
`tuple[Correlation, ...]` without a single line changing. No
Protocol is declared for the act of correlating — unlike collecting
or normalizing, `correlate_findings`'s own signature (four
parameters, one of them the pre-filtered subject set from an earlier
step) is specific to how VS-4 4.2 actually calls it, and generalizing
it to a shape wide enough to be a reusable contract is not a claim
this milestone makes.
"""

from __future__ import annotations

from aistack.contracts.correlated_finding import CorrelatedFinding

Correlation = CorrelatedFinding

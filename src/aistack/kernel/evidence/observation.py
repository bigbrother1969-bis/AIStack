"""
Governed `Observation` contract — J4, Evidence and Observation
Foundation.

The place `RuntimeObservation` already occupies: canonical, governed
knowledge produced by normalizing `Evidence`, never raw technical
output (ARC-P-013). Named as a type alias for the same reason
`Evidence` (`kernel/evidence/evidence.py`) is: only one real type
occupies this role today, and an empty structural `Protocol` around
it would be excluded from `aistack.conformance.inventory`'s own
contract count for requiring nothing, and would state a shape
`RuntimeObservation` does not actually share with anything else.
"""

from __future__ import annotations

from aistack.contracts.runtime_observation import RuntimeObservation

Observation = RuntimeObservation

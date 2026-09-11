"""
Governed `Evidence` contract — J4, Evidence and Observation Foundation
(`claude/PLAN-J4-EVIDENCE-OBSERVATION-2026-09-10.md`).

The place `ContainerCpuReading` and `TemperatureReading` already
occupy: one source, one instant, concluding nothing (ARC-P-012).

Named as a type alias, a union of the real types, rather than as a
shared base class or an empty structural `Protocol` — the plan this
contract came from sketched `Evidence` as a minimal structural
Protocol, and building it turned up why that does not work.
`aistack.conformance.inventory.is_contract` deliberately excludes a
Protocol that requires nothing (`protocol_members(subject)` empty),
because such a Protocol is satisfied by every class in the package
and counting it inflates what the heritage actually guarantees —
the exact defect that module's own docstring records finding once
already, on two Protocols `aistack.conformance.structural` itself
declares to measure its own noise. `ContainerCpuReading` and
`TemperatureReading` share no field; the only honest common shape
they have is "one of these two named types," which a union states
directly rather than an empty marker implying a shape neither
declares.

A third existing contract, `CpuReductionMeasurement` (VS-4 4.8), is
deliberately not a member. It is orthogonal by J4's own scoping:
already satisfied, never wired into `runtime_diagnose.py`, and no
collector or normalizer this milestone declares touches it.
"""

from __future__ import annotations

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.temperature_reading import TemperatureReading

Evidence = ContainerCpuReading | TemperatureReading

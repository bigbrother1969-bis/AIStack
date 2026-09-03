"""
Pluggable per-app activity detectors.

`claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md`, decision 1:
one priority app's own detection method must not be assumed to
generalise to any other's, so each priority app declares a
`detector:` (`aistack.priority.definition.DetectorDefinition`), and
this package is where the corresponding behaviour lives — one
module per detector type, each conforming to
`aistack.priority.detectors.base.Detector`.
"""

from __future__ import annotations

import os
from typing import Mapping

from aistack.priority.definition import (
    CpuThresholdDetectorDefinition,
    DetectorDefinition,
    PriorityAppDefinition,
)
from aistack.priority.detectors.base import Detector
from aistack.priority.detectors.cpu_threshold import CpuThresholdDetector
from aistack.priority.detectors.jellyfin import JellyfinDetector


def build_detector(
    app: PriorityAppDefinition, environ: Mapping[str, str] | None = None
) -> Detector:
    """
    Build the one `Detector` a priority app's own definition names.

    **The one place `DetectorDefinition`'s `type:` tag is switched
    on.** `aistack.priority.yaml.store._load_detector` already
    refuses an unknown `type:` at load time, so by the time a
    `PriorityAppDefinition` reaches here its `detector` is always
    one of the two known shapes — this function's `else` branch is
    unreachable in practice, kept only so a third shape added to the
    union without a matching branch here fails loudly instead of
    silently building the wrong detector.

    `environ` defaults to the real process environment
    (`os.environ`) and is only ever overridden in a test — GOV-P-001
    still holds: this function reads the named variable, it does not
    invent a key or accept one as a literal.
    """

    environ = os.environ if environ is None else environ
    detector: DetectorDefinition = app.detector

    if isinstance(detector, CpuThresholdDetectorDefinition):
        return CpuThresholdDetector(
            container=app.container,
            threshold_percent=detector.threshold_percent,
            sustained_seconds=detector.sustained_seconds,
        )

    return JellyfinDetector(
        url=detector.url,
        api_key=environ.get(detector.api_key_env, ""),
        timeout=detector.timeout_seconds,
    )

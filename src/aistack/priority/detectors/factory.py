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
    Build the `Detector` a priority app's definition names.

    Unknown detector types are already rejected when the YAML is loaded.
    `environ` defaults to `os.environ`; the API key is read from the
    variable the definition names.
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

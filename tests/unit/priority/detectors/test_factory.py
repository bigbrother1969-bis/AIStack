from aistack.priority.definition import (
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
)
from aistack.priority.detectors.cpu_threshold import CpuThresholdDetector
from aistack.priority.detectors.factory import build_detector
from aistack.priority.detectors.jellyfin import JellyfinDetector


def test_a_jellyfin_detector_definition_builds_a_jellyfin_detector():
    app = PriorityAppDefinition(
        container="jellyfin",
        normal_cpus=3,
        boosted_cpus=4,
        detector=JellyfinDetectorDefinition(
            url="http://127.0.0.1:8096", api_key_env="JELLYFIN_API_KEY"
        ),
    )

    detector = build_detector(app, environ={"JELLYFIN_API_KEY": "secret"})

    assert isinstance(detector, JellyfinDetector)
    assert detector._provider.url == "http://127.0.0.1:8096"
    assert detector._provider.api_key == "secret"


def test_a_missing_environment_variable_reads_as_an_empty_key():
    """
    GOV-P-001: this function reads the named variable, it does not
    invent one — a key that is not set in the environment is passed
    through as empty, the same fallback `JellyfinProvider` itself
    already treats as "no key was provided".
    """

    app = PriorityAppDefinition(
        container="jellyfin",
        normal_cpus=3,
        boosted_cpus=4,
        detector=JellyfinDetectorDefinition(
            url="http://127.0.0.1:8096", api_key_env="JELLYFIN_API_KEY"
        ),
    )

    detector = build_detector(app, environ={})

    assert detector._provider.api_key == ""


def test_a_cpu_threshold_detector_definition_builds_a_cpu_threshold_detector():
    app = PriorityAppDefinition(
        container="some-app",
        normal_cpus=1,
        boosted_cpus=2,
        detector=CpuThresholdDetectorDefinition(
            threshold_percent=70.0, sustained_seconds=30.0
        ),
    )

    detector = build_detector(app, environ={})

    assert isinstance(detector, CpuThresholdDetector)
    assert detector._container == "some-app"
    assert detector._threshold_percent == 70.0
    assert detector._sustained_seconds == 30.0

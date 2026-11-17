"""
The Tasks AIStack declares.

A Task is built on what a technology provides, so it lives outside the
Kernel (ADR-0027 § 7). The Kernel knows the `Task` contract and the
registry; `registrations.yml` names the Tasks it registers.
"""

from aistack.tasks.ai_reason import AiReasonTask
from aistack.tasks.architecture_render import ArchitectureRenderTask
from aistack.tasks.console_render import ConsoleRenderTask
from aistack.tasks.declarations_observe import DeclarationsObserveTask
from aistack.tasks.docker_discover import DockerDiscoverTask
from aistack.tasks.health_render import HealthRenderTask
from aistack.tasks.knowledge_integrity import KnowledgeIntegrityTask
from aistack.tasks.network_docker_discover import NetworkDockerDiscoverTask
from aistack.tasks.timemachine_rebuild import TimeMachineRebuildTask

__all__ = [
    "AiReasonTask",
    "ArchitectureRenderTask",
    "ConsoleRenderTask",
    "DeclarationsObserveTask",
    "DockerDiscoverTask",
    "HealthRenderTask",
    "KnowledgeIntegrityTask",
    "NetworkDockerDiscoverTask",
    "TimeMachineRebuildTask",
]

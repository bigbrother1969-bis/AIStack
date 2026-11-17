"""
The Tasks AIStack declares.

A Task is built on what a technology provides, so it lives outside the
Kernel (ADR-0027 § 7). The Kernel knows the `Task` contract and the
registry; `registrations.yml` names the Tasks it registers.
"""

from aistack.tasks.architecture_render import ArchitectureRenderTask
from aistack.tasks.console_render import ConsoleRenderTask
from aistack.tasks.docker_discover import DockerDiscoverTask
from aistack.tasks.health_render import HealthRenderTask

__all__ = [
    "ArchitectureRenderTask",
    "ConsoleRenderTask",
    "DockerDiscoverTask",
    "HealthRenderTask",
]

"""Declarations as files, for a test that needs one on disk."""

from __future__ import annotations

from pathlib import Path

from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.yaml import render_network_discovery_yaml
from aistack.kernel.selection import Selection
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.yaml import render_resource_priority_yaml
from aistack.selection.yaml import render_selection_yaml


def save_network_discovery(definition: NetworkDiscoveryDefinition, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_network_discovery_yaml(definition), encoding="utf-8")
    return path


def save_resource_priority(definition: ResourcePriorityDefinition, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_resource_priority_yaml(definition), encoding="utf-8")
    return path


def save_selection(selection: Selection, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_selection_yaml(selection), encoding="utf-8")
    return path

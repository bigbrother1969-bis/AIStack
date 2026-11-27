from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from aistack.boot_checks.expiry import DOMAIN, HOST
from aistack.boot_checks.definition import (
    CIRCUMSTANCES,
    DEFAULT_CATALOGUE,
    DEFAULT_SEVERITY,
    EXTRA_CONTROLS,
    FINDINGS,
    SEVERITIES,
    BootChecksDefinition,
)

_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def load_boot_checks_yaml(path: Path) -> BootChecksDefinition:
    """Load the start-up checks declaration; a wrong shape raises a `ValueError` naming the file and the key."""

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"Boot checks definition must contain a mapping: {path}")

    label = f"Boot checks definition {path}"
    defaults = BootChecksDefinition()
    ai = _section(data, "ai", label)
    summary = _section(data, "summary", label)
    window = _section(data, "backup_window", label)

    return BootChecksDefinition(
        settle_minutes=_positive_int(
            data, "settle_minutes", defaults.settle_minutes, label
        ),
        expected_containers=_names(
            data.get("expected_containers"), f"{label}: expected_containers"
        ),
        expected_stopped=_names(
            data.get("expected_stopped"), f"{label}: expected_stopped"
        ),
        mounts=_paths(data.get("mounts"), f"{label}: mounts"),
        expected_monitors=_names(data.get("expected_monitors"), f"{label}: expected_monitors"),
        disk_report_hours=_positive_int(data, "disk_report_hours", defaults.disk_report_hours, label),
        disk_old_hours=_optional_count(data, "disk_old_hours", label),
        disk_temperature_celsius=_positive_int(data, "disk_temperature_celsius", defaults.disk_temperature_celsius, label),
        disk_rising_days=_positive_int(data, "disk_rising_days", defaults.disk_rising_days, label),
        history_days=_positive_int(data, "history_days", defaults.history_days, label),
        history_events=_positive_int(data, "history_events", defaults.history_events, label),
        data_disk_percent=_positive_int(data, "data_disk_percent", defaults.data_disk_percent, label),
        usage_points=_paths(data.get("usage_points"), f"{label}: usage_points"),
        usage_days=_positive_int(data, "usage_days", defaults.usage_days, label),
        disk_full_days=_positive_int(data, "disk_full_days", defaults.disk_full_days, label),
        disk_trend_days=_positive_int(data, "disk_trend_days", defaults.disk_trend_days, label),
        disk_trend_min_days=_positive_int(data, "disk_trend_min_days", defaults.disk_trend_min_days, label),
        system_disk_percent=_positive_int(data, "system_disk_percent", defaults.system_disk_percent, label),
        system_memory_percent=_positive_int(data, "system_memory_percent", defaults.system_memory_percent, label),
        system_temperature_celsius=_positive_int(data, "system_temperature_celsius", defaults.system_temperature_celsius, label),
        docker_user_rules=_optional_count(data, "docker_user_rules", label),
        probes=_probes(data.get("probes"), label),
        copies=_copies(data.get("copies"), label),
        certificates=_certificates(data.get("certificates"), label),
        domains=_domains(data.get("domains"), label),
        recurrence_days=_positive_int(data, "recurrence_days", defaults.recurrence_days, label),
        recurrence_starts=_positive_int(data, "recurrence_starts", defaults.recurrence_starts, label),
        certificate_days=_positive_int(data, "certificate_days", defaults.certificate_days, label),
        certificate_urgent_days=_positive_int(data, "certificate_urgent_days", defaults.certificate_urgent_days, label),
        domain_days=_positive_int(data, "domain_days", defaults.domain_days, label),
        domain_urgent_days=_positive_int(data, "domain_urgent_days", defaults.domain_urgent_days, label),
        ups_expected=_ups(data.get("ups_expected"), defaults.ups_expected, label),
        severity=_severity(data.get("severity"), label),
        companions=_flag(data, "companions", defaults.companions, label),
        companion_silent_minutes=_positive_int(
            data, "companion_silent_minutes", defaults.companion_silent_minutes, label
        ),
        companion_mounts=_companion_mounts(data.get("companion_mounts"), label),
        database_containers=_names(data.get("database_containers"), f"{label}: database_containers"),
        timezone=_zone(data.get("timezone"), defaults.timezone, label),
        backup_window=(
            _clock(window, "from", defaults.backup_window[0], f"{label}: backup_window"),
            _clock(window, "until", defaults.backup_window[1], f"{label}: backup_window"),
        ),
        recent_restart_hours=_positive_int(data, "recent_restart_hours", defaults.recent_restart_hours, label),
        memory_pressure_percent=_positive_int(data, "memory_pressure_percent", defaults.memory_pressure_percent, label),
        swap_used_percent=_positive_int(data, "swap_used_percent", defaults.swap_used_percent, label),
        catalogue=_catalogue(data.get("catalogue"), label),
        indicator_weighted=_flag(
            data, "indicator_weighted", defaults.indicator_weighted, label
        ),
        ai_enabled=_flag(ai, "enabled", defaults.ai_enabled, f"{label}: ai"),
        ai_max_extra_controls=_positive_int(
            ai, "max_extra_controls", defaults.ai_max_extra_controls, f"{label}: ai"
        ),
        summary_enabled=_flag(
            summary, "enabled", defaults.summary_enabled, f"{label}: summary"
        ),
        summary_at=_clock(summary, "at", defaults.summary_at, f"{label}: summary"),
    )


def _section(data: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = data.get(key)

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: {key} must be a mapping")

    return value


def _positive_int(data: dict[str, Any], key: str, default: int, label: str) -> int:
    value = data.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label}: {key} must be a positive whole number")

    return value


def _optional_count(data: dict[str, Any], key: str, label: str) -> int | None:
    value = data.get(key)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{label}: {key} must be a whole number, or absent to skip the control"
        )

    return value


def _flag(data: dict[str, Any], key: str, default: bool, label: str) -> bool:
    value = data.get(key, default)

    if not isinstance(value, bool):
        raise ValueError(f"{label}: {key} must be true or false")

    return value


def _clock(data: dict[str, Any], key: str, default: str, label: str) -> str:
    value = data.get(key, default)

    if not isinstance(value, str) or not _CLOCK.match(value):
        raise ValueError(f'{label}: {key} must be a time such as "08:00"')

    return value


def _names(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a list of names")

    return tuple(value)


def _paths(value: Any, label: str) -> tuple[str, ...]:
    paths = _names(value, label)

    if not all(item.startswith("/") for item in paths):
        raise ValueError(f"{label} must be absolute paths")

    return paths


def _certificates(value: Any, label: str) -> tuple[str, ...]:
    """A host (`host` or `host:port`) or the absolute path of a PEM file, each once."""

    if value is None:
        return ()

    if not isinstance(value, list):
        raise ValueError(f"{label}: certificates must be a list of hosts or absolute paths")

    for entry in value:
        if not isinstance(entry, str) or not (HOST.fullmatch(entry) or (entry.startswith("/") and ".." not in entry.split("/") and "\n" not in entry)):
            raise ValueError(f"{label}: certificates: {entry!r} is neither a host (host or host:port) nor an absolute path")

    return tuple(dict.fromkeys(value))


def _domains(value: Any, label: str) -> dict[str, str]:
    """A list of domain names, or a mapping from a name to the date (`YYYY-MM-DD`) to use when its registry publishes none."""

    if value is None:
        return {}

    if isinstance(value, list):
        value = dict.fromkeys(value)

    if not isinstance(value, dict):
        raise ValueError(f"{label}: domains must be a list of names, or a mapping from a name to a date")

    found: dict[str, str] = {}

    for name, declared in value.items():
        if not isinstance(name, str) or not DOMAIN.fullmatch(name):
            raise ValueError(f"{label}: domains: {name!r} is not a domain name")

        text = "" if declared is None else str(declared)

        if text:
            try:
                date.fromisoformat(text)
            except ValueError as error:
                raise ValueError(f"{label}: domains.{name} must be a date such as 2027-03-11") from error

        found[name] = text

    return found


def _copies(value: Any, label: str) -> dict[str, int]:
    """`copies: {label: days}`: the most days that may pass since the newest file of that copy was made."""

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: copies must map a copy's label to the most days since its newest file")

    for name, days in value.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,60}", name):
            raise ValueError(f"{label}: copies.{name} is not a label (letters, digits, - _ .)")

        if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
            raise ValueError(f"{label}: copies.{name} must be a positive number of days")

    return dict(value)


def _probes(value: Any, label: str) -> dict[str, int]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: probes must map a probe's label to the HTTP status it must answer")

    found: dict[str, int] = {}

    for name, status in value.items():
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise ValueError(f"{label}: probes.{name} must be an HTTP status such as 200")

        found[str(name)] = status

    return found


def _companion_mounts(value: Any, label: str) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: companion_mounts must map a host's name to the paths mounted on it")

    return {str(host): _paths(paths, f"{label}: companion_mounts.{host}") for host, paths in value.items()}


def _ups(value: Any, default: tuple[str, ...], label: str) -> tuple[str, ...]:
    if value is None:
        return default

    names = _names(value, f"{label}: ups_expected")

    if not names:
        raise ValueError(f"{label}: ups_expected must name at least one status, such as OL")

    return names


def _severity(value: Any, label: str) -> dict[str, str]:
    severity = dict(DEFAULT_SEVERITY)

    if value is None:
        return severity

    if not isinstance(value, dict):
        raise ValueError(
            f"{label}: severity must map a finding to ignore, warning or critical"
        )

    for finding, level in value.items():
        if finding not in FINDINGS:
            raise ValueError(
                f"{label}: severity.{finding} is not a known finding ({', '.join(FINDINGS)})"
            )

        if level not in SEVERITIES:
            raise ValueError(
                f"{label}: severity.{finding} must be one of {', '.join(SEVERITIES)}"
            )

        severity[finding] = level

    return severity


def _zone(value: Any, default: str, label: str) -> str:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    if value is None:
        return default

    try:
        ZoneInfo(str(value))
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise ValueError(f"{label}: timezone {value!r} is not a time zone such as Europe/Paris") from None

    return str(value)


def _catalogue(value: Any, label: str) -> dict[str, tuple[str, ...]]:
    """Which circumstances justify each extra control; a control or a circumstance outside the closed lists is refused."""

    catalogue = dict(DEFAULT_CATALOGUE)

    if value is None:
        return catalogue

    if not isinstance(value, dict):
        raise ValueError(f"{label}: catalogue must map an extra control to its circumstances")

    for control, when in value.items():
        if control not in EXTRA_CONTROLS:
            raise ValueError(f"{label}: catalogue.{control} is not a known extra control ({', '.join(EXTRA_CONTROLS)})")

        if not isinstance(when, list) or not all(item in CIRCUMSTANCES for item in when):
            raise ValueError(f"{label}: catalogue.{control} must list circumstances among {', '.join(CIRCUMSTANCES)}")

        catalogue[control] = tuple(when)

    return catalogue

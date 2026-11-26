from __future__ import annotations

from dataclasses import dataclass, field

# How much a finding weighs. `ignore` drops the control for this owner.
IGNORE = "ignore"
WARNING = "warning"
CRITICAL = "critical"
SEVERITIES = (IGNORE, WARNING, CRITICAL)

# The findings the base controls can raise. A closed list: the declaration
# may change how much one weighs, never add one.
FINDINGS = (
    "failed_unit",
    "container_missing",
    "container_stopped",
    "container_unhealthy",
    "mount_missing",
    "docker_user_changed",
    "kvm_modules",
    "backup_failed",
    "backup_late",
    "storage_low",
    "probe_failed",
    "ups_on_battery",
    "monitor_down",
    "companion_unreachable",
    "companion_throttled",
)

DEFAULT_SEVERITY = {
    "failed_unit": CRITICAL,
    "container_missing": CRITICAL,
    "container_stopped": WARNING,
    "container_unhealthy": WARNING,
    "mount_missing": CRITICAL,
    "docker_user_changed": WARNING,
    "kvm_modules": IGNORE,
    "backup_failed": CRITICAL,
    "backup_late": WARNING,
    "storage_low": WARNING,
    "probe_failed": CRITICAL,
    "ups_on_battery": WARNING,
    "monitor_down": WARNING,
    "companion_unreachable": CRITICAL,
    "companion_throttled": WARNING,
}


@dataclass(frozen=True)
class BootChecksDefinition:
    """
    What a healthy start is, as the owner declared it.

    `expected_containers` is the reference list of containers that must
    exist after a start and `expected_stopped` the ones kept stopped on
    purpose; an empty reference list means the control is not declared and
    is skipped, never guessed. `mounts` are the paths that must be mounted.
    `docker_user_rules` is the number of rules the DOCKER-USER chain holds
    (`None` skips the control). `probes` maps the label of a probe the host
    unit asks to the status it must answer. `severity` says how much each finding
    weighs. Thresholds of disks, backups and the UPS are not repeated here:
    the controls reuse OPS-0005, OPS-0006 and the health cockpit.
    """

    settle_minutes: int = 10
    expected_containers: tuple[str, ...] = ()
    expected_stopped: tuple[str, ...] = ()
    mounts: tuple[str, ...] = ()
    docker_user_rules: int | None = None
    # label -> the HTTP status the host's probe of that label must answer.
    probes: dict[str, int] = field(default_factory=dict)
    # What the first word of the UPS status may be (`OL` = on line).
    ups_expected: tuple[str, ...] = ("OL",)
    severity: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SEVERITY))
    companions: bool = True
    # A companion whose last facts are older than this is unreachable (its push runs every 15 minutes).
    companion_silent_minutes: int = 45
    # host name (as in hosts.yml) -> the paths that must be mounted on that host after a start.
    companion_mounts: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # The indicator sits beside the weighted health score, not inside it.
    indicator_weighted: bool = False
    ai_enabled: bool = True
    ai_max_extra_controls: int = 3
    summary_enabled: bool = True
    summary_at: str = "08:00"

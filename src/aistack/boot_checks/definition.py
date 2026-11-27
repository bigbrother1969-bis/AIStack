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
    "disk_failing",
    "disk_attribute",
    "disk_counter_rising",
    "disk_hot",
    "system_down",
    "system_pressure",
    "disk_full_soon",
    "data_disk_full",
    "data_disk_soon",
    "companion_unreachable",
    "companion_throttled",
    "database_recovery",
    "kernel_disk_errors",
    "memory_pressure",
    "copy_late",
    "copy_missing",
    "restore_test_failed",
    "restore_test_old",
    "certificate_soon",
    "certificate_urgent",
    "certificate_invalid",
    "domain_soon",
    "domain_urgent",
    "anomaly_recurring",
)

# The circumstances the code computes from the facts, and the extra controls a circumstance may justify
# (ADR-0032 § 3, slice B5a). Both lists are closed: the declaration may link them differently, never add one.
CIRCUMSTANCES = ("unclean_previous_stop", "ups_event", "recent_restart", "restart_in_backup_window", "memory_pressure")
EXTRA_CONTROLS = ("database_recovery", "kernel_disk_errors", "restart_cause", "backup_after_restart", "memory")
DEFAULT_CATALOGUE = {
    "database_recovery": ("unclean_previous_stop",),
    "kernel_disk_errors": ("unclean_previous_stop",),
    "restart_cause": ("recent_restart", "ups_event"),
    "backup_after_restart": ("restart_in_backup_window",),
    "memory": ("memory_pressure",),
}

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
    "disk_failing": CRITICAL,
    "disk_attribute": WARNING,
    "disk_counter_rising": WARNING,
    "disk_hot": WARNING,
    "system_down": WARNING,
    "system_pressure": WARNING,
    "disk_full_soon": WARNING,
    "data_disk_full": WARNING,
    "data_disk_soon": WARNING,
    "companion_unreachable": CRITICAL,
    "companion_throttled": WARNING,
    "database_recovery": WARNING,
    "kernel_disk_errors": CRITICAL,
    "memory_pressure": WARNING,
    "copy_late": WARNING,
    "copy_missing": CRITICAL,
    "restore_test_failed": CRITICAL,
    "restore_test_old": WARNING,
    "certificate_soon": WARNING,
    "certificate_urgent": CRITICAL,
    "certificate_invalid": WARNING,
    "domain_soon": WARNING,
    "domain_urgent": CRITICAL,
    "anomaly_recurring": WARNING,
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
    # The Uptime Kuma monitors that must be running after a start (by name); empty = no reference list.
    expected_monitors: tuple[str, ...] = ()
    # Scrutiny: a disk with no report for this many hours is not read; one with at least `disk_old_hours` of use is said
    # to be old (`None` = say nothing of age).
    disk_report_hours: int = 36
    disk_old_hours: int | None = None
    # O5: a disk whose temperature reaches this (degrees) is to watch; a counter of its SMART report that rose within the
    # last `disk_rising_days` is to watch too.
    disk_temperature_celsius: int = 55
    disk_rising_days: int = 30
    # Beszel: a machine whose disk or memory use, in percent, or whose temperature, in degrees, reaches this is to watch.
    system_disk_percent: int = 90
    system_memory_percent: int = 90
    system_temperature_celsius: int = 80
    # The history of the verdicts (O2): how many days and how many lines the journal keeps, the oldest going first.
    history_days: int = 180
    history_events: int = 2000
    # The trend of the system disks (O4): a line through the last `disk_trend_days` of Beszel's measures, said only with at
    # least `disk_trend_min_days` of history; a disk that would be full within `disk_full_days` is to watch.
    disk_full_days: int = 30
    # The data disks (O4b): at or above this percent a disk is to watch; `usage_points` names them, empty means
    # everything mounted under /media or /mnt; the journal of samples keeps `usage_days` days.
    data_disk_percent: int = 90
    usage_points: tuple[str, ...] = ()
    usage_days: int = 60
    disk_trend_days: int = 14
    disk_trend_min_days: int = 7
    # The copies the host unit looks at (O6): label -> the most days that may pass since the newest file of that copy was made.
    # Empty = none declared: the control is skipped, AIStack never guesses a copy.
    copies: dict[str, int] = field(default_factory=dict)
    # What expires (O7). A certificate is a host (`host` or `host:port`, asked for the certificate it presents) or the absolute
    # path of a PEM file; a domain is a name, with the date declared by hand (`YYYY-MM-DD`, or empty) for a registry that does
    # not publish one. Ending within the first number of days is to watch, within the second (or past) is to fix.
    certificates: tuple[str, ...] = ()
    domains: dict[str, str] = field(default_factory=dict)
    # What was recorded just before an anomaly (O8): how many hours back, and how many facts at most (the nearest ones).
    frieze_hours: int = 6
    frieze_events: int = 8
    recurrence_days: int = 60
    recurrence_starts: int = 3
    certificate_days: int = 21
    certificate_urgent_days: int = 7
    domain_days: int = 60
    domain_urgent_days: int = 14
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
    # The containers of the databases whose log is read for a recovery after the start (the host unit reads the same names).
    database_containers: tuple[str, ...] = ()
    # The owner's time zone, for the backup window; a restart is "recent" under this many hours.
    timezone: str = "Europe/Paris"
    backup_window: tuple[str, str] = ("02:00", "05:00")
    recent_restart_hours: int = 12
    # Memory: the 5-minute pressure and the swap in use that call for the memory control, in percent.
    memory_pressure_percent: int = 10
    swap_used_percent: int = 50
    # extra control -> the circumstances that justify it.
    catalogue: dict[str, tuple[str, ...]] = field(default_factory=lambda: dict(DEFAULT_CATALOGUE))
    # The indicator sits beside the weighted health score, not inside it.
    indicator_weighted: bool = False
    ai_enabled: bool = True
    ai_max_extra_controls: int = 3
    summary_enabled: bool = True
    summary_at: str = "08:00"

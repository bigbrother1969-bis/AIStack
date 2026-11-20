from __future__ import annotations

from dataclasses import dataclass, field


# Paths (shell patterns, `*` crosses `/`) whose change on a host is worth a
# look: accounts, privilege, remote access, firewall, VPN, UPS, tunnel,
# programs the owner installs by hand and scheduled jobs.
DRIFT_SENSITIVE = (
    "/etc/sudoers", "/etc/sudoers.d/*", "/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow",
    "/etc/ssh/*", "/etc/pam.d/*", "/etc/ufw/*", "/etc/wireguard/*", "/etc/nut/*", "/etc/cloudflared/*",
    "/etc/hosts", "/etc/crontab", "/etc/cron.*/*", "/var/spool/cron/*", "/usr/local/sbin/*", "/usr/local/bin/*",
    "*/authorized_keys",
)
# Files that change all the time by themselves: counted, never reported.
DRIFT_NOISE = (
    "/etc/cups/*", "/etc/fake-hwclock.data", "/etc/resolv.conf", "/etc/mtab", "/etc/adjtime",
    "*.dpkg-new", "*.dpkg-old", "*.dpkg-dist", "*.dpkg-tmp", "*.O",
)


@dataclass(frozen=True)
class SecurityDefinition:
    """
    What the owner declares about the host's exposure (ADR-0028 § 2).

    `declared_ports` are the ports the owner expects to find listening on
    every interface, with their purpose: a declared port is no longer
    reported. `sensitive_ports` are ports whose service should not be
    reachable from every network (a database, a file share, SSH): listening
    on every interface without being declared is a finding to watch.
    `critical_ports` are ports whose service gives control of the host to
    whoever reaches it (the Docker API): the same, as a finding to fix.
    `accepted` names, per kind of risk, the containers the owner accepts
    carrying it (a monitor with the Docker socket, say): they are counted,
    not reported. `max_image_age_days` is how old a running container's
    image may be before it is a finding to watch. `max_listed` bounds how many names one finding carries.
    The `drift_*` and `accepted_drift` fields judge what the host collectors
    of ADR-0020 saw change in the last `drift_window_hours`.
    """

    declared_ports: dict[int, str] = field(default_factory=dict)
    sensitive_ports: dict[int, str] = field(default_factory=dict)
    critical_ports: dict[int, str] = field(default_factory=dict)
    accepted: dict[str, tuple[str, ...]] = field(default_factory=dict)
    max_image_age_days: int = 365
    max_reboot_pending_days: int = 14
    max_apt_age_days: int = 7
    accepted_files: tuple[str, ...] = ()
    max_listed: int = 20
    # T3a: drift of host files and units read from the ADR-0020 records.
    drift_window_hours: int = 24
    drift_apt_grace_minutes: int = 60
    drift_sensitive: tuple[str, ...] = DRIFT_SENSITIVE
    drift_noise: tuple[str, ...] = DRIFT_NOISE
    accepted_drift: tuple[str, ...] = ()
    # T3b: refused packets counted from the firewall's counters.
    refusal_window_hours: int = 24
    refusal_watch_per_hour: int = 0
    # T3c: failed logins and scanner requests counted from the host's logs (0 = information only).
    ssh_failed_outside_watch: int = 0
    npm_scans_outside_watch: int = 0

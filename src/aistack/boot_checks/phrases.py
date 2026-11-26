"""
The sentences of the controls, in the owner's language (ADR-0032).

The controls write their sentences in English, once, and the verdict keeps them so:
a stable text for the file, the command, the tests and the engines that will read
it. What the owner reads, on the page and in the morning message, goes through
`say`, which recognises each sentence by its form and gives the catalog's version,
with the numbers and names the sentence carried. A sentence it does not know (a
note that comes from another part of the program, the reason a source could not
be read) is shown as it is, never guessed.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from aistack.boot_checks.disks import COUNTERS

# (catalog key under `boot_check.phrase`, the English sentence as a pattern).
RULES: tuple[tuple[str, str], ...] = (
    ("failed_units_some", r"(?P<n>\d+) unit\(s\) failed"),
    ("failed_units_none", r"no failed unit"),
    ("mounts_none_declared", r"no mount declared"),
    ("mounts_missing", r"(?P<n>\d+) mount\(s\) missing"),
    ("mounts_present", r"(?P<n>\d+) declared mount\(s\) present"),
    ("containers_no_list", r"no reference list of containers declared"),
    ("containers_missing", r"(?P<n>\d+) container\(s\) missing"),
    ("containers_stopped", r"(?P<n>\d+) container\(s\) stopped"),
    ("containers_present", r"(?P<n>\d+) expected present, (?P<running>\d+) running"),
    ("health_unhealthy", r"(?P<n>\d+) container\(s\) unhealthy"),
    ("health_starting", r"(?P<n>\d+) container\(s\) still starting"),
    ("health_none", r"no container unhealthy"),
    ("docker_user_not_declared", r"number of DOCKER-USER rules not declared"),
    ("docker_user_changed", r"the DOCKER-USER chain changed"),
    ("docker_user_ok", r"(?P<n>\d+) rules, as declared"),
    ("docker_user_detail", r"declared (?P<declared>\d+), found (?P<found>\d+)"),
    ("probes_none_declared", r"no probe declared"),
    ("probes_failed", r"(?P<n>\d+) probe\(s\) failed"),
    ("probes_ok", r"(?P<n>\d+) probe\(s\) answer as declared"),
    ("probe_unread", r"(?P<label>.+): not read instead of (?P<want>.+)"),
    ("probe_wrong", r"(?P<label>.+): (?P<got>.+) instead of (?P<want>.+)"),
    ("kvm_loaded", r"KVM modules are loaded"),
    ("kvm_not_loaded", r"KVM modules not loaded"),
    ("ups_none_declared", r"no UPS declared on the host"),
    ("ups_says", r"the UPS says (?P<says>.+)"),
    ("previous_unknown", r"the end of the previous run is not known"),
    ("previous_clean", r"the previous run ended with a clean shutdown"),
    ("previous_unclean", r"the previous run did not end with a shutdown \(power loss or hard stop\)"),
    ("throttled_now", r"a power or temperature limit is active now"),
    ("throttled_since", r"a limit was reached since the start, none now"),
    ("throttled_none", r"no power or temperature limit, now or since the start"),
    ("limit_under_voltage", r"under-voltage"),
    ("limit_frequency_capped", r"frequency capped"),
    ("limit_throttled", r"throttled"),
    ("limit_soft_temperature", r"soft temperature limit"),
    ("clock_network", r"the clock was set by the network"),
    ("clock_not_set", r"the clock is not set by the network yet: the start time may be off"),
    ("reachable_facts", r"facts from (?P<hour>\d\d:\d\d) UTC"),
    ("reachable_none", r"no facts"),
    ("monitor_not_connected", r"Uptime Kuma is not connected \(its address and an API key, in Settings\)"),
    ("monitor_pending", r"(?P<n>\d+) monitor\(s\) still pending"),
    ("monitor_ignored", r"monitor findings are ignored"),
    ("monitor_up", r"(?P<n>\d+) monitor\(s\) up, none down"),
    ("monitor_up_no_list", r"(?P<n>\d+) monitor\(s\) up, none down \(no reference list declared\)"),
    ("disks_not_connected", r"Scrutiny is not connected \(its address, in Settings\)"),
    ("disks_ignored", r"disk findings are ignored"),
    ("disks_head_ok", r"(?P<n>\d+) disk\(s\) read, none failing"),
    ("disks_head", r"(?P<n>\d+) disk\(s\) read"),
    ("disks_failing", r"(?P<n>\d+) failing SMART"),
    ("disks_worn", r"(?P<n>\d+) with a critical SMART attribute above zero"),
    ("disks_stale", r"(?P<n>\d+) not reported for over (?P<hours>\d+) h"),
    ("disks_unread", r"(?P<n>\d+) without readable attributes"),
    ("disks_old", r"(?P<n>\d+) old"),
    ("disks_statistics", r"(?P<n>\d+) flagged only by Scrutiny's statistics"),
    ("disks_rising", r"(?P<n>\d+) with a counter rising"),
    ("disks_hot", r"(?P<n>\d+) at or above (?P<limit>\d+) \u00b0C"),
    ("disks_peaked", r"(?P<n>\d+) peaked at or above (?P<limit>\d+) \u00b0C"),
    ("disks_hot_line", r"(?P<label>.+): (?P<temp>\d+) \u00b0C now \(limit (?P<limit>\d+) \u00b0C\)"),
    ("disks_peak_line", r"(?P<label>.+): reached (?P<peak>\d+) \u00b0C on (?P<date>\d{4}-\d{2}-\d{2})"),
    ("disks_do_backup", r"to do: back up the disks above now and plan to replace them"),
    ("disks_do_cable", r"to do: check the SATA cable and the power connector of the disks above"),
    ("disks_do_cool", r"to do: check the airflow and the fan of the machine"),
    ("throttled_do_power", r"to do: the power supply or its cable is too weak, use the board's own supply"),
    *(
        (f"disks_rise_{number}", r"(?P<label>.+): " + name + r" rose from (?P<a>\d+) to (?P<b>\d+) since (?P<date>\d{4}-\d{2}-\d{2})")
        for number, name in COUNTERS.items()
    ),
    ("systems_not_connected", r"Beszel is not connected \(its account, in Settings\)"),
    ("systems_ignored", r"system findings are ignored"),
    ("systems_head_ok", r"(?P<n>\d+) system\(s\) read, none down, none under pressure"),
    ("systems_head", r"(?P<n>\d+) system\(s\) read"),
    ("systems_down", r"(?P<n>\d+) system\(s\) down"),
    ("systems_disk", r"(?P<n>\d+) with disk use at or above (?P<limit>\d+) %"),
    ("systems_memory", r"(?P<n>\d+) with memory use at or above (?P<limit>\d+) %"),
    ("systems_temperature", r"(?P<n>\d+) at or above (?P<limit>\d+) \u00b0C"),
    ("systems_unread", r"(?P<n>\d+) without readings"),
    ("systems_trend_head_ok", r"(?P<n>\d+) system\(s\) measured, none full within (?P<days>\d+) days"),
    ("systems_trend_head", r"(?P<n>\d+) system\(s\) measured"),
    ("systems_trend_soon", r"(?P<n>\d+) full within (?P<days>\d+) days"),
    ("systems_trend_short", r"(?P<n>\d+) without enough history"),
    ("systems_trend_ignored", r"disk trend findings are ignored"),
    ("systems_trend_line", r"(?P<name>.+): about (?P<left>\d+) day\(s\) left at \+(?P<rate>[\d.]+) GB/day \((?P<used>\d+) of (?P<total>\d+) GB\)"),
    ("systems_not_enough", r"not read: Beszel has less than (?P<days>\d+) days of measures for the system disks"),
    ("data_none", r"no data disk to read \(nothing under /media or /mnt, none declared\)"),
    ("data_ignored", r"data disk findings are ignored"),
    ("data_head_ok", r"(?P<n>\d+) data disk\(s\) read, none at or above (?P<limit>\d+) %, none full within (?P<days>\d+) days"),
    ("data_head", r"(?P<n>\d+) data disk\(s\) read"),
    ("data_full", r"(?P<n>\d+) at or above (?P<limit>\d+) %"),
    ("data_soon", r"(?P<n>\d+) full within (?P<days>\d+) days"),
    ("data_short", r"(?P<n>\d+) without enough history"),
    ("data_line", r"(?P<name>.+): (?P<pct>[\d.]+) % used \((?P<used>\d+) of (?P<total>\d+) GB\)"),
    ("data_trend_line", r"(?P<name>.+): about (?P<left>\d+) day\(s\) left at \+(?P<rate>[\d.]+) GB/day \((?P<used>\d+) of (?P<total>\d+) GB\)"),
    ("systems_silent", r"(?P<name>.+) \(no reading since (?P<when>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\)"),
    ("domain_not_read", r"(?P<domain>storage|backup) was not read"),
    ("domain_not_instrumented", r"(?P<domain>storage|backup) is not instrumented on this host"),
    ("domain_findings", r"(?P<n>\d+) finding\(s\) in the (?P<domain>storage|backup) domain"),
    ("domain_nothing", r"nothing to report in the (?P<domain>storage|backup) domain"),
    ("db_none_declared", r"no database container declared"),
    ("db_recovered", r"(?P<n>\d+) database\(s\) recovered after the start"),
    ("db_ignored", r"database recovery findings are ignored"),
    ("db_unread", r"(?P<n>\d+) database log\(s\) not read"),
    ("db_clean", r"(?P<n>\d+) database log\(s\) read, no recovery"),
    ("kernel_errors", r"(?P<n>\d+) disk or file-system error line\(s\) in the kernel log since the start"),
    ("kernel_clean", r"no disk or file-system error in the kernel log since the start"),
    ("kernel_ignored", r"kernel disk errors are ignored"),
    ("cause_ups", r"the previous run was stopped by the UPS \(power cut\)"),
    ("cause_requested", r"the previous run was stopped by a shutdown or a reboot that was asked for"),
    ("cause_unknown", r"the cause of the previous stop is not in the journal"),
    ("cause_not_known", r"the cause of the previous stop is not known"),
    ("backup_late", r"the start fell in the backup window and the backup domain has (?P<n>\d+) finding\(s\)"),
    ("backup_clean", r"the start fell in the backup window; the backup domain has nothing to report"),
    ("backup_ignored", r"backup findings are ignored"),
    ("backup_unread", r"the backup domain was not read"),
    ("memory_said", r"memory pressure (?P<pressure>.+) %, swap (?P<swap>.+) % in use"),
    ("memory_ignored", r"memory findings are ignored"),
    ("not_read", r"not read: (?P<reason>.+)"),
)

_COMPILED = tuple((key, re.compile(pattern)) for key, pattern in RULES)
_BROKEN = re.compile(r"(?:(?P<down>\d+) down)?(?:, )?(?:(?P<missing>\d+) missing or paused)?(?: \((?P<names>.*)\))?")


def _monitor_broken(t: Callable[..., str], text: str) -> str | None:
    """`2 down, 1 missing or paused (a, b, +1)`: the two counts are told, the names stay as they are (an older incident has none)."""

    found = _BROKEN.fullmatch(text)

    if found is None or not (found["down"] or found["missing"]):
        return None

    parts = []

    if found["down"]:
        parts.append(t("boot_check.phrase.monitor_down", n=found["down"]))

    if found["missing"]:
        parts.append(t("boot_check.phrase.monitor_missing", n=found["missing"]))

    return f"{', '.join(parts)} ({found['names']})" if found["names"] else ", ".join(parts)


def _summary(t: Callable[..., str], text: str) -> str | None:
    """`8 disk(s) read; 1 failing SMART; 2 old`, `3 system(s) read; 1 system(s) down`: each part is told on its own, `None` when one is not the program's."""

    found = re.match(r"\d+ (data disk|disk|system)\(s\) (?:read|measured)", text)

    if found is None:
        return None

    prefix = {"data disk": "data_", "disk": "disks_"}.get(found.group(1), "systems_")

    told = []

    for part in text.split("; "):
        for key, pattern in _COMPILED:
            found = pattern.fullmatch(part) if key.startswith(prefix) else None

            if found is not None:
                told.append(t(f"boot_check.phrase.{key}", **found.groupdict()))
                break
        else:
            return None

    return "; ".join(told)


def say(t: Callable[..., str], text: str) -> str:
    """The sentence in the language of `t`, or the sentence itself when it is not one of the program's own."""

    broken = _monitor_broken(t, text)

    if broken is not None:
        return broken

    summary = _summary(t, text)

    if summary is not None:
        return summary

    for key, pattern in _COMPILED:
        found = pattern.fullmatch(text)

        if found is None:
            continue

        values = found.groupdict()

        if "domain" in values:
            values["domain"] = t(f"boot_check.phrase.domain.{values['domain']}")

        return t(f"boot_check.phrase.{key}", **values)

    return text

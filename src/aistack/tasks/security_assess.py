from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aistack.config import PACKAGE_ROOT, configured
from aistack.generators.security import SecurityAssessmentArtifactGenerator
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.security.definition import SecurityDefinition
from aistack.security.drift import assess_drift
from aistack.security.exposure import assess, propose_declaration, read_listeners, read_published
from aistack.security.findings import SEVERITIES, worst
from aistack.security.firewall import read_firewall
from aistack.security.host import assess_files, assess_packages, assess_remote_hosts, read_host, read_remote_hosts
from aistack.security.logs import assess_logs, read_logs
from aistack.security.refusals import assess_refusals, read_refusals
from aistack.security.hygiene import OLD_IMAGE, Container, assess_hygiene, propose_accepted, read_containers
from aistack.security.images import assess_images, old_images, read_created
from aistack.hosts.records import HostRecords, HostsDeclaration, load_hosts_declaration, read_all
from aistack.security.yaml import load_security_yaml

DEFAULT_GENERATED_DIR = "reports/generated"
# Where the host units aistack-firewall-snapshot and aistack-host-hygiene write, under the data directory.
HOST_DIR = "security-host"

DEFAULT_DEFINITION = configured(PACKAGE_ROOT / "security" / "definitions" / "security.yml")


class SecurityAssessTask:
    """
    Assess what this host exposes (`security.assess`, ADR-0028 slice T1).

    Read-only: it reads the listening sockets and the ports Docker
    publishes, judges them against `security.yml`, and writes the
    assessment as `security-assessment.json` with its history. It changes
    nothing on any host and never carries a secret: a finding holds ports,
    names and counts. The request payload's `generated_dir` (default
    `reports/generated`) says where the report is written.

    Returns an Observation of plain values: where the report went, how
    many findings of each severity, and the worst severity.
    """

    task_id = "security.assess"
    task_name = "Security assessment"

    def execute(self, request: Request) -> Observation:
        generated_dir = Path(request.payload.get("generated_dir", DEFAULT_GENERATED_DIR))

        definition = load_security_yaml(DEFAULT_DEFINITION)
        listeners, unread = read_listeners()
        published = read_published()
        firewall, firewall_note = read_firewall(generated_dir / HOST_DIR)
        packages, host_files, host_note = read_host(generated_dir / HOST_DIR)
        remote_hosts = read_remote_hosts(generated_dir)
        containers = read_containers()
        created = read_created(sorted({item.image_id for item in containers if item.image_id})) if containers else {}
        now = datetime.now(timezone.utc)
        findings = (
            assess(listeners, unread, published, definition, firewall, firewall_note)
            + assess_hygiene(containers, definition)
            + assess_images(containers, created, now, definition)
            + assess_packages(packages, host_note, now, definition)
            + assess_files(host_files, definition)
            + assess_remote_hosts(remote_hosts, now, definition)
            + assess_drift(*read_drift(generated_dir), now, definition)
            + assess_logs(read_logs(generated_dir / HOST_DIR, generated_dir), definition)
            + assess_refusals(read_refusals(generated_dir / HOST_DIR), now, definition, firewall is not None)
        )

        assessment = {
            "security": {
                "scope": "the host AIStack runs on",
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "listeners": [
                    {"protocol": item.protocol, "port": item.port, "bind": item.bind}
                    for item in listeners
                ],
                "published": [
                    {"container": item.container, "protocol": item.protocol, "port": item.port, "bind": item.bind}
                    for item in (published or [])
                ],
                "findings": [finding.as_dict() for finding in findings],
            }
        }

        output_path = SecurityAssessmentArtifactGenerator().generate(
            assessment=assessment,
            output_path=generated_dir / "security-assessment.json",
        )

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "output_path": str(output_path),
                "counts": {
                    severity: sum(1 for finding in findings if finding.severity == severity)
                    for severity in SEVERITIES
                },
                "worst": worst(findings) or "",
                "findings": [finding.as_dict() for finding in findings],
                "proposal": (
                    propose_declaration(listeners, published, definition)
                    + (propose_accepted(containers, definition, _old_names(containers, created, now, definition)) if containers is not None else "")
                    if request.payload.get("propose")
                    else ""
                ),
            },
        )


def _old_names(
    containers: list[Container] | None,
    created: dict[str, datetime] | None,
    now: datetime,
    definition: SecurityDefinition,
) -> dict[str, list[str]]:
    if not containers or created is None:
        return {}
    return {OLD_IMAGE: [item.name for item, _ in old_images(containers, created, now, definition)]}


def read_drift(generated_dir: Path) -> tuple[list[HostRecords], HostsDeclaration | None]:
    """The change records of the traced hosts; an unreadable `hosts.yml` is no reason to fail the assessment."""

    try:
        declaration = load_hosts_declaration(generated_dir)
    except (OSError, ValueError, AttributeError):
        return [], None
    return read_all(declaration), declaration

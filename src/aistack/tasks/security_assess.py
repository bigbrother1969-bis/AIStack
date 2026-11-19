from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aistack.config import PACKAGE_ROOT, configured
from aistack.generators.security import SecurityAssessmentArtifactGenerator
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.security.exposure import assess, propose_declaration, read_listeners, read_published
from aistack.security.firewall import read_firewall
from aistack.security.hygiene import assess_hygiene, propose_accepted, read_containers
from aistack.security.findings import SEVERITIES, worst
from aistack.security.yaml import load_security_yaml

DEFAULT_GENERATED_DIR = "reports/generated"
# Where the host unit aistack-firewall-snapshot writes, under the data directory.
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
        containers = read_containers()
        findings = assess(listeners, unread, published, definition, firewall, firewall_note) + assess_hygiene(
            containers, definition
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
                    + (propose_accepted(containers, definition) if containers is not None else "")
                    if request.payload.get("propose")
                    else ""
                ),
            },
        )

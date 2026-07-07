# STD-0002 - Test Artifact Isolation

## Status

Accepted

## Principle

Operational artifacts shall never be used as outputs of tests, demonstrations or development workflows.

Test executions shall always generate dedicated artifacts isolated from production artifacts.

## Rationale

Operational artifacts may already participate in governed workflows such as synchronization, deployment, reporting or knowledge management.

Overwriting them during tests introduces uncontrolled side effects, breaks reproducibility and may affect production workflows.

## Standard

- Tests shall write into dedicated locations such as reports/generated/, examples/generated/ or sandbox/.
- Production artifacts shall only be modified through explicit governed workflows.
- Tests may compare generated artifacts with operational artifacts but shall never overwrite them automatically.

## Examples

- A Syncthing selection used daily shall never be the output of a test run.
- A Docker Runtime Catalog used by AIStack shall not be replaced by a demonstration script.

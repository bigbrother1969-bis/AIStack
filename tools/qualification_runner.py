#!/usr/bin/env python3
"""End-to-end qualification runner for the AIStack Knowledge Transport Layer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from aistack.path.filesystem import FilesystemPathRepository, FilesystemPathResolver
from aistack.transaction.adapters.transport_operation_engine import TransportOperationEngine
from aistack.transaction.contracts.operation import Operation
from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.executor.default_transaction_executor import DefaultTransactionExecutor
from aistack.transaction.registry.in_memory_operation_registry import InMemoryOperationRegistry
from aistack.transport import DefaultTransportEngine
from aistack.transport.capabilities import FilesystemTransportCapability
from aistack.transport.contracts import (
    DeliveryMode,
    ResourceReference,
    TransportEndpoint,
    TransportRequest,
)
from aistack.transport.filesystem import FilesystemReceiver, FilesystemWriter
from aistack.transport.registry import InMemoryTransportRegistry

RUNNER_VERSION = "2.2.0"
TRANSPORT_OPERATION_KIND = "transport"
MIB = 1024 * 1024
GIB = 1024 * MIB
DEFAULT_LARGE_SIZES = (100 * MIB, 500 * MIB, 1 * GIB, 5 * GIB, 20 * GIB, 50 * GIB)
CHUNK_SIZE = 8 * MIB
SAMPLE_INTERVAL_SECONDS = 0.25
HEARTBEAT_INTERVAL_SECONDS = 5.0


@dataclass(slots=True)
class Metrics:
    duration_seconds: float = 0.0
    source_size_bytes: int = 0
    throughput_mib_per_second: float = 0.0
    process_cpu_seconds: float = 0.0
    system_cpu_average_percent: float | None = None
    system_cpu_peak_percent: float | None = None
    process_rss_peak_bytes: int | None = None
    source_sha256_seconds: float = 0.0
    destination_sha256_seconds: float = 0.0


@dataclass(slots=True)
class ScenarioResult:
    scenario_id: str
    description: str
    mandatory: bool
    success: bool
    explanation: str
    source: str | None = None
    destination: str | None = None
    delivery_mode: str | None = None
    expected: dict[str, Any] = field(default_factory=dict)
    observed: dict[str, Any] = field(default_factory=dict)
    metrics: Metrics = field(default_factory=Metrics)
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class QualificationReport:
    qualification_id: str
    started_at: str
    finished_at: str = ""
    runner_version: str = RUNNER_VERSION
    git_commit: str | None = None
    environment: dict[str, Any] = field(default_factory=dict)
    results: list[ScenarioResult] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        total = len(self.results)
        succeeded = sum(result.success for result in self.results)
        failed = total - succeeded
        mandatory_failed = sum(
            not result.success and result.mandatory for result in self.results
        )
        durations = [result.metrics.duration_seconds for result in self.results]
        throughputs = [
            result.metrics.throughput_mib_per_second
            for result in self.results
            if result.metrics.source_size_bytes > 0
            and result.metrics.duration_seconds > 0
        ]
        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "mandatory_failed": mandatory_failed,
            "duration_seconds": sum(durations),
            "average_throughput_mib_per_second": (
                sum(throughputs) / len(throughputs) if throughputs else 0.0
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["summary"] = self.summary()
        return payload


class SystemSampler:
    """Samples host CPU usage and current process RSS while a scenario runs."""

    def __init__(self, interval_seconds: float = SAMPLE_INTERVAL_SECONDS) -> None:
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.cpu_samples: list[float] = []
        self.rss_samples: list[int] = []

    def start(self) -> None:
        self._stop_event.clear()
        self._sample_once()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds * 4)
        self._sample_once()

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            self._sample_once()

    def _sample_once(self) -> None:
        cpu = read_system_cpu_percent(self._interval_seconds / 4)
        if cpu is not None:
            self.cpu_samples.append(cpu)
        rss = read_process_rss_bytes()
        if rss is not None:
            self.rss_samples.append(rss)


class HashDeliveryVerifier:
    """Verifies delivery by comparing source and destination SHA-256 hashes."""

    def __init__(self, resolver: FilesystemPathResolver) -> None:
        self._resolver = resolver

    def verify(self, request: TransportRequest, result: object) -> bool:
        source = self._resolver.resolve(request.source_resource)
        destination = self._resolver.resolve(request.destination_resource)
        return (
            destination.exists()
            and source.stat().st_size == destination.stat().st_size
            and sha256_file(source)[0] == sha256_file(destination)[0]
        )


class ConsoleReporter:
    """Small, dependency-free console UX for long qualification campaigns."""

    def __init__(self, quiet: bool = False, verbose: bool = False) -> None:
        self.quiet = quiet
        self.verbose = verbose
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_started = 0.0
        self._heartbeat_phase = ""

    def banner(self, workspace: Path, reports_root: Path) -> None:
        if self.quiet:
            return
        print("=" * 68, flush=True)
        print(f"AIStack Qualification Runner v{RUNNER_VERSION}", flush=True)
        print("=" * 68, flush=True)
        print(f"Host............... {socket.gethostname()}", flush=True)
        print(f"Workspace.......... {workspace}", flush=True)
        print(f"Reports............ {reports_root}", flush=True)
        print("", flush=True)

    def phase(self, message: str) -> None:
        if not self.quiet:
            print(f"[PHASE] {message}", flush=True)

    def scenario(self, current: int, total: int, scenario_id: str, description: str) -> None:
        if self.quiet:
            return
        print("", flush=True)
        print("-" * 68, flush=True)
        print(f"Scenario {current}/{total}: {scenario_id}", flush=True)
        print(description, flush=True)
        print("-" * 68, flush=True)

    def action(self, message: str) -> None:
        if not self.quiet:
            print(f"  -> {message}", flush=True)

    def detail(self, message: str) -> None:
        if self.verbose and not self.quiet:
            print(f"     {message}", flush=True)

    def progress(self, label: str, current: int, total: int) -> None:
        if self.quiet or total <= 0:
            return
        percent = min(100.0, 100.0 * current / total)
        print(
            f"     {label}: {human_size(current)} / {human_size(total)} "
            f"({percent:5.1f}%)",
            flush=True,
        )

    def result(self, result: ScenarioResult) -> None:
        if self.quiet:
            return
        status = "PASS" if result.success else "FAIL"
        print(
            f"  [{status}] {result.metrics.duration_seconds:.2f} s"
            f" | {result.metrics.throughput_mib_per_second:.2f} MiB/s",
            flush=True,
        )
        if self.verbose or not result.success:
            print(f"     {result.explanation}", flush=True)
            if result.error_message:
                print(
                    f"     {result.error_type}: {result.error_message}",
                    flush=True,
                )

    def start_heartbeat(self, phase: str) -> None:
        self.stop_heartbeat()
        if self.quiet:
            return
        self._heartbeat_phase = phase
        self._heartbeat_started = time.perf_counter()
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=1.0)
        self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        while not self._heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            elapsed = time.perf_counter() - self._heartbeat_started
            print(
                f"     [heartbeat] {self._heartbeat_phase} "
                f"| elapsed {format_duration(elapsed)}",
                flush=True,
            )


class QualificationRunner:
    def __init__(
        self,
        workspace: Path,
        reports_root: Path,
        destination_root: Path | None = None,
        selected_scenario: str | None = None,
        quiet: bool = False,
        verbose: bool = False,
    ) -> None:
        self.workspace = workspace
        self.reports_root = reports_root
        self.console = ConsoleReporter(quiet=quiet, verbose=verbose)
        self.selected_scenario = normalize_scenario_selector(selected_scenario)
        self._scenario_current = 0
        self._scenario_total = 1 if self.selected_scenario else 17 + 1 + 1 + 1 + len(DEFAULT_LARGE_SIZES)
        self.source_root = workspace / "source"
        self.destination_root = (
            destination_root if destination_root is not None else workspace / "destination"
        )
        self.report = QualificationReport(
            qualification_id=datetime.now(timezone.utc).strftime(
                "KTL-%Y%m%dT%H%M%SZ"
            ),
            started_at=iso_now(),
            git_commit=git_commit(),
            environment=collect_environment(),
        )

    def run(self) -> int:
        self.console.banner(self.workspace, self.reports_root)
        self.console.phase("Preparing qualification workspace")
        self._prepare_workspace()
        try:
            self._run_standard_matrix()
            self._run_create_conflict()
            self._run_replace()
            self._run_batch()
            self._run_large_files()
        finally:
            self.console.stop_heartbeat()
            self.console.phase("Writing qualification reports")
            self.report.finished_at = iso_now()
            json_path, markdown_path = self._write_reports()
            self._print_summary(json_path, markdown_path)
        return 1 if self.report.summary()["mandatory_failed"] else 0

    def _prepare_workspace(self) -> None:
        self.console.detail(f"Preparing workspace: {self.workspace}")
        self.workspace.mkdir(parents=True, exist_ok=True)

        if self.source_root.exists():
            shutil.rmtree(self.source_root)
        self.source_root.mkdir(parents=True)

        # Never erase an externally supplied destination root. Only reset the
        # disposable destination directory when it belongs to this workspace.
        if self.destination_root == self.workspace / "destination":
            if self.destination_root.exists():
                shutil.rmtree(self.destination_root)
        self.destination_root.mkdir(parents=True, exist_ok=True)

        if not os.access(self.workspace, os.W_OK):
            raise PermissionError(f"Workspace is not writable: {self.workspace}")
        if not os.access(self.destination_root, os.W_OK):
            raise PermissionError(
                f"Destination root is not writable: {self.destination_root}"
            )

        workspace_disk = shutil.disk_usage(self.workspace)
        destination_disk = shutil.disk_usage(self.destination_root)
        self.report.environment.update(
            {
                "qualification_workspace": str(self.workspace),
                "qualification_workspace_filesystem": filesystem_type(self.workspace),
                "qualification_workspace_free_bytes": workspace_disk.free,
                "qualification_destination_root": str(self.destination_root),
                "qualification_destination_filesystem": filesystem_type(
                    self.destination_root
                ),
                "qualification_destination_free_bytes": destination_disk.free,
                "selected_scenario": self.selected_scenario,
            }
        )

    def _run_standard_matrix(self) -> None:
        cases: list[tuple[str, bytes, str]] = [
            ("empty.txt", b"", "empty file"),
            ("plain.txt", b"AIStack Knowledge Transport Layer\n", "plain text"),
            (
                "unicode/Connaissance gouvernee - ete.txt",
                "Été, déjà, façade, 日本語, العربية, 🚀\n".encode("utf-8"),
                "Unicode and accented text",
            ),
            (
                "deep/a/b/c/d/e/f/knowledge.json",
                json.dumps(
                    {"project": "AIStack", "governed": True, "score": 1.0},
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
                "deep directory tree",
            ),
            ("table.csv", b"id,name\n1,AIStack\n2,Oak-15\n", "CSV"),
            ("policy.yaml", b"policy:\n  owner: aistack\n  trust: 1.0\n", "YAML"),
            ("document.pdf", deterministic_bytes(128 * 1024), "PDF extension"),
            ("document.docx", deterministic_bytes(128 * 1024), "DOCX extension"),
            ("document.odt", deterministic_bytes(128 * 1024), "ODT extension"),
            ("presentation.pptx", deterministic_bytes(128 * 1024), "PPTX extension"),
            ("image.png", deterministic_bytes(256 * 1024), "PNG extension"),
            ("photo.jpg", deterministic_bytes(256 * 1024), "JPG extension"),
            ("archive.zip", deterministic_bytes(512 * 1024), "ZIP extension"),
            ("audio.mp3", deterministic_bytes(512 * 1024), "MP3 extension"),
            ("audio.flac", deterministic_bytes(512 * 1024), "FLAC extension"),
            ("video.mkv", deterministic_bytes(1 * MIB), "MKV extension"),
            ("binary.bin", deterministic_bytes(1 * MIB), "binary content"),
        ]
        for index, (relative_path, content, description) in enumerate(cases, 1):
            scenario_id = f"standard-{index:02d}"
            if not self._should_run(scenario_id):
                continue
            self._announce_scenario(scenario_id, description)
            source = self.source_root / relative_path
            destination = self.destination_root / relative_path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(content)
            self._execute_copy(
                scenario_id=scenario_id,
                description=description,
                source=source,
                destination=destination,
                delivery_mode=DeliveryMode.CREATE,
            )

    def _run_create_conflict(self) -> None:
        if not self._should_run("create-conflict"):
            return
        self._announce_scenario(
            "create-conflict",
            "CREATE must preserve an existing destination",
        )
        source = self.source_root / "create-conflict.txt"
        destination = self.destination_root / "create-conflict.txt"
        source.write_bytes(b"new governed content")
        destination.write_bytes(b"existing governed content")
        before_hash, _ = sha256_file(destination)
        result = self._execute_copy(
            scenario_id="create-conflict",
            description="CREATE must preserve an existing destination",
            source=source,
            destination=destination,
            delivery_mode=DeliveryMode.CREATE,
            expected_success=False,
        )
        after_hash, _ = sha256_file(destination)
        preserved = before_hash == after_hash
        result.success = result.success and preserved
        result.observed["destination_preserved"] = preserved
        if not preserved:
            result.explanation = "CREATE overwrote an existing destination."

    def _run_replace(self) -> None:
        if not self._should_run("replace-existing"):
            return
        self._announce_scenario(
            "replace-existing",
            "REPLACE must overwrite an existing destination",
        )
        source = self.source_root / "replace.txt"
        destination = self.destination_root / "replace.txt"
        source.write_bytes(b"replacement content")
        destination.write_bytes(b"obsolete content")
        self._execute_copy(
            scenario_id="replace-existing",
            description="REPLACE must overwrite an existing destination",
            source=source,
            destination=destination,
            delivery_mode=DeliveryMode.REPLACE,
        )

    def _run_batch(self) -> None:
        if not self._should_run("batch-1000-small-files"):
            return
        self._announce_scenario(
            "batch-1000-small-files",
            "Transport 1,000 deterministic 4 KiB files",
        )
        batch_root = self.source_root / "batch"
        destination_root = self.destination_root / "batch"
        count = 1000
        size = 4096
        started = time.perf_counter()
        successful = 0
        errors: list[str] = []
        for index in range(count):
            if index % 100 == 0:
                self.console.action(f"Batch progress: {index}/{count}")
            source = batch_root / f"item-{index:04d}.bin"
            destination = destination_root / f"item-{index:04d}.bin"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(deterministic_bytes(size, seed=index))
            result = self._execute_copy(
                scenario_id=f"batch-item-{index:04d}",
                description="small-file batch member",
                source=source,
                destination=destination,
                delivery_mode=DeliveryMode.CREATE,
                record=False,
            )
            if result.success:
                successful += 1
            else:
                errors.append(result.error_message or result.explanation)
        duration = time.perf_counter() - started
        total_size = count * size
        batch_result = ScenarioResult(
                scenario_id="batch-1000-small-files",
                description="Transport 1,000 deterministic 4 KiB files",
                mandatory=True,
                success=successful == count,
                explanation=(
                    f"All {count} files were delivered and verified."
                    if successful == count
                    else f"{count - successful} batch members failed."
                ),
                expected={"file_count": count, "file_size_bytes": size},
                observed={"successful": successful, "errors": errors[:20]},
                metrics=Metrics(
                    duration_seconds=duration,
                    source_size_bytes=total_size,
                    throughput_mib_per_second=(total_size / MIB / duration),
                ),
            )
        self.report.results.append(batch_result)
        self.console.result(batch_result)

    def _run_large_files(self) -> None:
        for size in DEFAULT_LARGE_SIZES:
            label = human_size(size).replace(" ", "-").lower()
            scenario_id = f"large-{label}"
            if not self._should_run(scenario_id):
                continue
            description = f"Transport a {human_size(size)} file"
            self._announce_scenario(scenario_id, description)
            self._validate_capacity(size)
            source = self.source_root / "large" / f"large-{label}.bin"
            destination = self.destination_root / "large" / f"large-{label}.bin"
            source.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.console.action(f"Generating {human_size(size)} source file")
                self.console.start_heartbeat("Generating source file")
                generate_file(
                    source,
                    size,
                    progress=lambda current, total: self.console.progress(
                        "Generated", current, total
                    ),
                )
                self.console.stop_heartbeat()
                self._execute_copy(
                    scenario_id=scenario_id,
                    description=description,
                    source=source,
                    destination=destination,
                    delivery_mode=DeliveryMode.CREATE,
                )
            except BaseException as error:
                self.report.results.append(
                    ScenarioResult(
                        scenario_id=scenario_id,
                        description=description,
                        mandatory=True,
                        success=False,
                        explanation="The large-file scenario could not complete.",
                        source=str(source),
                        destination=str(destination),
                        delivery_mode=DeliveryMode.CREATE.value,
                        expected={"size_bytes": size},
                        observed={"free_bytes": shutil.disk_usage(self.workspace).free},
                        error_type=type(error).__name__,
                        error_message=str(error),
                    )
                )
            finally:
                source.unlink(missing_ok=True)
                destination.unlink(missing_ok=True)

    def _should_run(self, scenario_id: str) -> bool:
        return self.selected_scenario is None or self.selected_scenario == scenario_id

    def _validate_capacity(self, payload_size: int) -> None:
        """Fail before generation when source or destination capacity is unsafe."""
        safety_factor = 1.10
        source_required = int(payload_size * safety_factor)
        destination_required = int(payload_size * safety_factor)

        source_usage = shutil.disk_usage(self.source_root)
        destination_usage = shutil.disk_usage(self.destination_root)
        same_filesystem = (
            self.source_root.stat().st_dev == self.destination_root.stat().st_dev
        )

        if same_filesystem:
            required = source_required + destination_required
            available = source_usage.free
            self.console.action("Checking qualification storage capacity")
            self.console.detail("Source and destination use the same filesystem")
            self.console.detail(f"Available: {human_size(available)}")
            self.console.detail(f"Required:  {human_size(required)}")
            if available < required:
                raise RuntimeError(
                    "Insufficient qualification capacity on shared filesystem: "
                    f"{human_size(available)} available, "
                    f"{human_size(required)} required"
                )
            return

        self.console.action("Checking source and destination storage capacity")
        self.console.detail(
            f"Source: {human_size(source_usage.free)} available / "
            f"{human_size(source_required)} required"
        )
        self.console.detail(
            f"Destination: {human_size(destination_usage.free)} available / "
            f"{human_size(destination_required)} required"
        )
        if source_usage.free < source_required:
            raise RuntimeError(
                "Insufficient source workspace capacity: "
                f"{human_size(source_usage.free)} available, "
                f"{human_size(source_required)} required"
            )
        if destination_usage.free < destination_required:
            raise RuntimeError(
                "Insufficient destination capacity: "
                f"{human_size(destination_usage.free)} available, "
                f"{human_size(destination_required)} required"
            )

    def _execute_copy(
        self,
        scenario_id: str,
        description: str,
        source: Path,
        destination: Path,
        delivery_mode: DeliveryMode,
        expected_success: bool = True,
        record: bool = True,
    ) -> ScenarioResult:
        result = ScenarioResult(
            scenario_id=scenario_id,
            description=description,
            mandatory=True,
            success=False,
            explanation="Scenario did not complete.",
            source=str(source),
            destination=str(destination),
            delivery_mode=delivery_mode.value,
            expected={"transport_success": expected_success},
        )
        sampler = SystemSampler()
        cpu_started = time.process_time()
        started = time.perf_counter()
        try:
            self.console.action("Calculating source SHA-256")
            self.console.start_heartbeat("Calculating source SHA-256")
            source_hash, source_hash_seconds = sha256_file(source)
            self.console.stop_heartbeat()
            source_size = source.stat().st_size
            before_destination_hash = (
                sha256_file(destination)[0] if destination.exists() else None
            )
            executor, transaction = build_transaction(
                source=source,
                destination=destination,
                delivery_mode=delivery_mode,
            )
            self.console.detail(f"Source: {source}")
            self.console.detail(f"Destination: {destination}")
            self.console.action("Executing real transport transaction")
            self.console.start_heartbeat("Executing transport transaction")
            sampler.start()
            executor.execute(transaction)
            sampler.stop()
            self.console.stop_heartbeat()
            duration = time.perf_counter() - started
            destination_exists = destination.exists()
            destination_hash = None
            destination_hash_seconds = 0.0
            if destination_exists:
                self.console.action("Verifying destination SHA-256")
                self.console.start_heartbeat("Verifying destination SHA-256")
                destination_hash, destination_hash_seconds = sha256_file(destination)
                self.console.stop_heartbeat()
            delivered_and_verified = (
                destination_exists
                and destination.stat().st_size == source_size
                and destination_hash == source_hash
            )
            if expected_success:
                success = delivered_and_verified
                explanation = (
                    "Destination exists and size and SHA-256 match the source."
                    if success
                    else "Destination integrity verification failed."
                )
            else:
                success = (
                    destination_exists
                    and before_destination_hash == destination_hash
                    and destination_hash != source_hash
                )
                explanation = (
                    "CREATE conflict was rejected and existing content was preserved."
                    if success
                    else "CREATE conflict behavior did not match the contract."
                )
            result.success = success
            result.explanation = explanation
            result.observed = {
                "destination_exists": destination_exists,
                "source_sha256": source_hash,
                "destination_sha256": destination_hash,
                "source_size_bytes": source_size,
                "destination_size_bytes": (
                    destination.stat().st_size if destination_exists else None
                ),
            }
            result.metrics = Metrics(
                duration_seconds=duration,
                source_size_bytes=source_size,
                throughput_mib_per_second=(
                    source_size / MIB / duration if duration > 0 else 0.0
                ),
                process_cpu_seconds=time.process_time() - cpu_started,
                system_cpu_average_percent=(
                    sum(sampler.cpu_samples) / len(sampler.cpu_samples)
                    if sampler.cpu_samples
                    else None
                ),
                system_cpu_peak_percent=(
                    max(sampler.cpu_samples) if sampler.cpu_samples else None
                ),
                process_rss_peak_bytes=(
                    max(sampler.rss_samples) if sampler.rss_samples else None
                ),
                source_sha256_seconds=source_hash_seconds,
                destination_sha256_seconds=destination_hash_seconds,
            )
        except BaseException as error:
            sampler.stop()
            duration = time.perf_counter() - started
            destination_exists = destination.exists()
            destination_hash = (
                sha256_file(destination)[0] if destination_exists else None
            )
            source_hash = sha256_file(source)[0] if source.exists() else None

            if not expected_success:
                preserved = (
                    destination_exists
                    and before_destination_hash is not None
                    and destination_hash == before_destination_hash
                    and destination_hash != source_hash
                )
                result.success = preserved
                result.explanation = (
                    "CREATE conflict was rejected by the real transaction pipeline "
                    "and the existing destination was preserved."
                    if preserved
                    else "CREATE conflict raised an exception but destination "
                    "preservation could not be proven."
                )
                result.observed = {
                    "destination_exists": destination_exists,
                    "source_sha256": source_hash,
                    "destination_sha256": destination_hash,
                    "destination_preserved": preserved,
                    "exception_was_expected": True,
                }
            else:
                result.explanation = "Scenario raised an unexpected exception."

            result.error_type = type(error).__name__
            result.error_message = str(error)
            result.metrics.duration_seconds = duration
            result.metrics.process_cpu_seconds = time.process_time() - cpu_started
            result.metrics.system_cpu_average_percent = (
                sum(sampler.cpu_samples) / len(sampler.cpu_samples)
                if sampler.cpu_samples
                else None
            )
            result.metrics.system_cpu_peak_percent = (
                max(sampler.cpu_samples) if sampler.cpu_samples else None
            )
            result.metrics.process_rss_peak_bytes = (
                max(sampler.rss_samples) if sampler.rss_samples else None
            )
        self.console.stop_heartbeat()
        if record:
            self.report.results.append(result)
            self.console.result(result)
        return result

    def _announce_scenario(self, scenario_id: str, description: str) -> None:
        self._scenario_current += 1
        self.console.scenario(
            self._scenario_current,
            self._scenario_total,
            scenario_id,
            description,
        )

    def _write_reports(self) -> tuple[Path, Path]:
        now = datetime.now(timezone.utc)
        output_dir = self.reports_root / f"{now:%Y}" / f"{now:%m}"
        output_dir.mkdir(parents=True, exist_ok=True)
        base = output_dir / f"qualification-{now:%Y-%m-%dT%H-%M-%SZ}"
        json_path = base.with_suffix(".json")
        markdown_path = base.with_suffix(".md")
        json_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        markdown_path.write_text(render_markdown(self.report), encoding="utf-8")
        return json_path, markdown_path

    def _print_summary(self, json_path: Path, markdown_path: Path) -> None:
        summary = self.report.summary()
        print("\nKnowledge Transport Layer qualification")
        print("=" * 40)
        print(f"Qualification: {self.report.qualification_id}")
        print(f"Scenarios:     {summary['total']}")
        print(f"Succeeded:     {summary['succeeded']}")
        print(f"Failed:        {summary['failed']}")
        print(f"Duration:      {summary['duration_seconds']:.3f} s")
        print(
            "Average rate: "
            f"{summary['average_throughput_mib_per_second']:.2f} MiB/s"
        )
        print(f"JSON report:   {json_path}")
        print(f"Markdown:      {markdown_path}")


def build_transaction(
    source: Path,
    destination: Path,
    delivery_mode: DeliveryMode,
) -> tuple[DefaultTransactionExecutor, Transaction]:
    repository = FilesystemPathRepository(
        {"source": source, "destination": destination}
    )
    resolver = FilesystemPathResolver(repository)
    capability = FilesystemTransportCapability(
        receiver=FilesystemReceiver(resolver),
        writer=FilesystemWriter(resolver),
        verifier=HashDeliveryVerifier(resolver),
    )
    transport_registry = InMemoryTransportRegistry()
    transport_registry.register("filesystem", capability)
    transport_engine = DefaultTransportEngine(transport_registry)
    operation_registry = InMemoryOperationRegistry()
    operation_registry.register(
        TRANSPORT_OPERATION_KIND,
        TransportOperationEngine(transport_engine),
    )
    request = TransportRequest(
        source_resource=ResourceReference("file", "source"),
        destination_resource=ResourceReference("file", "destination"),
        source=TransportEndpoint("source", "filesystem", str(source.parent)),
        destination=TransportEndpoint(
            "destination", "filesystem", str(destination.parent)
        ),
        delivery_mode=delivery_mode,
    )
    transaction = Transaction(
        operations=[
            Operation(
                name=f"Transport {source.name}",
                kind=TRANSPORT_OPERATION_KIND,
                payload=request,
            )
        ]
    )
    return DefaultTransactionExecutor(operation_registry), transaction


def deterministic_bytes(size: int, seed: int = 0) -> bytes:
    pattern = hashlib.sha256(f"AIStack:{seed}".encode()).digest()
    repeats, remainder = divmod(size, len(pattern))
    return pattern * repeats + pattern[:remainder]


def generate_file(
    path: Path,
    size: int,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pattern = deterministic_bytes(CHUNK_SIZE)
    remaining = size
    written = 0
    next_progress = max(size // 20, CHUNK_SIZE)
    with path.open("wb") as stream:
        while remaining:
            chunk = pattern if remaining >= len(pattern) else pattern[:remaining]
            stream.write(chunk)
            remaining -= len(chunk)
            written += len(chunk)
            if progress is not None and (
                written >= next_progress or written == size
            ):
                progress(written, size)
                next_progress += max(size // 20, CHUNK_SIZE)
        stream.flush()
        os.fsync(stream.fileno())


def sha256_file(path: Path) -> tuple[str, float]:
    started = time.perf_counter()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest(), time.perf_counter() - started


def read_process_rss_bytes() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def read_system_cpu_percent(delay: float) -> float | None:
    def snapshot() -> tuple[int, int]:
        fields = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
        return sum(fields), idle

    try:
        total_1, idle_1 = snapshot()
        time.sleep(max(delay, 0.01))
        total_2, idle_2 = snapshot()
        total_delta = total_2 - total_1
        idle_delta = idle_2 - idle_1
        return 0.0 if total_delta <= 0 else 100.0 * (1.0 - idle_delta / total_delta)
    except (OSError, ValueError, IndexError):
        return None


def collect_environment() -> dict[str, Any]:
    disk = shutil.disk_usage(Path.cwd())
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_logical_count": os.cpu_count(),
        "memory_total_bytes": read_mem_total_bytes(),
        "filesystem": filesystem_type(Path.cwd()),
        "disk_total_bytes": disk.total,
        "disk_free_bytes_at_start": disk.free,
    }


def read_mem_total_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def filesystem_type(path: Path) -> str | None:
    try:
        return subprocess.run(
            ["findmnt", "-no", "FSTYPE", "--target", str(path.resolve())],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def human_size(size: int) -> str:
    if size >= GIB:
        return f"{size / GIB:g} GiB"
    if size >= MIB:
        return f"{size / MIB:g} MiB"
    if size >= 1024:
        return f"{size / 1024:g} KiB"
    return f"{size} B"


def render_markdown(report: QualificationReport) -> str:
    summary = report.summary()
    lines = [
        "# Knowledge Transport Layer Qualification Report",
        "",
        f"- Qualification ID: `{report.qualification_id}`",
        f"- Started: `{report.started_at}`",
        f"- Finished: `{report.finished_at}`",
        f"- Runner version: `{report.runner_version}`",
        f"- Git commit: `{report.git_commit or 'unknown'}`",
        "",
        "## Summary",
        "",
        f"- Total scenarios: **{summary['total']}**",
        f"- Succeeded: **{summary['succeeded']}**",
        f"- Failed: **{summary['failed']}**",
        f"- Mandatory failures: **{summary['mandatory_failed']}**",
        f"- Measured duration: **{summary['duration_seconds']:.3f} s**",
        "- Average throughput: "
        f"**{summary['average_throughput_mib_per_second']:.2f} MiB/s**",
        "",
        "## Environment",
        "",
        "```json",
        json.dumps(report.environment, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Scenarios",
        "",
        "| Status | Scenario | Size | Duration | Throughput | Explanation |",
        "|---|---|---:|---:|---:|---|",
    ]
    for result in report.results:
        status = "PASS" if result.success else "FAIL"
        metrics = result.metrics
        lines.append(
            f"| {status} | `{result.scenario_id}` | "
            f"{human_size(metrics.source_size_bytes)} | "
            f"{metrics.duration_seconds:.3f} s | "
            f"{metrics.throughput_mib_per_second:.2f} MiB/s | "
            f"{result.explanation.replace('|', '\\|')} |"
        )
    lines.extend(["", "## Detailed Results", ""])
    for result in report.results:
        lines.extend(
            [
                f"### {result.scenario_id}",
                "",
                "```json",
                json.dumps(asdict(result), indent=2, ensure_ascii=False),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def normalize_scenario_selector(selector: str | None) -> str | None:
    if selector is None:
        return None
    value = selector.strip().lower()
    aliases = {
        **{str(index): f"standard-{index:02d}" for index in range(1, 18)},
        "18": "create-conflict",
        "19": "replace-existing",
        "20": "batch-1000-small-files",
        "21": "large-100-mib",
        "22": "large-500-mib",
        "23": "large-1-gib",
        "24": "large-5-gib",
        "25": "large-20-gib",
        "26": "large-50-gib",
    }
    normalized = aliases.get(value, value)
    valid = set(aliases.values())
    if normalized not in valid:
        choices = ", ".join(sorted(valid))
        raise SystemExit(
            f"Unknown scenario {selector!r}. Valid identifiers: {choices}"
        )
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qualify the AIStack Knowledge Transport Layer end to end."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(
            os.environ.get(
                "AISTACK_QUALIFICATION_WORKSPACE",
                "/media/BACKUP/aistack-qualification",
            )
        ),
        help=(
            "Disposable source workspace. Defaults to "
            "$AISTACK_QUALIFICATION_WORKSPACE or "
            "/media/BACKUP/aistack-qualification."
        ),
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=None,
        help=(
            "Optional destination root, for example a mounted laptop share. "
            "When omitted, destination data stays inside the workspace."
        ),
    )
    parser.add_argument(
        "--scenario",
        help=(
            "Run one scenario only. Accepts an identifier such as "
            "large-50-gib or its campaign number (26)."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show technical details and paths.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the final summary.",
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        default=Path("reports/qualification"),
        help="Root directory of immutable qualification reports.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verbose and args.quiet:
        raise SystemExit("--verbose and --quiet cannot be used together.")
    return QualificationRunner(
        workspace=args.workspace.resolve(),
        reports_root=args.reports_root.resolve(),
        destination_root=(
            args.destination_root.resolve() if args.destination_root else None
        ),
        selected_scenario=args.scenario,
        quiet=args.quiet,
        verbose=args.verbose,
    ).run()


if __name__ == "__main__":
    sys.exit(main())

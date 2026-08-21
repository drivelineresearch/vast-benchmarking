from __future__ import annotations

import json
import time
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .benchmarks import (
    BenchmarkConfig,
    run_cpu_benchmarks,
    run_disk_benchmarks,
    run_gpu_benchmarks,
    run_memory_benchmarks,
)
from .models import BenchmarkResult, Metric
from .storage import save_result
from .system_info import collect_system_info


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def run_benchmark(
    *,
    profile: str = "standard",
    label: str = "",
    disk_dir: str = "/tmp",
    max_seconds: int | None = None,
    db_path: str | None = None,
    output_path: str | None = None,
    vast: dict[str, Any] | None = None,
) -> BenchmarkResult:
    config = BenchmarkConfig.for_profile(profile)
    if max_seconds is not None:
        if max_seconds < 30 or max_seconds > 600:
            raise ValueError("max_seconds must be between 30 and 600")
        config = replace(config, max_seconds=max_seconds)

    started_wall = _utc_now()
    started = time.monotonic()
    deadline = started + config.max_seconds
    metrics: list[Metric] = []
    errors: list[str] = []
    gpu_results: list[dict[str, Any]] = []
    system = collect_system_info(disk_dir)

    def phase(name: str, action: Any, minimum_remaining: float = 15.0) -> Any:
        remaining = deadline - time.monotonic()
        if remaining < minimum_remaining:
            errors.append(f"Skipped {name}: only {remaining:.1f}s remained in wall-clock budget")
            return None
        print(
            json.dumps(
                {"phase": name, "status": "started", "remaining_seconds": round(remaining, 1)}
            ),
            flush=True,
        )
        phase_started = time.monotonic()
        value = action()
        print(
            json.dumps(
                {
                    "phase": name,
                    "status": "finished",
                    "duration_seconds": round(time.monotonic() - phase_started, 2),
                }
            ),
            flush=True,
        )
        return value

    cpu_output = phase("cpu", lambda: run_cpu_benchmarks(config), 30.0)
    if cpu_output:
        phase_metrics, phase_errors = cpu_output
        metrics.extend(phase_metrics)
        errors.extend(phase_errors)

    memory_output = phase("memory", lambda: run_memory_benchmarks(config), 20.0)
    if memory_output:
        phase_metrics, phase_errors = memory_output
        metrics.extend(phase_metrics)
        errors.extend(phase_errors)

    disk_output = phase("disk", lambda: run_disk_benchmarks(config, disk_dir), 20.0)
    if disk_output:
        phase_metrics, phase_errors = disk_output
        metrics.extend(phase_metrics)
        errors.extend(phase_errors)

    gpu_output = phase("gpu", lambda: run_gpu_benchmarks(config), 45.0)
    if gpu_output:
        phase_metrics, gpu_results, phase_errors = gpu_output
        metrics.extend(phase_metrics)
        errors.extend(phase_errors)

    elapsed = time.monotonic() - started
    categories = {metric.category for metric in metrics}
    required = {"cpu", "memory", "disk"}
    if system.get("torch_cuda_available") or system.get("gpus"):
        required.add("gpu")
    status = (
        "complete" if required.issubset(categories) and elapsed <= config.max_seconds else "partial"
    )
    result = BenchmarkResult(
        run_id=str(uuid.uuid4()),
        started_at=started_wall,
        finished_at=_utc_now(),
        duration_seconds=elapsed,
        status=status,
        profile=profile,
        benchmark_version=__version__,
        label=label or system.get("hostname") or "benchmark",
        system=system,
        config=config.to_dict(),
        metrics=metrics,
        gpu_results=gpu_results,
        errors=errors,
        vast=vast or {},
    )
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.to_json() + "\n")
    if db_path:
        save_result(db_path, result)
    return result

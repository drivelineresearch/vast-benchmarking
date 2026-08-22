from __future__ import annotations

from typing import Any

from .models import Metric


def gpu_concurrency_issue(
    system: dict[str, Any], gpu_results: list[dict[str, Any]]
) -> str | None:
    """Return a blocking issue when not every visible GPU reported a concurrent result."""
    gpus = system.get("gpus") or []
    if not gpus:
        return None

    expected_indices = {
        int(gpu.get("index", index)) for index, gpu in enumerate(gpus)
    }
    returned_indices = {
        int(result["device_index"])
        for result in gpu_results
        if result.get("device_index") is not None
    }
    if returned_indices == expected_indices:
        return None
    missing = sorted(expected_indices - returned_indices)
    suffix = f"; missing device indices {missing}" if missing else ""
    return (
        "GPU concurrency incomplete: "
        f"{len(returned_indices)}/{len(expected_indices)} visible devices returned{suffix}"
    )


def benchmark_status(
    *,
    system: dict[str, Any],
    metrics: list[Metric],
    gpu_results: list[dict[str, Any]],
    elapsed_seconds: float,
    max_seconds: float,
) -> tuple[str, list[str]]:
    categories = {metric.category for metric in metrics}
    required = {"cpu", "memory", "disk"}
    if system.get("torch_cuda_available") or system.get("gpus"):
        required.add("gpu")

    issues: list[str] = []
    missing_categories = sorted(required - categories)
    if missing_categories:
        issues.append(f"Missing required benchmark categories: {', '.join(missing_categories)}")
    gpu_issue = gpu_concurrency_issue(system, gpu_results)
    if gpu_issue:
        issues.append(gpu_issue)
    if elapsed_seconds > max_seconds:
        issues.append(
            f"Wall-clock budget exceeded: {elapsed_seconds:.1f}s > {max_seconds:.1f}s"
        )
    return ("complete" if not issues else "partial", issues)

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

LEADERBOARD_METRICS = {
    "gpu_cv": ("gpu.concurrent.cv_images_per_sec_total", "GPU CV throughput"),
    "gpu_compute": ("gpu.concurrent.gemm_heavy_tflops_total", "GPU FP16 compute"),
    "cpu_multi": ("cpu.sha256_multi_gbps", "CPU multicore"),
    "cpu_single": ("cpu.sha256_single_gbps", "CPU single thread"),
    "memory": ("memory.copy_gbps", "Memory copy"),
    "disk": ("disk.sequential_write_gbps", "Disk write"),
}


def metric_map(metrics: Iterable[dict[str, Any]]) -> dict[str, float]:
    return {
        metric["name"]: float(metric["value"])
        for metric in metrics
        if metric.get("value") is not None
    }


def relative_scores(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute a transparent percent-of-best geometric mean across available categories."""
    maxima: dict[str, float] = {}
    for run in runs:
        values = metric_map(run.get("metrics", []))
        for metric_name, _label in LEADERBOARD_METRICS.values():
            value = values.get(metric_name)
            if value is not None and value > 0:
                maxima[metric_name] = max(maxima.get(metric_name, 0.0), value)

    scored: list[dict[str, Any]] = []
    for run in runs:
        values = metric_map(run.get("metrics", []))
        components: list[float] = []
        for metric_name, _label in LEADERBOARD_METRICS.values():
            value = values.get(metric_name)
            maximum = maxima.get(metric_name)
            if value is not None and maximum and value > 0:
                components.append(max(value / maximum, 1e-9))
        available_score = (
            100.0 * math.exp(sum(math.log(item) for item in components) / len(components))
            if components
            else 0.0
        )
        score = available_score * len(components) / len(LEADERBOARD_METRICS)
        enriched = dict(run)
        enriched["relative_score"] = score
        enriched["score_components"] = len(components)
        scored.append(enriched)
    return sorted(scored, key=lambda item: item["relative_score"], reverse=True)


def metric_leaderboard(
    runs: list[dict[str, Any]], metric_name: str, limit: int = 10
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in runs:
        for metric in run.get("metrics", []):
            if metric.get("name") == metric_name:
                rows.append(
                    {
                        "run_id": run["run_id"],
                        "label": run.get("label") or run.get("hostname") or run["run_id"],
                        "value": float(metric["value"]),
                        "unit": metric.get("unit", ""),
                        "machine_id": run.get("machine_id"),
                        "gpu_summary": run.get("gpu_summary", "CPU only"),
                        "cpu_model": run.get("cpu_model", "Unknown CPU"),
                    }
                )
                break
    return sorted(rows, key=lambda item: item["value"], reverse=True)[:limit]

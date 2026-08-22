from vast_benchmarking.models import Metric
from vast_benchmarking.validation import benchmark_status, gpu_concurrency_issue


def test_gpu_concurrency_requires_every_visible_device() -> None:
    system = {"gpus": [{"index": index} for index in range(4)]}
    results = [{"device_index": index} for index in (0, 1, 3)]

    issue = gpu_concurrency_issue(system, results)

    assert issue == (
        "GPU concurrency incomplete: 3/4 visible devices returned; "
        "missing device indices [2]"
    )


def test_benchmark_status_accepts_complete_gpu_concurrency() -> None:
    system = {"gpus": [{"index": 0}, {"index": 1}]}
    metrics = [
        Metric("cpu.test", 1, "unit", "cpu"),
        Metric("memory.test", 1, "unit", "memory"),
        Metric("disk.test", 1, "unit", "disk"),
        Metric("gpu.test", 1, "unit", "gpu"),
    ]

    status, issues = benchmark_status(
        system=system,
        metrics=metrics,
        gpu_results=[{"device_index": 0}, {"device_index": 1}],
        elapsed_seconds=100,
        max_seconds=540,
    )

    assert status == "complete"
    assert issues == []


def test_benchmark_status_marks_partial_gpu_concurrency() -> None:
    system = {"gpus": [{"index": 0}, {"index": 1}]}
    metrics = [
        Metric("cpu.test", 1, "unit", "cpu"),
        Metric("memory.test", 1, "unit", "memory"),
        Metric("disk.test", 1, "unit", "disk"),
        Metric("gpu.test", 1, "unit", "gpu"),
    ]

    status, issues = benchmark_status(
        system=system,
        metrics=metrics,
        gpu_results=[{"device_index": 0}],
        elapsed_seconds=100,
        max_seconds=540,
    )

    assert status == "partial"
    assert "1/2 visible devices" in issues[0]

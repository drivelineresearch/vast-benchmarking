from __future__ import annotations

import pytest

from vast_benchmarking.models import BenchmarkResult, Metric


@pytest.fixture
def sample_result() -> BenchmarkResult:
    return BenchmarkResult(
        run_id="11111111-2222-3333-4444-555555555555",
        started_at="2026-08-21T12:00:00+00:00",
        finished_at="2026-08-21T12:03:00+00:00",
        duration_seconds=180.0,
        status="complete",
        profile="standard",
        benchmark_version="0.1.0",
        label="Sample GPU Host",
        system={
            "hostname": "sample-host",
            "cpu_model": "Sample CPU",
            "cpu_effective": 128,
            "platform": "Linux",
            "python_version": "3.11",
            "torch_version": "2.10.0",
            "torch_cuda_version": "12.8",
            "gpus": [
                {"index": 0, "name": "RTX 5060 Ti", "memory_mib": 16311},
                {"index": 1, "name": "RTX 5060 Ti", "memory_mib": 16311},
            ],
        },
        config={"profile": "standard", "max_seconds": 540},
        metrics=[
            Metric("gpu.concurrent.cv_images_per_sec_total", 2400.0, "images/s", "gpu"),
            Metric("gpu.concurrent.gemm_heavy_tflops_total", 80.0, "TFLOP/s", "gpu"),
            Metric("cpu.sha256_multi_gbps", 40.0, "GB/s", "cpu"),
            Metric("cpu.sha256_single_gbps", 1.5, "GB/s", "cpu"),
            Metric("memory.copy_gbps", 70.0, "GB/s", "memory"),
            Metric("disk.sequential_write_gbps", 2.0, "GB/s", "disk"),
        ],
        gpu_results=[],
        errors=[],
        vast={
            "offer_id": 123,
            "machine_id": 456,
            "instance_id": 789,
            "hourly_rate": 0.5,
            "verification": "verified",
        },
    )

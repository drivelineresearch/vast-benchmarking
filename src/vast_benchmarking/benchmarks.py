from __future__ import annotations

import hashlib
import multiprocessing as mp
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np

from .models import Metric
from .system_info import effective_cpu_capacity, effective_cpu_count

GIB = 1024**3
MIB = 1024**2


@dataclass(slots=True)
class BenchmarkConfig:
    profile: str
    max_seconds: int
    gpu_kernel_seconds: float
    gpu_cv_seconds: float
    gpu_baseline_seconds: float
    cpu_single_seconds: float
    cpu_multi_seconds: float
    cpu_matmul_seconds: float
    memory_mib: int
    disk_mib: int
    cpu_worker_limit: int

    @classmethod
    def for_profile(cls, profile: str) -> BenchmarkConfig:
        if profile == "smoke":
            return cls(
                profile="smoke",
                max_seconds=90,
                gpu_kernel_seconds=1.0,
                gpu_cv_seconds=1.5,
                gpu_baseline_seconds=1.0,
                cpu_single_seconds=1.0,
                cpu_multi_seconds=1.5,
                cpu_matmul_seconds=1.0,
                memory_mib=64,
                disk_mib=64,
                cpu_worker_limit=4,
            )
        if profile != "standard":
            raise ValueError(f"unknown profile: {profile}")
        return cls(
            profile="standard",
            max_seconds=540,
            gpu_kernel_seconds=8.0,
            gpu_cv_seconds=12.0,
            gpu_baseline_seconds=6.0,
            cpu_single_seconds=5.0,
            cpu_multi_seconds=12.0,
            cpu_matmul_seconds=6.0,
            memory_mib=1024,
            disk_mib=1024,
            cpu_worker_limit=0,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _metric(
    name: str,
    value: float,
    unit: str,
    category: str,
    **metadata: Any,
) -> Metric:
    return Metric(
        name=name,
        value=float(value),
        unit=unit,
        category=category,
        metadata=metadata,
    )


def _sha256_worker(args: tuple[float, int]) -> int:
    duration, seed = args
    block = bytes([seed % 251]) * MIB
    processed = 0
    deadline = time.perf_counter() + duration
    digest = hashlib.sha256
    while time.perf_counter() < deadline:
        digest(block).digest()
        processed += len(block)
    return processed


def _timed_cpu_matmul(duration: float, threads: int) -> float:
    try:
        import torch
    except ImportError:
        return 0.0

    previous = torch.get_num_threads()
    torch.set_num_threads(max(1, threads))
    size = 1024
    left = torch.randn((size, size), dtype=torch.float32)
    right = torch.randn((size, size), dtype=torch.float32)
    torch.matmul(left, right)
    started = time.perf_counter()
    iterations = 0
    try:
        while time.perf_counter() - started < duration:
            torch.matmul(left, right)
            iterations += 1
    finally:
        torch.set_num_threads(previous)
    elapsed = max(time.perf_counter() - started, 1e-9)
    return 2.0 * (size**3) * iterations / elapsed / 1e9


def run_cpu_benchmarks(config: BenchmarkConfig) -> tuple[list[Metric], list[str]]:
    metrics: list[Metric] = []
    errors: list[str] = []
    effective = effective_cpu_count()
    workers = effective if config.cpu_worker_limit <= 0 else min(effective, config.cpu_worker_limit)
    metrics.append(
        _metric("cpu.effective_cores", effective_cpu_capacity(), "cores", "cpu")
    )

    try:
        started = time.perf_counter()
        single_bytes = _sha256_worker((config.cpu_single_seconds, 0))
        elapsed = max(time.perf_counter() - started, 1e-9)
        metrics.append(
            _metric("cpu.sha256_single_gbps", single_bytes / elapsed / 1e9, "GB/s", "cpu")
        )
    except Exception as exc:  # pragma: no cover - hardware dependent
        errors.append(f"CPU single-thread SHA-256 failed: {exc}")

    try:
        ctx = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context()
        started = time.perf_counter()
        with ctx.Pool(processes=workers, maxtasksperchild=1) as pool:
            processed = pool.map(
                _sha256_worker,
                [(config.cpu_multi_seconds, worker) for worker in range(workers)],
            )
        elapsed = max(time.perf_counter() - started, 1e-9)
        metrics.append(
            _metric(
                "cpu.sha256_multi_gbps",
                sum(processed) / elapsed / 1e9,
                "GB/s",
                "cpu",
                workers=workers,
            )
        )
    except Exception as exc:  # pragma: no cover - hardware dependent
        errors.append(f"CPU multicore SHA-256 failed: {exc}")

    try:
        single_gflops = _timed_cpu_matmul(config.cpu_matmul_seconds, 1)
        if single_gflops:
            metrics.append(
                _metric("cpu.torch_matmul_single_gflops", single_gflops, "GFLOP/s", "cpu")
            )
        multi_gflops = _timed_cpu_matmul(config.cpu_matmul_seconds, effective)
        if multi_gflops:
            metrics.append(
                _metric(
                    "cpu.torch_matmul_multi_gflops",
                    multi_gflops,
                    "GFLOP/s",
                    "cpu",
                    threads=effective,
                )
            )
    except Exception as exc:  # pragma: no cover - hardware dependent
        errors.append(f"CPU Torch matmul failed: {exc}")
    return metrics, errors


def _available_memory_bytes() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return 2 * GIB


def _best_rate(action: Any, bytes_moved: int, repeats: int = 3) -> float:
    rates: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        action()
        elapsed = max(time.perf_counter() - started, 1e-9)
        rates.append(bytes_moved / elapsed / 1e9)
    return max(rates)


def run_memory_benchmarks(config: BenchmarkConfig) -> tuple[list[Metric], list[str]]:
    errors: list[str] = []
    requested = config.memory_mib * MIB
    total_bytes = int(min(requested, max(64 * MIB, _available_memory_bytes() * 0.10)))
    elements = max(1, total_bytes // 2 // np.dtype(np.float64).itemsize)
    try:
        source = np.ones(elements, dtype=np.float64)
        target = np.empty_like(source)
        copy_rate = _best_rate(lambda: np.copyto(target, source), source.nbytes * 2)
        fill_rate = _best_rate(lambda: target.fill(3.14159), target.nbytes)
        scale_rate = _best_rate(
            lambda: np.multiply(source, 1.000001, out=target),
            source.nbytes * 2,
        )
        return (
            [
                _metric(
                    "memory.copy_gbps",
                    copy_rate,
                    "GB/s",
                    "memory",
                    allocation_bytes=source.nbytes + target.nbytes,
                ),
                _metric("memory.fill_gbps", fill_rate, "GB/s", "memory"),
                _metric("memory.scale_gbps", scale_rate, "GB/s", "memory"),
            ],
            errors,
        )
    except Exception as exc:  # pragma: no cover - hardware dependent
        errors.append(f"Memory benchmark failed: {exc}")
        return [], errors


def run_disk_benchmarks(config: BenchmarkConfig, disk_dir: str) -> tuple[list[Metric], list[str]]:
    errors: list[str] = []
    target_bytes = config.disk_mib * MIB
    chunk = bytes(8 * MIB)
    path: Path | None = None
    try:
        Path(disk_dir).mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(prefix="vast-benchmark-", dir=disk_dir)
        path = Path(raw_path)
        started = time.perf_counter()
        written = 0
        with os.fdopen(descriptor, "wb", buffering=0) as handle:
            while written < target_bytes:
                amount = min(len(chunk), target_bytes - written)
                handle.write(chunk[:amount])
                written += amount
            os.fsync(handle.fileno())
        write_elapsed = max(time.perf_counter() - started, 1e-9)

        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            read_descriptor = os.open(path, os.O_RDONLY)
            try:
                os.posix_fadvise(read_descriptor, 0, 0, os.POSIX_FADV_DONTNEED)
            finally:
                os.close(read_descriptor)

        started = time.perf_counter()
        read_bytes = 0
        read_buffer = bytearray(len(chunk))
        with path.open("rb", buffering=0) as handle:
            while True:
                count = handle.readinto(read_buffer)
                if not count:
                    break
                read_bytes += count
        read_elapsed = max(time.perf_counter() - started, 1e-9)
        return (
            [
                _metric(
                    "disk.sequential_write_gbps",
                    written / write_elapsed / 1e9,
                    "GB/s",
                    "disk",
                    bytes=written,
                    fsync=True,
                ),
                _metric(
                    "disk.sequential_read_gbps",
                    read_bytes / read_elapsed / 1e9,
                    "GB/s",
                    "disk",
                    bytes=read_bytes,
                    cache_advice="POSIX_FADV_DONTNEED",
                ),
            ],
            errors,
        )
    except Exception as exc:  # pragma: no cover - hardware dependent
        errors.append(f"Disk benchmark failed: {exc}")
        return [], errors
    finally:
        if path is not None and path.exists():
            path.unlink()


class NvidiaMonitor:
    def __init__(self) -> None:
        self.samples: list[list[dict[str, float]]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not shutil.which("nvidia-smi"):
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, float]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        flattened = [sample for batch in self.samples for sample in batch]
        if not flattened:
            return {}
        return {
            "gpu.utilization_avg_pct": sum(item["util"] for item in flattened) / len(flattened),
            "gpu.power_avg_watts": sum(item["power"] for item in flattened) / len(flattened),
            "gpu.temperature_max_c": max(item["temp"] for item in flattened),
            "gpu.memory_used_max_mib": max(item["memory"] for item in flattened),
        }

    def _run(self) -> None:
        query_fields = "utilization.gpu,power.draw,temperature.gpu,memory.used"
        while not self._stop.wait(1.0):
            try:
                completed = subprocess.run(
                    [
                        "nvidia-smi",
                        f"--query-gpu={query_fields}",
                        "--format=csv,noheader,nounits",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                batch: list[dict[str, float]] = []
                for line in completed.stdout.splitlines():
                    values = [float(value.strip()) for value in line.split(",")]
                    if len(values) == 4:
                        batch.append(
                            {
                                "util": values[0],
                                "power": values[1],
                                "temp": values[2],
                                "memory": values[3],
                            }
                        )
                if batch:
                    self.samples.append(batch)
            except (OSError, ValueError, subprocess.SubprocessError):
                continue


def _cuda_elapsed(action: Any, duration: float) -> tuple[int, float]:
    import torch

    torch.cuda.synchronize()
    started = time.perf_counter()
    iterations = 0
    while time.perf_counter() - started < duration:
        action()
        iterations += 1
    torch.cuda.synchronize()
    return iterations, max(time.perf_counter() - started, 1e-9)


def _gpu_worker(
    device_index: int,
    kernel_seconds: float,
    cv_seconds: float,
    baseline_only: bool,
    result_queue: Any,
) -> None:
    try:
        import torch
        from torch import nn

        torch.cuda.set_device(device_index)
        torch.backends.cudnn.benchmark = True
        properties = torch.cuda.get_device_properties(device_index)
        cuda_device = torch.device(f"cuda:{device_index}")
        total_memory = int(properties.total_memory)
        profiles = {"heavy": 6144 if total_memory < 10 * GIB else 8192}
        if not baseline_only:
            profiles = {"light": 2048, "medium": 4096, **profiles}

        result: dict[str, Any] = {
            "device_index": device_index,
            "name": properties.name,
            "total_memory_bytes": total_memory,
            "compute_capability": f"{properties.major}.{properties.minor}",
            "gemm_tflops": {},
        }
        dtype = torch.float16
        for profile_name, size in profiles.items():
            left = torch.randn((size, size), device=cuda_device, dtype=dtype)
            right = torch.randn((size, size), device=cuda_device, dtype=dtype)
            output = torch.empty((size, size), device=cuda_device, dtype=dtype)
            for _ in range(2):
                torch.mm(left, right, out=output)
            gemm_action = partial(torch.mm, left, right, out=output)
            iterations, elapsed = _cuda_elapsed(gemm_action, kernel_seconds)
            result["gemm_tflops"][profile_name] = 2.0 * (size**3) * iterations / elapsed / 1e12
            del left, right, output
            torch.cuda.empty_cache()

        batch_size = 32 if total_memory < 10 * GIB else 64
        model = (
            nn.Sequential(
                nn.Conv2d(3, 64, 7, stride=2, padding=3, bias=False),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 128, 3, stride=2, padding=1, bias=False),
                nn.ReLU(inplace=True),
                nn.Conv2d(128, 256, 3, stride=2, padding=1, bias=False),
                nn.ReLU(inplace=True),
                nn.Conv2d(256, 256, 3, padding=1, bias=False),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d((1, 1)),
            )
            .to(cuda_device, dtype=dtype)
            .eval()
        )
        images = torch.randn((batch_size, 3, 224, 224), device=cuda_device, dtype=dtype)
        with torch.inference_mode():
            for _ in range(3):
                model(images)
            cv_action = partial(model, images)
            iterations, elapsed = _cuda_elapsed(cv_action, cv_seconds)
        result["cv_images_per_sec"] = batch_size * iterations / elapsed
        del model, images
        torch.cuda.empty_cache()

        if not baseline_only:
            free_memory, _total = torch.cuda.mem_get_info(device_index)
            transfer_bytes = int(min(256 * MIB, free_memory * 0.10))
            elements = max(1, transfer_bytes // 4)
            source = torch.empty(elements, device=cuda_device, dtype=torch.float32)
            target = torch.empty_like(source)
            iterations, elapsed = _cuda_elapsed(lambda: target.copy_(source), 3.0)
            result["device_copy_gbps"] = source.nbytes * iterations / elapsed / 1e9

            host_elements = max(1, min(64 * MIB, transfer_bytes) // 4)
            host = torch.empty(host_elements, dtype=torch.float32, pin_memory=True)
            device = torch.empty(host_elements, device=cuda_device, dtype=torch.float32)
            iterations, elapsed = _cuda_elapsed(lambda: device.copy_(host, non_blocking=True), 2.0)
            result["host_to_device_gbps"] = host.nbytes * iterations / elapsed / 1e9
            iterations, elapsed = _cuda_elapsed(lambda: host.copy_(device, non_blocking=True), 2.0)
            result["device_to_host_gbps"] = host.nbytes * iterations / elapsed / 1e9
            result["peak_allocated_bytes"] = int(torch.cuda.max_memory_allocated(device_index))
        result_queue.put({"ok": True, "result": result})
    except Exception as exc:  # pragma: no cover - hardware dependent
        result_queue.put(
            {
                "ok": False,
                "device_index": device_index,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )


def _run_gpu_processes(
    device_indices: list[int],
    kernel_seconds: float,
    cv_seconds: float,
    baseline_only: bool,
    timeout: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()
    processes = [
        ctx.Process(
            target=_gpu_worker,
            args=(index, kernel_seconds, cv_seconds, baseline_only, result_queue),
        )
        for index in device_indices
    ]
    for process in processes:
        process.start()

    deadline = time.monotonic() + timeout
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    failed_indices: set[int] = set()
    while len(results) + len(errors) < len(processes) and time.monotonic() < deadline:
        try:
            item = result_queue.get(timeout=min(1.0, max(0.1, deadline - time.monotonic())))
        except queue.Empty:
            if not any(process.is_alive() for process in processes):
                break
            continue
        if item.get("ok"):
            results.append(item["result"])
        else:
            failed_index = int(item.get("device_index", -1))
            failed_indices.add(failed_index)
            errors.append(f"GPU {failed_index}: {item.get('error')}")

    successful_indices = {int(result["device_index"]) for result in results}
    for device_index, process in zip(device_indices, processes, strict=True):
        remaining = max(0.0, deadline - time.monotonic())
        process.join(timeout=min(remaining, 5.0))
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if device_index not in successful_indices:
                errors.append(f"GPU worker PID {process.pid} exceeded its timeout")
        elif (
            process.exitcode not in (0, None)
            and device_index not in successful_indices
            and device_index not in failed_indices
        ):
            errors.append(f"GPU worker PID {process.pid} exited with code {process.exitcode}")
    return sorted(results, key=lambda item: item["device_index"]), errors


def run_gpu_benchmarks(
    config: BenchmarkConfig,
) -> tuple[list[Metric], list[dict[str, Any]], list[str]]:
    try:
        import torch
    except ImportError:
        return [], [], ["PyTorch is not installed; GPU benchmark skipped"]
    if not torch.cuda.is_available():
        return [], [], ["CUDA is not available; GPU benchmark skipped"]

    count = torch.cuda.device_count()
    if count < 1:
        return [], [], ["No CUDA devices are visible; GPU benchmark skipped"]

    baseline, baseline_errors = _run_gpu_processes(
        [0],
        config.gpu_baseline_seconds,
        config.gpu_baseline_seconds,
        True,
        timeout=max(45.0, config.gpu_baseline_seconds * 6),
    )
    monitor = NvidiaMonitor()
    monitor.start()
    concurrent, concurrent_errors = _run_gpu_processes(
        list(range(count)),
        config.gpu_kernel_seconds,
        config.gpu_cv_seconds,
        False,
        timeout=max(90.0, config.gpu_kernel_seconds * 12 + config.gpu_cv_seconds * 4),
    )
    monitor_values = monitor.stop()

    metrics: list[Metric] = [_metric("gpu.count", count, "GPUs", "gpu")]
    for profile in ("light", "medium", "heavy"):
        values = [item.get("gemm_tflops", {}).get(profile) for item in concurrent]
        valid = [float(value) for value in values if value is not None]
        if valid:
            metrics.append(
                _metric(
                    f"gpu.concurrent.gemm_{profile}_tflops_total",
                    sum(valid),
                    "TFLOP/s",
                    "gpu",
                    devices=len(valid),
                    dtype="float16",
                )
            )
    cv_values = [
        float(item["cv_images_per_sec"]) for item in concurrent if "cv_images_per_sec" in item
    ]
    if cv_values:
        metrics.append(
            _metric(
                "gpu.concurrent.cv_images_per_sec_total",
                sum(cv_values),
                "images/s",
                "gpu",
                devices=len(cv_values),
                input_shape="3x224x224",
                dtype="float16",
            )
        )
    if baseline:
        baseline_heavy = baseline[0].get("gemm_tflops", {}).get("heavy")
        baseline_cv = baseline[0].get("cv_images_per_sec")
        if baseline_heavy:
            metrics.append(
                _metric("gpu.single.gemm_heavy_tflops", baseline_heavy, "TFLOP/s", "gpu")
            )
            concurrent_heavy = next(
                (
                    metric.value
                    for metric in metrics
                    if metric.name == "gpu.concurrent.gemm_heavy_tflops_total"
                ),
                None,
            )
            if concurrent_heavy:
                efficiency = concurrent_heavy / (float(baseline_heavy) * count) * 100.0
                metrics.append(
                    _metric(
                        "gpu.concurrent.gemm_scaling_efficiency_pct",
                        efficiency,
                        "%",
                        "gpu",
                    )
                )
        if baseline_cv:
            metrics.append(_metric("gpu.single.cv_images_per_sec", baseline_cv, "images/s", "gpu"))
            if cv_values:
                metrics.append(
                    _metric(
                        "gpu.concurrent.cv_scaling_efficiency_pct",
                        sum(cv_values) / (float(baseline_cv) * count) * 100.0,
                        "%",
                        "gpu",
                    )
                )

    for metric_name, source_key, unit in (
        ("gpu.device_copy_gbps_total", "device_copy_gbps", "GB/s"),
        ("gpu.host_to_device_gbps_total", "host_to_device_gbps", "GB/s"),
        ("gpu.device_to_host_gbps_total", "device_to_host_gbps", "GB/s"),
    ):
        values = [float(item[source_key]) for item in concurrent if source_key in item]
        if values:
            metrics.append(_metric(metric_name, sum(values), unit, "gpu", devices=len(values)))

    for name, value in monitor_values.items():
        unit = (
            "%"
            if name.endswith("pct")
            else "W"
            if "watts" in name
            else "C"
            if "temperature" in name
            else "MiB"
        )
        metrics.append(_metric(name, value, unit, "gpu"))
    return metrics, concurrent, baseline_errors + concurrent_errors

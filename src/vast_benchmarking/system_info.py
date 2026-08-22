from __future__ import annotations

import math
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError):
        pass
    return values


def cpu_affinity_count() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def _parse_cpu_max(raw: str) -> float | None:
    parts = raw.split()
    if len(parts) != 2 or parts[0] == "max":
        return None
    try:
        quota, period = (float(part) for part in parts)
    except ValueError:
        return None
    return quota / period if quota > 0 and period > 0 else None


def cpu_quota_cores() -> float | None:
    try:
        quota = _parse_cpu_max(Path("/sys/fs/cgroup/cpu.max").read_text())
        if quota is not None:
            return quota
    except OSError:
        pass
    try:
        quota = float(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        period = float(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if quota > 0 and period > 0:
            return quota / period
    except (OSError, ValueError):
        pass
    return None


def effective_cpu_capacity() -> float:
    affinity = float(cpu_affinity_count())
    quota = cpu_quota_cores()
    return min(affinity, quota) if quota is not None else affinity


def effective_cpu_count() -> int:
    return max(1, math.ceil(effective_cpu_capacity()))


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown CPU"


def _nvidia_summary() -> list[dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return []
    fields = "index,name,uuid,memory.total,driver_version,pci.bus_id"
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={fields}",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    devices: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 6:
            continue
        devices.append(
            {
                "index": int(parts[0]),
                "name": parts[1],
                "uuid": parts[2],
                "memory_mib": int(parts[3]),
                "driver_version": parts[4],
                "pci_bus_id": parts[5],
            }
        )
    return devices


def collect_system_info(disk_dir: str) -> dict[str, Any]:
    meminfo = _read_meminfo()
    disk = os.statvfs(disk_dir)
    info: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "python_version": platform.python_version(),
        "cpu_model": cpu_model(),
        "cpu_logical_visible": os.cpu_count() or 1,
        "cpu_affinity_count": cpu_affinity_count(),
        "cpu_quota_cores": cpu_quota_cores(),
        "cpu_effective": effective_cpu_capacity(),
        "memory_total_bytes": meminfo.get("MemTotal"),
        "memory_available_bytes": meminfo.get("MemAvailable"),
        "disk_path": str(Path(disk_dir).resolve()),
        "disk_total_bytes": disk.f_blocks * disk.f_frsize,
        "disk_free_bytes": disk.f_bavail * disk.f_frsize,
        "gpus": _nvidia_summary(),
    }
    try:
        import numpy

        info["numpy_version"] = numpy.__version__
    except ImportError:
        info["numpy_version"] = None
    try:
        import torch

        info.update(
            {
                "torch_version": torch.__version__,
                "torch_cuda_version": torch.version.cuda,
                "torch_cuda_available": torch.cuda.is_available(),
            }
        )
    except ImportError:
        info.update(
            {
                "torch_version": None,
                "torch_cuda_version": None,
                "torch_cuda_available": False,
            }
        )
    return info

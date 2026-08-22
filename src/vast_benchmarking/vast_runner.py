from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .storage import ingest_json, record_rental_event, rental_summary
from .vast_api import VastAPIError, VastClient, read_api_key

DEFAULT_IMAGE = "vastai/pytorch:2.10.0-cu128-cuda-12.9-mini-py311-2026-08-21"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _credit(account: dict[str, Any]) -> float | None:
    value = account.get("credit")
    return float(value) if value is not None else None


def _bounded_timeout(deadline: float, requested_seconds: int) -> int:
    remaining = int(deadline - time.monotonic())
    if remaining <= 0:
        raise RuntimeError("instance reached its maximum rental duration")
    return max(1, min(requested_seconds, remaining))


def _ssh_base(host: str, port: int, key: str, known_hosts: str) -> list[str]:
    return [
        "ssh",
        "-i",
        key,
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        "ConnectTimeout=8",
        f"root@{host}",
    ]


def _ssh_endpoints(instance: dict[str, Any]) -> list[tuple[str, int, str]]:
    endpoints: list[tuple[str, int, str]] = []
    public_ip = instance.get("public_ipaddr")
    ports = instance.get("ports")
    if public_ip and isinstance(ports, dict):
        mappings = ports.get("22/tcp", [])
        if isinstance(mappings, list):
            for mapping in mappings:
                if not isinstance(mapping, dict) or not mapping.get("HostPort"):
                    continue
                endpoint = (str(public_ip), int(mapping["HostPort"]), "direct")
                if endpoint not in endpoints:
                    endpoints.append(endpoint)
    if instance.get("ssh_host") and instance.get("ssh_port"):
        endpoint = (str(instance["ssh_host"]), int(instance["ssh_port"]), "proxy")
        if endpoint not in endpoints:
            endpoints.append(endpoint)
    return endpoints


def _wait_for_running(client: VastClient, instance_id: int, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() < deadline:
        instance = client.instance(instance_id)
        last_status = str(instance.get("actual_status") or "unknown")
        print(json.dumps({"instance_id": instance_id, "status": last_status}), flush=True)
        if last_status == "running" and instance.get("ssh_host") and instance.get("ssh_port"):
            return instance
        if last_status in {"exited", "offline", "destroyed"}:
            raise VastAPIError(f"instance {instance_id} entered terminal status {last_status}")
        # Parallel batches otherwise synchronize their API polls and can exceed
        # Vast's per-client request threshold.
        time.sleep(12 + instance_id % 6)
    raise VastAPIError(
        f"instance {instance_id} did not become SSH-ready, last status {last_status}"
    )


def _wait_for_ssh(
    instance: dict[str, Any],
    key: str,
    known_hosts: str,
    timeout_seconds: int,
) -> tuple[str, int, list[str], str]:
    endpoints = _ssh_endpoints(instance)
    if not endpoints:
        raise RuntimeError("instance did not advertise an SSH endpoint")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for host, port, route in endpoints:
            ssh = _ssh_base(host, port, key, known_hosts)
            try:
                probe = (
                    "if [ -x /venv/main/bin/python ]; then p=/venv/main/bin/python; "
                    "elif command -v python >/dev/null; then p=\"$(command -v python)\"; "
                    "else p=\"$(command -v python3)\"; fi; "
                    "\"$p\" --version && \"$p\" -c 'import torch; "
                    "assert torch.cuda.is_available()' && nvidia-smi -L && "
                    "printf '__PYTHON__=%s\\n' \"$p\""
                )
                completed = subprocess.run(
                    [*ssh, probe],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            except subprocess.TimeoutExpired:
                continue
            if completed.returncode == 0:
                marker = next(
                    (
                        line.split("=", 1)[1]
                        for line in completed.stdout.splitlines()
                        if line.startswith("__PYTHON__=")
                    ),
                    "",
                )
                if not marker.startswith("/"):
                    continue
                print(
                    json.dumps(
                        {
                            "ssh_route": route,
                            "ssh_host": host,
                            "ssh_port": port,
                            "python": marker,
                        }
                    ),
                    flush=True,
                )
                print(
                    "\n".join(
                        line
                        for line in completed.stdout.splitlines()
                        if not line.startswith("__PYTHON__=")
                    ),
                    flush=True,
                )
                return host, port, ssh, marker
        time.sleep(10)
    raise RuntimeError("SSH did not become ready before timeout")


def _project_archive(project_dir: Path) -> Path:
    descriptor, raw_path = tempfile.mkstemp(prefix="vast-benchmarking-", suffix=".tar.gz")
    os.close(descriptor)
    archive_path = Path(raw_path)
    excluded = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "results"}
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in project_dir.rglob("*"):
            relative = path.relative_to(project_dir)
            if any(part in excluded for part in relative.parts):
                continue
            archive.add(path, arcname=relative, recursive=False)
    return archive_path


def _upload_project(ssh: list[str], project_dir: Path) -> None:
    archive = _project_archive(project_dir)
    try:
        with archive.open("rb") as archive_handle:
            remote = subprocess.run(
                [
                    *ssh,
                    "mkdir -p /workspace/vast-benchmarking "
                    "&& tar -xzf - -C /workspace/vast-benchmarking",
                ],
                stdin=archive_handle,
                check=False,
            )
        if remote.returncode != 0:
            raise RuntimeError(f"project upload failed with exit code {remote.returncode}")
    finally:
        archive.unlink(missing_ok=True)


def _download_result(
    host: str,
    port: int,
    key: str,
    known_hosts: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "scp",
        "-i",
        key,
        "-P",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        f"root@{host}:/workspace/vast-result.json",
        str(destination),
    ]
    subprocess.run(command, check=True, timeout=120)


def run_offer(args: argparse.Namespace) -> int:
    api_key = read_api_key(args.env_file)
    client = VastClient(api_key)
    db_path = str(Path(args.db).resolve())
    project_dir = Path(args.project_dir).resolve()
    results_dir = Path(args.results_dir).resolve()
    ssh_key = str(Path(args.ssh_key).resolve())
    if not project_dir.joinpath("pyproject.toml").is_file():
        raise RuntimeError(f"project directory is invalid: {project_dir}")
    if not Path(ssh_key).is_file():
        raise RuntimeError(f"SSH key does not exist: {ssh_key}")
    public_key_path = Path(f"{ssh_key}.pub")
    if not public_key_path.is_file():
        raise RuntimeError(f"SSH public key does not exist: {public_key_path}")

    active_instances = client.instances()
    if active_instances and not args.allow_existing_instances:
        ids = [instance.get("id") for instance in active_instances]
        raise RuntimeError(f"refusing to create another instance while these exist: {ids}")

    offer = client.offer(args.offer_id)
    if not offer.get("rentable", False) or offer.get("rented", False):
        raise RuntimeError(f"offer {args.offer_id} is not currently rentable")
    hourly_rate = float(offer.get("dph_total_adj") or offer.get("dph_total") or 0)
    if hourly_rate <= 0 or hourly_rate > args.max_hourly:
        raise RuntimeError(
            f"offer rate ${hourly_rate:.4f}/hr violates max hourly ${args.max_hourly:.4f}/hr"
        )
    cuda_max = float(offer.get("cuda_max_good") or 0)
    if cuda_max < args.min_cuda:
        raise RuntimeError(
            f"offer CUDA ceiling {cuda_max:.1f} is below required runtime {args.min_cuda:.1f}"
        )
    spent = float(rental_summary(db_path).get("estimated_cost") or 0.0)
    projected = hourly_rate * args.max_instance_minutes / 60.0
    if spent + projected > args.budget:
        raise RuntimeError(
            f"budget preflight failed: ${spent:.4f} spent + ${projected:.4f} projected "
            f"> ${args.budget:.2f} cap"
        )

    start_account = client.account()
    label = f"vast-benchmark-{args.category}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    preflight = {
        "category": args.category,
        "label": args.label,
        "offer_id": args.offer_id,
        "machine_id": offer.get("machine_id"),
        "gpu_name": offer.get("gpu_name"),
        "num_gpus": offer.get("num_gpus"),
        "cpu_cores_effective": offer.get("cpu_cores_effective"),
        "hourly_rate": hourly_rate,
        "projected_max_cost": projected,
        "budget_spent_before": spent,
        "budget_cap": args.budget,
    }
    print(json.dumps({"preflight": preflight}, sort_keys=True), flush=True)

    instance_id: int | None = None
    instance_started = time.monotonic()
    instance_deadline = instance_started + args.max_instance_minutes * 60
    result_path: Path | None = None
    benchmark_returncode = 1
    try:
        instance_id = client.create_instance(
            args.offer_id,
            image=args.image,
            disk_gb=args.disk_gb,
            label=label,
        )
        record_rental_event(
            db_path,
            recorded_at=_utc_now(),
            action="created",
            instance_id=instance_id,
            offer_id=args.offer_id,
            hourly_rate=hourly_rate,
            account_credit=_credit(start_account),
            estimated_cost=0.0,
            details=preflight,
        )
        client.attach_ssh_key(instance_id, public_key_path.read_text())
        print(json.dumps({"created_instance": instance_id}), flush=True)
        instance = _wait_for_running(
            client,
            instance_id,
            _bounded_timeout(instance_deadline, args.startup_timeout_seconds),
        )
        known_hosts = str(results_dir / f"known_hosts_{instance_id}")
        host, port, ssh, python_bin = _wait_for_ssh(
            instance,
            ssh_key,
            known_hosts,
            _bounded_timeout(instance_deadline, args.ssh_timeout_seconds),
        )
        _upload_project(ssh, project_dir)

        vast_meta = {
            "category": args.category,
            "offer_id": args.offer_id,
            "machine_id": offer.get("machine_id"),
            "instance_id": instance_id,
            "hourly_rate": hourly_rate,
            "verification": offer.get("verification"),
            "reliability": offer.get("reliability"),
            "geolocation": offer.get("geolocation"),
            "listed_gpu_name": offer.get("gpu_name"),
            "listed_num_gpus": offer.get("num_gpus"),
            "listed_gpu_ram_mib": offer.get("gpu_ram"),
            "listed_cpu_name": offer.get("cpu_name"),
            "listed_cpu_effective": offer.get("cpu_cores_effective"),
        }
        remote_command = shlex.join(
            [
                "env",
                "PYTHONPATH=/workspace/vast-benchmarking/src",
                python_bin,
                "-m",
                "vast_benchmarking",
                "run",
                "--profile",
                args.profile,
                "--max-seconds",
                str(args.benchmark_max_seconds),
                "--label",
                args.label,
                "--disk-dir",
                "/workspace",
                "--output",
                "/workspace/vast-result.json",
                "--vast-meta",
                json.dumps(vast_meta, separators=(",", ":")),
            ]
        )
        completed = subprocess.run(
            [*ssh, remote_command],
            check=False,
            timeout=_bounded_timeout(instance_deadline, args.benchmark_max_seconds + 180),
        )
        benchmark_returncode = completed.returncode
        result_path = results_dir / f"{args.category}-{instance_id}.json"
        _download_result(host, port, ssh_key, known_hosts, result_path)
        result = ingest_json(db_path, result_path)
        print(
            json.dumps(
                {
                    "ingested_run": result.run_id,
                    "status": result.status,
                    "duration_seconds": result.duration_seconds,
                    "result_path": str(result_path),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    finally:
        if instance_id is not None:
            elapsed_hours = max(0.0, time.monotonic() - instance_started) / 3600.0
            estimated_cost = hourly_rate * elapsed_hours
            client.destroy_instance(instance_id)
            time.sleep(3)
            remaining_ids = {int(item["id"]) for item in client.instances() if item.get("id")}
            if instance_id in remaining_ids:
                raise RuntimeError(f"instance {instance_id} still exists after destroy request")
            end_account = client.account()
            record_rental_event(
                db_path,
                recorded_at=_utc_now(),
                action="destroyed",
                instance_id=instance_id,
                offer_id=args.offer_id,
                hourly_rate=hourly_rate,
                account_credit=_credit(end_account),
                estimated_cost=estimated_cost,
                details={
                    "elapsed_hours": elapsed_hours,
                    "credit_before": _credit(start_account),
                    "credit_after": _credit(end_account),
                    "benchmark_returncode": benchmark_returncode,
                    "result_path": str(result_path) if result_path else None,
                },
            )
            print(
                json.dumps(
                    {
                        "destroyed_instance": instance_id,
                        "estimated_cost": estimated_cost,
                        "credit_before": _credit(start_account),
                        "credit_after": _credit(end_account),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    # Exit non-zero for partial benchmarks after ingesting their diagnostics so
    # batch orchestration can replace them instead of counting them as accepted.
    return 0 if benchmark_returncode == 0 and result_path else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vast-benchmark-runner")
    parser.add_argument("--env-file", default="/etc/vastai.env")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run-offer")
    run_parser.add_argument("--offer-id", type=int, required=True)
    run_parser.add_argument("--category", required=True)
    run_parser.add_argument("--label", required=True)
    run_parser.add_argument("--db", default="results/benchmarks.sqlite")
    run_parser.add_argument("--results-dir", default="results")
    run_parser.add_argument("--project-dir", default=".")
    run_parser.add_argument("--ssh-key", default="/home/kyle/.ssh/vast_benchmark_ed25519")
    run_parser.add_argument("--image", default=DEFAULT_IMAGE)
    run_parser.add_argument("--disk-gb", type=int, default=32)
    run_parser.add_argument("--profile", choices=("smoke", "standard"), default="standard")
    run_parser.add_argument("--benchmark-max-seconds", type=int, default=540)
    run_parser.add_argument("--startup-timeout-seconds", type=int, default=900)
    run_parser.add_argument("--ssh-timeout-seconds", type=int, default=300)
    run_parser.add_argument("--max-instance-minutes", type=float, default=30.0)
    run_parser.add_argument("--max-hourly", type=float, default=1.2)
    run_parser.add_argument("--min-cuda", type=float, default=12.9)
    run_parser.add_argument("--budget", type=float, default=5.0)
    run_parser.add_argument(
        "--allow-existing-instances",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run-offer":
            return run_offer(args)
    except (VastAPIError, RuntimeError, subprocess.SubprocessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

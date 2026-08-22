from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .storage import rental_summary
from .vast_api import VastClient, read_api_key
from .vast_runner import DEFAULT_IMAGE


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text())
    entries = payload.get("runs") if isinstance(payload, dict) else payload
    if not isinstance(entries, list) or not entries:
        raise ValueError("batch manifest must contain a non-empty runs list")
    required = {"offer_id", "category", "label"}
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict) or not required.issubset(raw):
            raise ValueError(f"manifest run {index} must contain offer_id, category, and label")
        normalized.append(
            {
                "offer_id": int(raw["offer_id"]),
                "category": str(raw["category"]),
                "label": str(raw["label"]),
            }
        )
    offer_ids = [entry["offer_id"] for entry in normalized]
    if len(offer_ids) != len(set(offer_ids)):
        raise ValueError("batch manifest contains duplicate offer IDs")
    return normalized


def offer_rate(offer: dict[str, Any]) -> float:
    return float(offer.get("dph_total_adj") or offer.get("dph_total") or 0)


def preflight_batch(
    client: VastClient,
    entries: list[dict[str, Any]],
    *,
    spent: float,
    budget: float,
    max_hourly: float,
    min_cuda: float,
    max_instance_minutes: float,
) -> dict[str, Any]:
    active = client.instances()
    if active:
        raise RuntimeError(
            f"refusing batch launch while instances already exist: "
            f"{[item.get('id') for item in active]}"
        )
    selected: list[dict[str, Any]] = []
    machine_ids: set[int] = set()
    for entry in entries:
        offer = client.offer(entry["offer_id"])
        if not offer.get("rentable", False) or offer.get("rented", False):
            raise RuntimeError(f"offer {entry['offer_id']} is not currently rentable")
        rate = offer_rate(offer)
        if rate <= 0 or rate > max_hourly:
            raise RuntimeError(
                f"offer {entry['offer_id']} rate ${rate:.4f}/hr violates "
                f"max hourly ${max_hourly:.4f}/hr"
            )
        cuda_max = float(offer.get("cuda_max_good") or 0)
        if cuda_max < min_cuda:
            raise RuntimeError(
                f"offer {entry['offer_id']} CUDA ceiling {cuda_max:.1f} is below "
                f"required runtime {min_cuda:.1f}"
            )
        machine_id = int(offer.get("machine_id") or -1)
        if machine_id in machine_ids:
            raise RuntimeError(f"batch contains duplicate machine {machine_id}")
        machine_ids.add(machine_id)
        selected.append(
            {
                **entry,
                "machine_id": machine_id,
                "gpu_name": offer.get("gpu_name"),
                "num_gpus": offer.get("num_gpus"),
                "gpu_ram_mib": offer.get("gpu_ram"),
                "cpu_name": offer.get("cpu_name"),
                "listed_cpu_effective": offer.get("cpu_cores_effective"),
                "hourly_rate": rate,
                "verification": offer.get("verification"),
                "reliability": offer.get("reliability"),
                "cuda_max_good": cuda_max,
            }
        )
    projected = sum(item["hourly_rate"] for item in selected) * max_instance_minutes / 60
    if spent + projected > budget:
        raise RuntimeError(
            f"batch budget preflight failed: ${spent:.4f} spent + ${projected:.4f} "
            f"projected > ${budget:.2f} cap"
        )
    return {
        "recorded_spend_before": spent,
        "projected_batch_max": projected,
        "projected_total_max": spent + projected,
        "budget_cap": budget,
        "max_instance_minutes": max_instance_minutes,
        "runs": selected,
    }


def _child_command(args: argparse.Namespace, entry: dict[str, Any]) -> list[str]:
    return [
        sys.executable,
        "-m",
        "vast_benchmarking.vast_runner",
        "--env-file",
        args.env_file,
        "run-offer",
        "--offer-id",
        str(entry["offer_id"]),
        "--category",
        entry["category"],
        "--label",
        entry["label"],
        "--db",
        args.db,
        "--results-dir",
        args.results_dir,
        "--project-dir",
        args.project_dir,
        "--ssh-key",
        args.ssh_key,
        "--image",
        args.image,
        "--disk-gb",
        str(args.disk_gb),
        "--profile",
        args.profile,
        "--benchmark-max-seconds",
        str(args.benchmark_max_seconds),
        "--startup-timeout-seconds",
        str(args.startup_timeout_seconds),
        "--ssh-timeout-seconds",
        str(args.ssh_timeout_seconds),
        "--max-instance-minutes",
        str(args.max_instance_minutes),
        "--max-hourly",
        str(args.max_hourly),
        "--min-cuda",
        str(args.min_cuda),
        "--budget",
        str(args.budget),
        "--allow-existing-instances",
    ]


def run_batch(args: argparse.Namespace) -> int:
    entries = load_manifest(args.manifest)
    client = VastClient(read_api_key(args.env_file))
    db_path = str(Path(args.db).resolve())
    args.db = db_path
    args.results_dir = str(Path(args.results_dir).resolve())
    args.project_dir = str(Path(args.project_dir).resolve())
    args.ssh_key = str(Path(args.ssh_key).expanduser().resolve())
    spent = float(rental_summary(db_path).get("estimated_cost") or 0)
    preflight = preflight_batch(
        client,
        entries,
        spent=spent,
        budget=args.budget,
        max_hourly=args.max_hourly,
        min_cuda=args.min_cuda,
        max_instance_minutes=args.max_instance_minutes,
    )
    batch_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = Path(args.results_dir) / "batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)
    (batch_dir / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    print(json.dumps({"batch_id": batch_id, **preflight}, sort_keys=True), flush=True)

    children: list[tuple[dict[str, Any], subprocess.Popen[bytes], Any]] = []
    try:
        for entry in entries:
            log_handle = (batch_dir / f"{entry['category']}-{entry['offer_id']}.log").open("wb")
            process = subprocess.Popen(
                _child_command(args, entry),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
            children.append((entry, process, log_handle))
            print(
                json.dumps(
                    {
                        "launched_offer": entry["offer_id"],
                        "category": entry["category"],
                        "pid": process.pid,
                    }
                ),
                flush=True,
            )
            if args.launch_stagger_seconds:
                time.sleep(args.launch_stagger_seconds)
        returncodes: dict[int, int] = {}
        for entry, process, _log_handle in children:
            returncodes[entry["offer_id"]] = process.wait()
            print(
                json.dumps(
                    {"finished_offer": entry["offer_id"], "returncode": process.returncode}
                ),
                flush=True,
            )
    except BaseException:
        for _entry, process, _log_handle in children:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        for _entry, process, _log_handle in children:
            try:
                process.wait(timeout=240)
            except subprocess.TimeoutExpired:
                pass
        raise
    finally:
        for _entry, _process, log_handle in children:
            log_handle.close()

    summary = {
        "batch_id": batch_id,
        "returncodes": returncodes,
        "all_succeeded": all(code == 0 for code in returncodes.values()),
    }
    (batch_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary["all_succeeded"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vast-benchmark-batch")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--env-file", default="/etc/vastai.env")
    parser.add_argument("--db", default="results/benchmarks.sqlite")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--ssh-key", default="~/.ssh/vast_benchmark_ed25519")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--disk-gb", type=int, default=32)
    parser.add_argument("--profile", choices=("smoke", "standard"), default="standard")
    parser.add_argument("--benchmark-max-seconds", type=int, default=540)
    parser.add_argument("--startup-timeout-seconds", type=int, default=900)
    parser.add_argument("--ssh-timeout-seconds", type=int, default=300)
    parser.add_argument("--max-instance-minutes", type=float, default=30)
    parser.add_argument("--max-hourly", type=float, default=1.2)
    parser.add_argument("--min-cuda", type=float, default=12.9)
    parser.add_argument("--budget", type=float, default=5)
    parser.add_argument("--launch-stagger-seconds", type=float, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return run_batch(build_parser().parse_args(argv))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

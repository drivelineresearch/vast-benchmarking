from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vast_benchmarking.storage import list_runs, save_machine_annotations

PRIMARY_METRICS = {
    "gpu-heavy": ("gpu.concurrent.cv_images_per_sec_total", "images/s"),
    "high-effective-cpu": ("cpu.sha256_multi_gbps", "GB/s"),
    "fast-single-cpu": ("cpu.sha256_single_gbps", "GB/s"),
}


def metric_value(run: dict[str, Any], name: str) -> float | None:
    for metric in run.get("metrics", []):
        if metric.get("name") == name:
            return float(metric["value"])
    return None


def grade(percent_of_best: float) -> str:
    if percent_of_best >= 95:
        return "S"
    if percent_of_best >= 80:
        return "A"
    if percent_of_best >= 65:
        return "B"
    if percent_of_best >= 50:
        return "C"
    return "D"


def final_error(log_path: Path) -> str:
    if not log_path.is_file():
        return "No durable child log was produced."
    lines = log_path.read_text(errors="replace").splitlines()
    errors = [line.removeprefix("ERROR: ") for line in lines if line.startswith("ERROR:")]
    if errors:
        return errors[-1]
    if any("KeyboardInterrupt" in line for line in lines):
        return "Run was interrupted after a compatibility precheck failed."
    return "Run ended before a benchmark result was ingested."


def failure_annotation(
    attempt: dict[str, Any], error: str, *, source: str, updated_at: str
) -> dict[str, Any]:
    lowered = error.lower()
    if "429" in error or "too many requests" in lowered:
        disposition = "inconclusive"
        tags = ["api-rate-limit"]
        notes = (
            "Vast API throttled orchestration during the 2026-08-22 campaign; "
            "the machine itself was not evaluated."
        )
    elif "offline" in lowered:
        disposition = "known-bad"
        tags = ["offline"]
        notes = (
            "Machine went offline during the 2026-08-22 provisioning attempt; "
            "no performance result was accepted."
        )
    elif "ssh did not become ready" in lowered:
        disposition = "known-bad"
        tags = ["ssh-unavailable"]
        notes = (
            "Machine reached running state during the 2026-08-22 attempt but never "
            "exposed usable SSH within 480 seconds."
        )
    elif "did not become ssh-ready" in lowered or "rental duration" in lowered:
        disposition = "known-bad"
        tags = ["provisioning-timeout"]
        notes = (
            "Machine did not finish container provisioning within the 15-minute limit "
            "during the 2026-08-22 campaign."
        )
    else:
        disposition = "inconclusive"
        tags = ["no-result"]
        notes = error
    return {
        "machine_id": attempt["machine_id"],
        "category": attempt["category"],
        "disposition": disposition,
        "rating": None,
        "notes": notes,
        "tags": tags,
        "source": source,
        "updated_at": updated_at,
    }


def campaign_cost(db_path: Path, since: str) -> float:
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(estimated_cost), 0)
            FROM rental_events
            WHERE action = 'destroyed' AND recorded_at >= ?
            """,
            (since,),
        ).fetchone()
    finally:
        connection.close()
    return float(row[0] if row else 0)


def compile_campaign(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str]:
    db_path = Path(args.db).resolve()
    campaign_runs = [
        run
        for run in list_runs(db_path)
        if run.get("finished_at", "") >= args.since
        and run.get("vast", {}).get("category") in PRIMARY_METRICS
    ]
    runs = [run for run in campaign_runs if run.get("status") == "complete"]
    generated_at = datetime.now(UTC).isoformat()
    annotations: dict[int, dict[str, Any]] = {}
    report_groups: dict[str, list[dict[str, Any]]] = {}

    for category, (primary_metric, unit) in PRIMARY_METRICS.items():
        category_runs = [run for run in runs if run["vast"]["category"] == category]
        values = [metric_value(run, primary_metric) for run in category_runs]
        best = max((value for value in values if value is not None), default=0)
        enriched: list[dict[str, Any]] = []
        for run in category_runs:
            value = metric_value(run, primary_metric) or 0
            percent = value / best * 100 if best else 0
            rating = grade(percent)
            hourly_rate = float(run.get("hourly_rate") or 0)
            annotation = {
                "machine_id": int(run["machine_id"]),
                "category": category,
                "disposition": "recommended" if percent >= 80 else "benchmarked",
                "rating": f"{rating} ({percent:.0f}%)",
                "notes": (
                    f"Measured {value:.3f} {unit} on {primary_metric}; "
                    f"{run.get('cpu_effective')} effective CPU cores; "
                    f"{run.get('gpu_summary')}; ${hourly_rate:.3f}/hr."
                ),
                "tags": [category, f"{rating}-grade", "benchmark-complete"],
                "source": args.source,
                "updated_at": generated_at,
            }
            annotations[annotation["machine_id"]] = annotation
            enriched.append(
                {
                    **run,
                    "primary_value": value,
                    "primary_unit": unit,
                    "percent_of_best": percent,
                    "grade": rating,
                }
            )
        report_groups[category] = sorted(
            enriched, key=lambda item: item["primary_value"], reverse=True
        )

    for run in campaign_runs:
        if run.get("status") != "partial" or int(run["machine_id"]) in annotations:
            continue
        expected = len(run.get("system", {}).get("gpus") or [])
        returned = len(run.get("gpu_results") or [])
        details = (
            f"Only {returned}/{expected} visible GPUs returned concurrent benchmark data; "
            "aggregate GPU totals are excluded from leaderboards."
            if expected
            else "The benchmark did not produce all required result categories."
        )
        annotations[int(run["machine_id"])] = {
            "machine_id": int(run["machine_id"]),
            "category": run["vast"]["category"],
            "disposition": "partial",
            "rating": None,
            "notes": details,
            "tags": [run["vast"]["category"], "benchmark-partial", "incomplete-result"],
            "source": args.source,
            "updated_at": generated_at,
        }

    attempts: dict[int, dict[str, Any]] = {}
    batches_root = Path(args.batches_root)
    for batch_dir in sorted(batches_root.iterdir() if batches_root.is_dir() else []):
        preflight_path = batch_dir / "preflight.json"
        if not preflight_path.is_file():
            continue
        preflight = json.loads(preflight_path.read_text())
        for attempt in preflight.get("runs", []):
            machine_id = int(attempt["machine_id"])
            attempts[machine_id] = attempt
            if machine_id in annotations:
                continue
            log_path = batch_dir / f"{attempt['category']}-{attempt['offer_id']}.log"
            error = final_error(log_path)
            annotations[machine_id] = failure_annotation(
                attempt,
                error,
                source=args.source,
                updated_at=generated_at,
            )

    if args.overrides:
        override_payload = json.loads(Path(args.overrides).read_text())
        overrides = (
            override_payload.get("machines")
            if isinstance(override_payload, dict)
            else override_payload
        )
        for override in overrides or []:
            normalized = {
                **override,
                "machine_id": int(override["machine_id"]),
                "source": override.get("source", args.source),
                "updated_at": override.get("updated_at", generated_at),
            }
            annotations[normalized["machine_id"]] = normalized

    ordered_annotations = sorted(annotations.values(), key=lambda item: item["machine_id"])
    save_machine_annotations(db_path, ordered_annotations)
    cost = campaign_cost(db_path, args.since)
    successful_ids = {int(run["machine_id"]) for run in runs}
    failed_annotations = [
        item for item in ordered_annotations if item["machine_id"] not in successful_ids
    ]

    lines = [
        "# Vast Benchmark Expansion Results",
        "",
        f"Generated: {generated_at}",
        "",
        f"- Accepted campaign runs: **{len(runs)}**",
        f"- Partial campaign runs excluded from ratings: "
        f"**{sum(run.get('status') == 'partial' for run in campaign_runs)}**",
        f"- Estimated campaign rental cost: **${cost:.2f}**",
        f"- Attempted machines with no accepted result: **{len(failed_annotations)}**",
        "- Ratings are campaign-local percent-of-best grades: S >=95%, A >=80%, "
        "B >=65%, C >=50%, D <50%.",
        "",
    ]
    for category in PRIMARY_METRICS:
        lines.extend(
            [
                f"## {category}",
                "",
                "| Rank | Grade | Machine | Label | Primary result | Effective cores | Rate |",
                "|---:|:---:|---:|---|---:|---:|---:|",
            ]
        )
        for index, run in enumerate(report_groups[category], 1):
            lines.append(
                f"| {index} | {run['grade']} | {run['machine_id']} | {run['label']} | "
                f"{run['primary_value']:.3f} {run['primary_unit']} | "
                f"{run['cpu_effective']} | ${float(run.get('hourly_rate') or 0):.3f}/hr |"
            )
        lines.append("")

    lines.extend(
        [
            "## Failed and incompatible attempts",
            "",
            "| Machine | Category | Disposition | Tags | Note |",
            "|---:|---|---|---|---|",
        ]
    )
    for annotation in failed_annotations:
        lines.append(
            f"| {annotation['machine_id']} | {annotation.get('category') or ''} | "
            f"{annotation['disposition']} | {', '.join(annotation.get('tags') or [])} | "
            f"{annotation['notes']} |"
        )
    lines.append("")
    return ordered_annotations, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--since", required=True)
    parser.add_argument("--batches-root", required=True)
    parser.add_argument("--overrides")
    parser.add_argument("--annotations-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--source", default="2026-08-22-parallel-expansion")
    args = parser.parse_args()
    annotations, report = compile_campaign(args)
    annotations_output = Path(args.annotations_output)
    annotations_output.parent.mkdir(parents=True, exist_ok=True)
    annotations_output.write_text(json.dumps({"machines": annotations}, indent=2) + "\n")
    report_output = Path(args.report_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(report)
    print(
        json.dumps(
            {
                "annotations": len(annotations),
                "annotations_output": str(annotations_output),
                "report_output": str(report_output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

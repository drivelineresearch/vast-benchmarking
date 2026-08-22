from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

from .scoring import LEADERBOARD_METRICS, metric_leaderboard
from .storage import (
    get_machine_annotation,
    get_run,
    list_machine_annotations,
    list_runs,
    rental_summary,
)


def _compact_number(value: float) -> str:
    """Format dense dashboard values without hiding useful precision."""
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if magnitude >= 1_000:
        return f"{value / 1_000:.2f}k"
    return f"{value:.2f}"


def _dashboard_data(db_path: str) -> dict[str, Any]:
    all_runs = list_runs(db_path)
    annotations = list_machine_annotations(db_path)
    annotations_by_machine = {item["machine_id"]: item for item in annotations}
    for run in all_runs:
        run["annotation"] = annotations_by_machine.get(run.get("machine_id"))
    runs: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for run in all_runs:
        if run.get("status") != "complete":
            run["leaderboard_state"] = "partial"
            continue
        key = (
            run.get("machine_id") or run.get("run_id"),
            run.get("vast", {}).get("category"),
        )
        if key in seen:
            run["leaderboard_state"] = "superseded"
            continue
        seen.add(key)
        run["leaderboard_state"] = "accepted"
        runs.append(run)
    leaderboards: dict[str, dict[str, Any]] = {}
    for key, (metric_name, label) in LEADERBOARD_METRICS.items():
        rows = metric_leaderboard(runs, metric_name, limit=max(len(runs), 6))
        top_value = max((row["value"] for row in rows), default=0)
        for row in rows:
            row["performance_percent"] = row["value"] / top_value * 100 if top_value else 0
            hourly_rate = row["hourly_rate"] or 0
            row["value_per_dollar"] = row["value"] / hourly_rate if hourly_rate > 0 else None
        top_value_per_dollar = max(
            (row["value_per_dollar"] or 0 for row in rows),
            default=0,
        )
        for row in rows:
            row["value_per_dollar_percent"] = (
                (row["value_per_dollar"] or 0) / top_value_per_dollar * 100
                if top_value_per_dollar
                else 0
            )
            row["value_per_dollar_display"] = (
                _compact_number(row["value_per_dollar"])
                if row["value_per_dollar"] is not None
                else "Unavailable"
            )
        leaderboards[key] = {
            "title": label,
            "metric": metric_name,
            "rows": rows,
            "top_value": top_value,
            "top_value_per_dollar": top_value_per_dollar,
            "display_limit": min(6, len(rows)),
            "candidate_count": len(rows),
        }
    complete = len(runs)
    total_gpu_count = sum(
        int(run.get("system", {}).get("gpus") and len(run["system"]["gpus"]) or 0) for run in runs
    )
    return {
        "runs": runs,
        "all_runs": all_runs,
        "machine_annotations": annotations,
        "leaderboards": leaderboards,
        "summary": {
            "run_count": len(all_runs),
            "complete_count": complete,
            "excluded_count": len(all_runs) - complete,
            "gpu_count": total_gpu_count,
            "machine_count": len({run.get("machine_id") for run in runs if run.get("machine_id")}),
        },
        "rentals": rental_summary(db_path),
    }


def create_app(db_path: str) -> Flask:
    app = Flask(__name__)
    # Production Gunicorn listens on loopback. Only the local reverse proxy can reach
    # it, which is why these forwarded headers are trusted.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.config["BENCHMARK_DB"] = str(Path(db_path).resolve())

    @app.get("/")
    def index() -> str:
        return render_template("index.html", **_dashboard_data(app.config["BENCHMARK_DB"]))

    @app.get("/runs/<run_id>")
    def run_detail(run_id: str) -> str:
        run = get_run(app.config["BENCHMARK_DB"], run_id)
        if run is None:
            abort(404)
        categories: dict[str, list[dict[str, Any]]] = {}
        for metric in run["metrics"]:
            categories.setdefault(metric["category"], []).append(metric)
        annotation = (
            get_machine_annotation(app.config["BENCHMARK_DB"], run["machine_id"])
            if run.get("machine_id")
            else None
        )
        return render_template(
            "run.html", run=run, categories=categories, annotation=annotation
        )

    @app.get("/api/runs")
    def api_runs() -> Any:
        return jsonify(_dashboard_data(app.config["BENCHMARK_DB"]))

    @app.get("/healthz")
    def healthz() -> Any:
        return jsonify({"ok": True})

    return app

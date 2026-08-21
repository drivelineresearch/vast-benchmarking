from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template

from .scoring import LEADERBOARD_METRICS, metric_leaderboard, relative_scores
from .storage import get_run, list_runs, rental_summary


def _dashboard_data(db_path: str) -> dict[str, Any]:
    all_runs = list_runs(db_path)
    runs: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for run in all_runs:
        if run.get("status") != "complete":
            continue
        key = (
            run.get("machine_id") or run.get("run_id"),
            run.get("vast", {}).get("category"),
        )
        if key in seen:
            continue
        seen.add(key)
        runs.append(run)
    scored = relative_scores(runs)
    leaderboards = {
        key: {
            "title": label,
            "metric": metric_name,
            "rows": metric_leaderboard(runs, metric_name, limit=10),
        }
        for key, (metric_name, label) in LEADERBOARD_METRICS.items()
    }
    complete = len(runs)
    total_gpu_count = sum(
        int(run.get("system", {}).get("gpus") and len(run["system"]["gpus"]) or 0) for run in runs
    )
    return {
        "runs": scored,
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
        return render_template("run.html", run=run, categories=categories)

    @app.get("/api/runs")
    def api_runs() -> Any:
        return jsonify(_dashboard_data(app.config["BENCHMARK_DB"]))

    @app.get("/healthz")
    def healthz() -> Any:
        return jsonify({"ok": True, "database": app.config["BENCHMARK_DB"]})

    return app

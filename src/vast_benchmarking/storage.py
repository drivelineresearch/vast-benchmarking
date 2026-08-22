from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import BenchmarkResult

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    status TEXT NOT NULL,
    profile TEXT NOT NULL,
    benchmark_version TEXT NOT NULL,
    label TEXT NOT NULL,
    hostname TEXT,
    cpu_model TEXT,
    cpu_effective REAL,
    gpu_summary TEXT,
    machine_id INTEGER,
    offer_id INTEGER,
    instance_id INTEGER,
    hourly_rate REAL,
    verification TEXT,
    system_json TEXT NOT NULL,
    config_json TEXT NOT NULL,
    vast_json TEXT NOT NULL,
    errors_json TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    category TEXT NOT NULL,
    higher_is_better INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    PRIMARY KEY (run_id, name)
);

CREATE INDEX IF NOT EXISTS idx_metrics_name_value ON metrics(name, value DESC);
CREATE INDEX IF NOT EXISTS idx_runs_finished ON runs(finished_at DESC);

CREATE TABLE IF NOT EXISTS rental_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    action TEXT NOT NULL,
    instance_id INTEGER,
    offer_id INTEGER,
    hourly_rate REAL,
    account_credit REAL,
    estimated_cost REAL,
    details_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS machine_annotations (
    machine_id INTEGER PRIMARY KEY,
    category TEXT,
    disposition TEXT NOT NULL,
    rating TEXT,
    notes TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _gpu_summary(system: dict[str, Any]) -> str:
    devices = system.get("gpus") or []
    if not devices:
        return "CPU only"
    grouped: dict[str, int] = {}
    for device in devices:
        name = str(device.get("name") or "Unknown GPU")
        grouped[name] = grouped.get(name, 0) + 1
    return ", ".join(f"{count}× {name}" for name, count in grouped.items())


@contextmanager
def connect(path: str | Path) -> Iterator[sqlite3.Connection]:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        yield connection
    finally:
        connection.close()


def init_db(path: str | Path) -> None:
    with connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute("PRAGMA user_version = 2")
        connection.commit()


def save_result(path: str | Path, result: BenchmarkResult) -> None:
    init_db(path)
    vast = result.vast
    raw = result.to_json(indent=None)
    with connect(path) as connection:
        connection.execute("BEGIN")
        connection.execute(
            """
            INSERT INTO runs (
                run_id, started_at, finished_at, duration_seconds, status, profile,
                benchmark_version, label, hostname, cpu_model, cpu_effective,
                gpu_summary, machine_id, offer_id, instance_id, hourly_rate,
                verification, system_json, config_json, vast_json, errors_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                finished_at = excluded.finished_at,
                duration_seconds = excluded.duration_seconds,
                status = excluded.status,
                label = excluded.label,
                system_json = excluded.system_json,
                config_json = excluded.config_json,
                vast_json = excluded.vast_json,
                errors_json = excluded.errors_json,
                raw_json = excluded.raw_json
            """,
            (
                result.run_id,
                result.started_at,
                result.finished_at,
                result.duration_seconds,
                result.status,
                result.profile,
                result.benchmark_version,
                result.label,
                result.system.get("hostname"),
                result.system.get("cpu_model"),
                result.system.get("cpu_effective"),
                _gpu_summary(result.system),
                vast.get("machine_id"),
                vast.get("offer_id"),
                vast.get("instance_id"),
                vast.get("hourly_rate"),
                vast.get("verification"),
                json.dumps(result.system, sort_keys=True),
                json.dumps(result.config, sort_keys=True),
                json.dumps(vast, sort_keys=True),
                json.dumps(result.errors),
                raw,
            ),
        )
        connection.execute("DELETE FROM metrics WHERE run_id = ?", (result.run_id,))
        connection.executemany(
            """
            INSERT INTO metrics (
                run_id, name, value, unit, category, higher_is_better, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    result.run_id,
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.category,
                    int(metric.higher_is_better),
                    json.dumps(metric.metadata, sort_keys=True),
                )
                for metric in result.metrics
            ],
        )
        connection.commit()


def ingest_json(path: str | Path, json_path: str | Path) -> BenchmarkResult:
    payload = json.loads(Path(json_path).read_text())
    result = BenchmarkResult.from_dict(payload)
    save_result(path, result)
    return result


def record_rental_event(
    path: str | Path,
    *,
    recorded_at: str,
    action: str,
    instance_id: int | None,
    offer_id: int | None,
    hourly_rate: float | None,
    account_credit: float | None,
    estimated_cost: float | None,
    details: dict[str, Any],
) -> None:
    init_db(path)
    with connect(path) as connection:
        connection.execute(
            """
            INSERT INTO rental_events (
                recorded_at, action, instance_id, offer_id, hourly_rate,
                account_credit, estimated_cost, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recorded_at,
                action,
                instance_id,
                offer_id,
                hourly_rate,
                account_credit,
                estimated_cost,
                json.dumps(details, sort_keys=True),
            ),
        )
        connection.commit()


def list_runs(path: str | Path) -> list[dict[str, Any]]:
    init_db(path)
    with connect(path) as connection:
        run_rows = connection.execute("SELECT * FROM runs ORDER BY finished_at DESC").fetchall()
        metric_rows = connection.execute("SELECT * FROM metrics ORDER BY category, name").fetchall()
    by_run: dict[str, list[dict[str, Any]]] = {}
    for row in metric_rows:
        metric = dict(row)
        metric["metadata"] = json.loads(metric.pop("metadata_json"))
        by_run.setdefault(metric["run_id"], []).append(metric)

    runs: list[dict[str, Any]] = []
    for row in run_rows:
        run = dict(row)
        run["metrics"] = by_run.get(run["run_id"], [])
        run["system"] = json.loads(run.pop("system_json"))
        run["config"] = json.loads(run.pop("config_json"))
        run["vast"] = json.loads(run.pop("vast_json"))
        run["errors"] = json.loads(run.pop("errors_json"))
        raw = json.loads(run.pop("raw_json"))
        run["gpu_results"] = raw.get("gpu_results", [])
        runs.append(run)
    return runs


def get_run(path: str | Path, run_id: str) -> dict[str, Any] | None:
    return next((run for run in list_runs(path) if run["run_id"] == run_id), None)


def save_machine_annotations(
    path: str | Path, annotations: list[dict[str, Any]]
) -> None:
    init_db(path)
    now = datetime.now(UTC).isoformat()
    rows: list[tuple[Any, ...]] = []
    for annotation in annotations:
        if not annotation.get("machine_id") or not annotation.get("disposition"):
            raise ValueError("machine annotations require machine_id and disposition")
        rows.append(
            (
                int(annotation["machine_id"]),
                annotation.get("category"),
                str(annotation["disposition"]),
                annotation.get("rating"),
                str(annotation.get("notes") or ""),
                json.dumps(annotation.get("tags") or [], sort_keys=True),
                str(annotation.get("source") or "local"),
                str(annotation.get("updated_at") or now),
            )
        )
    with connect(path) as connection:
        connection.executemany(
            """
            INSERT INTO machine_annotations (
                machine_id, category, disposition, rating, notes,
                tags_json, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(machine_id) DO UPDATE SET
                category = excluded.category,
                disposition = excluded.disposition,
                rating = excluded.rating,
                notes = excluded.notes,
                tags_json = excluded.tags_json,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            rows,
        )
        connection.commit()


def list_machine_annotations(path: str | Path) -> list[dict[str, Any]]:
    init_db(path)
    with connect(path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM machine_annotations
            ORDER BY
                CASE disposition WHEN 'known-bad' THEN 0 WHEN 'incompatible' THEN 1 ELSE 2 END,
                machine_id
            """
        ).fetchall()
    annotations: list[dict[str, Any]] = []
    for row in rows:
        annotation = dict(row)
        annotation["tags"] = json.loads(annotation.pop("tags_json"))
        annotations.append(annotation)
    return annotations


def get_machine_annotation(path: str | Path, machine_id: int) -> dict[str, Any] | None:
    return next(
        (
            annotation
            for annotation in list_machine_annotations(path)
            if annotation["machine_id"] == machine_id
        ),
        None,
    )


def rental_summary(path: str | Path) -> dict[str, Any]:
    init_db(path)
    with connect(path) as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS event_count,
                COALESCE(SUM(CASE WHEN action = 'destroyed' THEN estimated_cost ELSE 0 END), 0)
                    AS estimated_cost,
                MIN(account_credit) AS minimum_credit,
                MAX(account_credit) AS maximum_credit
            FROM rental_events
            """
        ).fetchone()
    return dict(row) if row else {}

from __future__ import annotations

import json

from vast_benchmarking.models import BenchmarkResult
from vast_benchmarking.storage import ingest_json, list_runs, save_result


def test_result_round_trip(tmp_path, sample_result: BenchmarkResult) -> None:
    database = tmp_path / "benchmarks.sqlite"
    save_result(database, sample_result)

    runs = list_runs(database)
    assert len(runs) == 1
    run = runs[0]
    assert run["run_id"] == sample_result.run_id
    assert run["machine_id"] == 456
    assert run["cpu_effective"] == 128
    assert run["gpu_summary"] == "2× RTX 5060 Ti"
    assert len(run["metrics"]) == 6


def test_ingest_json_is_idempotent(tmp_path, sample_result: BenchmarkResult) -> None:
    database = tmp_path / "benchmarks.sqlite"
    source = tmp_path / "result.json"
    source.write_text(json.dumps(sample_result.to_dict()))

    ingest_json(database, source)
    ingest_json(database, source)

    assert len(list_runs(database)) == 1

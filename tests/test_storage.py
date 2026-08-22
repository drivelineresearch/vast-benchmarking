from __future__ import annotations

import json

from vast_benchmarking.models import BenchmarkResult
from vast_benchmarking.storage import (
    ingest_json,
    list_machine_annotations,
    list_runs,
    save_machine_annotations,
    save_result,
)


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
    assert run["gpu_results"] == sample_result.gpu_results


def test_ingest_json_is_idempotent(tmp_path, sample_result: BenchmarkResult) -> None:
    database = tmp_path / "benchmarks.sqlite"
    source = tmp_path / "result.json"
    source.write_text(json.dumps(sample_result.to_dict()))

    ingest_json(database, source)
    ingest_json(database, source)

    assert len(list_runs(database)) == 1


def test_machine_annotations_upsert(tmp_path) -> None:
    database = tmp_path / "benchmarks.sqlite"
    save_machine_annotations(
        database,
        [
            {
                "machine_id": 456,
                "category": "gpu-heavy",
                "disposition": "recommended",
                "rating": "A",
                "notes": "Strong CV throughput.",
                "tags": ["cv", "verified"],
                "source": "test",
            }
        ],
    )
    annotations = list_machine_annotations(database)
    assert annotations[0]["machine_id"] == 456
    assert annotations[0]["rating"] == "A"
    assert annotations[0]["tags"] == ["cv", "verified"]

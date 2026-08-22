from __future__ import annotations

from vast_benchmarking.models import BenchmarkResult
from vast_benchmarking.storage import save_result
from vast_benchmarking.web import create_app


def test_dashboard_and_detail_render(tmp_path, sample_result: BenchmarkResult) -> None:
    database = tmp_path / "benchmarks.sqlite"
    save_result(database, sample_result)
    app = create_app(str(database))
    app.config.update(TESTING=True)

    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sample GPU Host" in response.data
    assert b"Overall leaderboard" in response.data
    assert b"All run history" in response.data
    assert b"accepted" in response.data

    response = client.get("/api/runs")
    assert response.status_code == 200
    assert len(response.get_json()["all_runs"]) == 1

    response = client.get(f"/runs/{sample_result.run_id}")
    assert response.status_code == 200
    assert b"gpu.concurrent.cv_images_per_sec_total" in response.data

    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_forwarded_prefix_is_used_for_links(tmp_path, sample_result: BenchmarkResult) -> None:
    database = tmp_path / "benchmarks.sqlite"
    save_result(database, sample_result)
    app = create_app(str(database))
    app.config.update(TESTING=True)

    response = app.test_client().get(
        "/",
        headers={
            "X-Forwarded-Host": "dc-boddydev.drivelinebaseball.com",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Prefix": "/vast-benchmark",
        },
    )

    assert response.status_code == 200
    assert b'href="/vast-benchmark/static/app.css"' in response.data
    assert b'href="/vast-benchmark/runs/' in response.data

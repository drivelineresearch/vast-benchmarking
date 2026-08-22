from __future__ import annotations

from vast_benchmarking.models import BenchmarkResult
from vast_benchmarking.storage import save_machine_annotations, save_result
from vast_benchmarking.web import create_app


def test_dashboard_and_detail_render(tmp_path, sample_result: BenchmarkResult) -> None:
    database = tmp_path / "benchmarks.sqlite"
    save_result(database, sample_result)
    save_machine_annotations(
        database,
        [
            {
                "machine_id": 456,
                "category": "gpu-heavy",
                "disposition": "recommended",
                "rating": "A",
                "notes": "Strong CV throughput.",
                "tags": ["cv"],
            }
        ],
    )
    app = create_app(str(database))
    app.config.update(TESTING=True)

    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sample GPU Host" in response.data
    assert b"Overall leaderboard" not in response.data
    assert b"Category rankings" in response.data
    assert b"Measured performance" in response.data
    assert b"Hourly rental price" in response.data
    assert b"Machine #456" in response.data
    assert b"Offer #123" in response.data
    assert b"Instance #789" in response.data
    assert b"$0.500" in response.data
    assert b"All run history" in response.data
    assert b"accepted" in response.data
    assert b"Ratings and known issues" in response.data
    assert b"Strong CV throughput" in response.data

    response = client.get("/api/runs")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["all_runs"]) == 1
    row = payload["leaderboards"]["gpu_cv"]["rows"][0]
    assert row["machine_id"] == 456
    assert row["offer_id"] == 123
    assert row["instance_id"] == 789
    assert row["hourly_rate"] == 0.5
    assert row["performance_percent"] == 100
    assert row["price_percent"] == 100

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

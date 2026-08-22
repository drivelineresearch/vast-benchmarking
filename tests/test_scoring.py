from __future__ import annotations

from vast_benchmarking.scoring import metric_leaderboard, relative_scores


def test_relative_scores_reward_balanced_performance() -> None:
    runs = [
        {
            "run_id": "balanced",
            "metrics": [
                {"name": "cpu.sha256_multi_gbps", "value": 90},
                {"name": "memory.copy_gbps", "value": 90},
            ],
        },
        {
            "run_id": "one-dimensional",
            "metrics": [
                {"name": "cpu.sha256_multi_gbps", "value": 100},
                {"name": "memory.copy_gbps", "value": 20},
            ],
        },
    ]

    scored = relative_scores(runs)
    assert scored[0]["run_id"] == "balanced"
    assert scored[0]["relative_score"] > scored[1]["relative_score"]
    assert scored[0]["score_components"] == 2


def test_metric_leaderboard_exposes_numeric_vast_ids_and_hardware() -> None:
    rows = metric_leaderboard(
        [
            {
                "run_id": "12345678-abcd",
                "label": "Machine A",
                "machine_id": 101,
                "offer_id": 202,
                "instance_id": 303,
                "hourly_rate": 0.75,
                "verification": "verified",
                "cpu_effective": 64,
                "cpu_model": "Example CPU",
                "gpu_summary": "2× Example GPU",
                "duration_seconds": 120,
                "system": {
                    "memory_total_bytes": 128 * 1024**3,
                    "torch_cuda_version": "12.8",
                    "gpus": [{"memory_mib": 8192}, {"memory_mib": 8192}],
                },
                "vast": {"reliability": 0.99, "geolocation": "Seattle, WA"},
                "metrics": [
                    {
                        "name": "gpu.concurrent.cv_images_per_sec_total",
                        "value": 1000,
                        "unit": "images/s",
                    }
                ],
            }
        ],
        "gpu.concurrent.cv_images_per_sec_total",
    )

    assert rows[0]["machine_id"] == 101
    assert rows[0]["offer_id"] == 202
    assert rows[0]["instance_id"] == 303
    assert rows[0]["run_short_id"] == "12345678"
    assert rows[0]["memory_gib"] == 128
    assert rows[0]["gpu_vram_gib"] == 8
    assert rows[0]["reliability_pct"] == 99

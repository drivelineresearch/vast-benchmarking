from __future__ import annotations

from vast_benchmarking.scoring import relative_scores


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

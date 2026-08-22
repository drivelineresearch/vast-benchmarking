from __future__ import annotations

import json

import pytest

from vast_benchmarking.batch_runner import load_manifest, preflight_batch


class FakeClient:
    def __init__(self, offers: dict[int, dict], instances: list[dict] | None = None) -> None:
        self.offers = offers
        self._instances = instances or []

    def instances(self) -> list[dict]:
        return self._instances

    def offer(self, offer_id: int) -> dict:
        return self.offers[offer_id]


def test_manifest_and_combined_budget_preflight(tmp_path) -> None:
    manifest = tmp_path / "batch.json"
    manifest.write_text(
        json.dumps(
            {
                "runs": [
                    {"offer_id": 1, "category": "gpu-heavy", "label": "GPU A"},
                    {"offer_id": 2, "category": "cpu-high", "label": "CPU B"},
                ]
            }
        )
    )
    entries = load_manifest(manifest)
    client = FakeClient(
        {
            1: {
                "rentable": True,
                "rented": False,
                "machine_id": 11,
                "dph_total": 1.0,
                "cuda_max_good": 13.0,
            },
            2: {
                "rentable": True,
                "rented": False,
                "machine_id": 22,
                "dph_total": 0.5,
                "cuda_max_good": 13.0,
            },
        }
    )

    result = preflight_batch(
        client,
        entries,
        spent=0.5,
        budget=2,
        max_hourly=1.2,
        min_cuda=12.9,
        max_instance_minutes=30,
    )

    assert result["projected_batch_max"] == pytest.approx(0.75)
    assert result["projected_total_max"] == pytest.approx(1.25)


def test_batch_preflight_rejects_existing_instances() -> None:
    client = FakeClient({}, instances=[{"id": 99}])
    with pytest.raises(RuntimeError, match="instances already exist"):
        preflight_batch(
            client,
            [{"offer_id": 1, "category": "gpu-heavy", "label": "GPU A"}],
            spent=0,
            budget=10,
            max_hourly=1.2,
            min_cuda=12.9,
            max_instance_minutes=30,
        )

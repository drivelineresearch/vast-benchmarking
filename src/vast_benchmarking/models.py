from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass(slots=True)
class Metric:
    name: str
    value: float
    unit: str
    category: str
    higher_is_better: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkResult:
    run_id: str
    started_at: str
    finished_at: str
    duration_seconds: float
    status: str
    profile: str
    benchmark_version: str
    label: str
    system: dict[str, Any]
    config: dict[str, Any]
    metrics: list[Metric]
    gpu_results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    vast: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BenchmarkResult:
        data = dict(payload)
        data["metrics"] = [
            metric if isinstance(metric, Metric) else Metric(**metric)
            for metric in data.get("metrics", [])
        ]
        return cls(**data)

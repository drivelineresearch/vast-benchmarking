from __future__ import annotations

import argparse
import json
from pathlib import Path

from vast_benchmarking.models import BenchmarkResult
from vast_benchmarking.storage import save_result
from vast_benchmarking.validation import benchmark_status


def revalidate(path: Path, db_path: Path) -> tuple[str, str, list[str]]:
    result = BenchmarkResult.from_dict(json.loads(path.read_text()))
    previous = result.status
    status, issues = benchmark_status(
        system=result.system,
        metrics=result.metrics,
        gpu_results=result.gpu_results,
        elapsed_seconds=result.duration_seconds,
        max_seconds=float(result.config.get("max_seconds") or 0),
    )
    result.status = status
    result.errors.extend(issue for issue in issues if issue not in result.errors)
    path.write_text(result.to_json() + "\n")
    save_result(db_path, result)
    return previous, status, issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--since", default="")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    changed: list[dict[str, object]] = []
    checked = 0
    for path in sorted(Path(args.results_dir).glob("*.json")):
        payload = json.loads(path.read_text())
        if args.since and str(payload.get("finished_at") or "") < args.since:
            continue
        previous, current, issues = revalidate(path, db_path)
        checked += 1
        if previous != current:
            changed.append(
                {
                    "path": str(path),
                    "previous": previous,
                    "current": current,
                    "issues": issues,
                }
            )
    print(json.dumps({"checked": checked, "changed": changed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

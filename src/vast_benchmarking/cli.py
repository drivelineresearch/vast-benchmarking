from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .runner import run_benchmark
from .storage import ingest_json, init_db, save_machine_annotations


def _json_object(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vast-benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the bounded hardware benchmark")
    run_parser.add_argument("--profile", choices=("smoke", "standard"), default="standard")
    run_parser.add_argument("--label", default="")
    run_parser.add_argument("--disk-dir", default="/tmp")
    run_parser.add_argument("--max-seconds", type=int)
    run_parser.add_argument("--db")
    run_parser.add_argument("--output")
    run_parser.add_argument("--vast-meta", type=_json_object, default={})

    init_parser = subparsers.add_parser("init-db", help="Initialize an empty results database")
    init_parser.add_argument("--db", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a benchmark JSON result")
    ingest_parser.add_argument("result")
    ingest_parser.add_argument("--db", required=True)

    annotate_parser = subparsers.add_parser(
        "annotate", help="Upsert machine ratings and operational notes"
    )
    annotate_parser.add_argument("annotations")
    annotate_parser.add_argument("--db", required=True)

    serve_parser = subparsers.add_parser("serve", help="Serve the leaderboard dashboard")
    serve_parser.add_argument("--db", required=True)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.add_argument("--debug", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        result = run_benchmark(
            profile=args.profile,
            label=args.label,
            disk_dir=args.disk_dir,
            max_seconds=args.max_seconds,
            db_path=args.db,
            output_path=args.output,
            vast=args.vast_meta,
        )
        print(result.to_json())
        return 0 if result.status == "complete" else 2
    if args.command == "init-db":
        init_db(args.db)
        print(str(Path(args.db).resolve()))
        return 0
    if args.command == "ingest":
        result = ingest_json(args.db, args.result)
        print(json.dumps({"run_id": result.run_id, "status": result.status}))
        return 0
    if args.command == "annotate":
        payload = json.loads(Path(args.annotations).read_text())
        annotations = payload.get("machines") if isinstance(payload, dict) else payload
        if not isinstance(annotations, list):
            raise ValueError("annotation file must contain a machines list")
        save_machine_annotations(args.db, annotations)
        print(json.dumps({"annotations_saved": len(annotations)}))
        return 0
    if args.command == "serve":
        from .web import create_app

        init_db(args.db)
        app = create_app(args.db)
        app.run(host=args.host, port=args.port, debug=args.debug)
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

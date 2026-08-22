from __future__ import annotations

import os

from .web import create_app

database = os.environ.get("VAST_BENCHMARK_DB", "results/benchmarks.sqlite")
app = create_app(database)

# Benchmark contract

Read this before changing benchmark execution, result validation, scoring, storage, or
dashboard metrics.

## Runtime and portability

- The standard profile must finish within its 540-second wall-clock budget in a normal
  CUDA-enabled Docker container.
- A run must not download a model. GPU CV uses a small synthetic convolution workload.
- The JSON artifact remains portable and self-describing. Schema changes need compatible
  ingestion behavior or an explicit migration plan.

## Capacity and acceptance

- `cpu.effective_cores` is the lower of the process affinity and cgroup CPU quota. Keep
  the fractional value; worker selection may round up to exercise fractional capacity.
- GPU totals are accepted only when every visible CUDA device returns its concurrent
  worker result. Preserve partial records for diagnosis but exclude them from rankings.
- Within each machine/category pair, only the newest complete run enters a leaderboard;
  older complete runs remain visible as superseded history.

## Comparison semantics

- Raw category metrics are authoritative. A category leader is 100%, and every other bar
  is its raw metric divided by that leader's metric.
- Performance per dollar is the raw metric divided by the historical hourly rate. It is
  meaningful only within the same metric category.
- A displayed rental rate is the rate captured for that run. Never present it as a live
  offer or current provider price.
- Composite relative scores are secondary summaries. Do not use them to replace category
  metrics or compare runs with missing components without a visible caveat.

## Verification

Use synthetic result fixtures for acceptance and normalization tests. Benchmark changes
also need a smoke-profile run on available local hardware; a live Vast run requires a
separately authorized budget.

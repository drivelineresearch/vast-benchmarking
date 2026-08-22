# Benchmark methodology

Vast Benchmarking answers a practical question: how much hardware can this rented
container actually use? Marketplace specifications provide context, but the dashboard
ranks measurements taken inside the container.

## Runtime contract

- The `standard` profile has a hard 540-second wall-clock budget.
- The `smoke` profile is a shorter environment and integration check.
- GPU CV uses synthetic tensors and a small convolution workload. It does not download a
  model or dataset.
- Each JSON result is portable and self-describing. SQLite normalizes that record for
  queries while retaining the raw payload.

## GPU workloads

The FP16 compute test runs matrix multiplication concurrently on every visible CUDA
device and reports aggregate TFLOP/s.

The CV test runs a synthetic convolution-shaped workload on every visible device at the
same time and reports aggregate images/s. It also records host-to-device transport,
utilization, power, temperature, and the outcome from each worker.

Aggregate GPU metrics are accepted only when every visible GPU returns its concurrent
worker result. Partial records remain inspectable, but do not enter a leaderboard.

## CPU workloads

Effective CPU cores are calculated as:

```text
min(process affinity CPUs, cgroup CPU quota)
```

The fractional value is preserved. Worker selection may round up to exercise fractional
capacity, but the reported capacity is not replaced with the host's advertised core
count.

The single-thread test runs SHA-256 with one worker. The multicore test runs SHA-256
across the container's effective concurrency. Torch matrix multiplication provides a
separate CPU compute measurement.

## Memory and disk

The memory tests report NumPy copy, fill, and scale bandwidth. They measure sustained
array movement in the container, not DIMM specifications.

The disk test performs sequential writes with `fsync` and cache-advised reads on the
selected path. Filesystem, mount, cache behavior, and remote storage can affect the
result. Compare disk results only when the tested paths are operationally similar.

## Acceptance and history

- A complete run must satisfy the schema and required workload checks.
- A GPU run is partial when any visible device worker is missing.
- Within each machine and category, only the newest complete run enters rankings.
- Older complete runs remain visible as superseded history.
- Failures and incompatible attempts can be annotated without receiving a performance
  rating.

## Rankings and value

Raw category metrics are authoritative. The accepted category leader is 100%. Each
other machine receives:

```text
percent of best = machine metric / leader metric × 100
performance per dollar = machine metric / historical hourly rate
```

Performance per dollar is meaningful only within one metric category. It does not make
images/s, TFLOP/s, GB/s, or distinct workload families interchangeable.

Rental price is captured at benchmark time. It is historical context, not a live offer
or a promise that the machine can still be rented at that rate.

## Reproducibility limits

Treat close results as estimates rather than permanent hardware truths. Provider load,
clock behavior, thermals, container limits, driver/runtime combinations, and storage
topology can move a result. Record the benchmark version, profile, image, machine ID,
offer ID, instance ID, timestamp, and raw JSON when making a consequential comparison.

# 🧪 Benchmark methodology

Vast Benchmarking asks one practical question: **how much hardware capacity can this
rented container actually use?** Marketplace specifications remain useful context, but
the dashboard ranks measured results from inside the container.

## ⏱️ Runtime contract

- The `standard` profile has a hard **540-second benchmark wall-clock budget**.
- The `smoke` profile is a shorter environment and integration check.
- GPU CV uses synthetic tensors and a small convolution workload. It does not download a
  model or dataset.
- Each JSON result is portable and self-describing. SQLite normalizes that record for
  queries while retaining the raw payload.

## 🎮 GPU workloads

**FP16 compute** runs matrix multiplication concurrently on every visible CUDA device
and reports aggregate TFLOP/s.

**CV throughput** runs a synthetic convolution-shaped workload concurrently on every
visible device and reports aggregate images/s. Supporting metrics include host-to-device
transport, utilization, power, temperature, and per-device worker outcomes.

Aggregate GPU metrics are accepted only when every visible GPU returns its concurrent
worker result. Partial records remain inspectable, but do not enter a leaderboard.

## 🧠 CPU workloads

**Effective CPU cores** are calculated as:

```text
min(process affinity CPUs, cgroup CPU quota)
```

The fractional value is preserved. Worker selection may round up to exercise fractional
capacity, but the reported capacity is not replaced with the host's advertised core
count.

**Single-thread throughput** runs SHA-256 with one worker. **Multicore throughput** runs
SHA-256 across effective container concurrency. Torch matrix multiplication supplies an
additional CPU compute signal.

## 💾 Memory and disk

**Memory** reports NumPy copy, fill, and scale bandwidth. These measure sustained array
movement in the active container, not DIMM specifications.

**Disk** performs sequential writes with `fsync` and cache-advised reads on the selected
benchmark path. Filesystem, mount, cache behavior, and remote storage can all influence
the result, so compare disk results only when the tested paths are operationally similar.

## ✅ Acceptance and history

- A complete run must satisfy the schema and required workload checks.
- A GPU run is partial when any visible device worker is missing.
- Within each machine and category, only the newest complete run enters rankings.
- Older complete runs remain visible as superseded history.
- Failures and incompatible attempts can be annotated without receiving a performance
  rating.

## 📈 Rankings and value

Raw category metrics are authoritative. The accepted category leader is **100%**, and
each other machine receives:

```text
percent of best = machine metric / leader metric × 100
performance per dollar = machine metric / historical hourly rate
```

Performance per dollar is meaningful only within one metric category. It does not make
images/s, TFLOP/s, GB/s, or distinct workload families interchangeable.

Rental price is captured at benchmark time. It is historical context, not a live offer
or a promise that the machine can still be rented at that rate.

## ⚠️ Reproducibility limits

Treat close results as estimates rather than permanent hardware truths. Provider load,
clock behavior, thermals, container limits, driver/runtime combinations, and storage
topology can move a result. Record the benchmark version, profile, image, machine ID,
offer ID, instance ID, timestamp, and raw JSON when making a consequential comparison.

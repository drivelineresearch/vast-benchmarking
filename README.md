<p align="center">
  <img src="assets/vast-benchmarking-banner.png" alt="Vast Benchmarking hardware throughput banner" width="100%">
</p>

<h1 align="center">Vast Benchmarking</h1>

<p align="center">
  <a href="https://github.com/drivelineresearch/vast-benchmarking/actions/workflows/ci.yml"><img src="https://github.com/drivelineresearch/vast-benchmarking/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="assets/badges/tests.svg" alt="18 tests passing">
  <img src="assets/badges/runtime.svg" alt="225 second maximum measured runtime">
  <img src="assets/badges/gpu-cv.svg" alt="116,501 CV images per second">
  <img src="assets/badges/effective-cpu.svg" alt="368.6 effective CPU cores">
  <img src="assets/badges/vast-cost.svg" alt="2.85 dollars conservative Vast campaign estimate">
  <img src="assets/badges/python.svg" alt="Python 3.10 or newer">
</p>

A bounded Python benchmark for comparing Vast.ai Docker offers on the workloads that
matter to Driveline Research: concurrent computer-vision GPU throughput, effective CPU
concurrency, single-thread CPU speed, host memory bandwidth, and disk throughput.

The standard profile has a hard 540-second wall-clock budget. It stores raw results in
SQLite and serves a Driveline-styled leaderboard from the same database.

## Accepted benchmark snapshot

The 2026-08-22 parallel expansion produced **12 accepted results on 12 distinct
machines**, four per target category. Two additional GPU runs were retained as partial
records and excluded because only 6/8 and 3/8 concurrent workers returned. Effective CPU
is measured from the live container's cgroup quota and affinity, so it can be lower than
the Vast listing.

| Category leader | Machine | Actual capacity | Primary result | Runtime |
| --- | --- | ---: | ---: | ---: |
| GPU-heavy | Machine 137275, 8× RTX 4070 Super 12 GB | 76.8 effective CPU cores | **116,501 CV images/s; 579.52 FP16 TFLOP/s** | 166 s |
| Effective CPU | Machine 146110, EPYC 9654 + RTX A2000 | **368.64 effective cores** (384 listed) | **427.82 GB/s multicore SHA-256** | 142 s |
| Fast single CPU | Machine 141094, Core Ultra 9 285K + RTX 5080 | 23.04 effective CPU cores | **5.333 GB/s single-thread SHA-256** | 115 s |

The campaign moved **$1.202** of Vast account credit. The deliberately conservative
elapsed-time ledger estimated **$2.852** for the expansion and **$3.439** across all
repository campaigns, safely below the authorized **$10.00** cap. All rented instances
were destroyed and verified absent. The full four-per-category table and time-scoped
provider failures are in [`reports/2026-08-22-expansion-results.md`](reports/2026-08-22-expansion-results.md).

## What it measures

| Category | Primary measurements |
| --- | --- |
| GPU intensity | Concurrent FP16 GEMM at 2048, 4096, and 6144/8192 matrix sizes |
| GPU CV | Concurrent 224×224 FP16 convolution throughput on every visible GPU |
| GPU concurrency | Aggregate throughput and scaling efficiency versus GPU 0 alone |
| GPU transport | Device copy, host-to-device, device-to-host, utilization, power, temperature |
| CPU | Effective cgroup/affinity cores, SHA-256 single/all-core throughput, Torch matmul |
| Memory | NumPy copy, fill, and scale bandwidth |
| Disk | fsync-backed sequential write and cache-advised sequential read |

`cpu.effective_cores` is the lower of the container's CPU affinity and cgroup CPU quota,
not the host's advertised core count. This captures the capacity the rental can actually
schedule. The benchmark retains the exact fractional quota and rounds worker count up so
fractional capacity is exercised.

## Quick start

```bash
uv sync --extra dev
uv run vast-benchmark run \
  --profile smoke \
  --db results/benchmarks.sqlite \
  --output results/local-smoke.json

uv run vast-benchmark serve \
  --db results/benchmarks.sqlite \
  --host 127.0.0.1 \
  --port 8080
```

Open <http://127.0.0.1:8080>. The health endpoint is `/healthz`, and normalized dashboard
data is available from `/api/runs`.

The dashboard includes an accepted-results leaderboard and an all-run history. The latter
keeps partial and superseded runs visible without allowing them to affect rankings.
Machine ratings and time-scoped provisioning notes are stored locally by Vast machine ID
and exposed on the dashboard and `/api/runs`. Vast's console labels are temporary labels
on a rental instance, not durable annotations on the underlying marketplace machine.

## Production service

The `deploy/` directory contains the Gunicorn systemd unit used on `dc-boddydev` and the
Apache route fragments for `/vast-benchmark/`. The backend listens only on
`127.0.0.1:18100`; Apache supplies the external scheme, host, and path prefix.

Live dashboard: <https://dc-boddydev.drivelinebaseball.com/vast-benchmark/>

## Run in Docker

The image starts from the official PyTorch CUDA 12.8 runtime. The benchmark does not
install or download models.

```bash
docker compose run --rm benchmark
docker compose up dashboard
```

On Vast.ai, an existing PyTorch image can run the source directly without installing web
dependencies:

```bash
PYTHONPATH=/workspace/vast-benchmarking/src \
/venv/main/bin/python -m vast_benchmarking run \
  --profile standard \
  --max-seconds 540 \
  --disk-dir /workspace \
  --output /workspace/vast-result.json
```

## Safe Vast runner

`vast-benchmark-runner` is intended to be invoked from the controller machine. It:

1. Refuses to create a machine if any Vast instance already exists.
2. Re-queries the exact offer and verifies it is rentable and under the hourly cap.
3. Enforces worst-case projected spend against the SQLite rental ledger.
4. Creates one instance, attaches the named public key through the instance API, verifies
   key-only SSH, uploads the source, and runs the benchmark.
5. Downloads and ingests the result.
6. Destroys the exact created instance in a `finally` block and verifies it is absent.

Vast rentals default to a pinned `vastai/pytorch` CUDA 12.9 image because it is
SSH-ready on the marketplace. The standalone Dockerfile remains based on the official
PyTorch CUDA runtime to verify the benchmark also works in a normal container.

Example:

```bash
uv run vast-benchmark-runner --env-file /etc/vastai.env run-offer \
  --offer-id 12345678 \
  --category gpu-heavy \
  --label "8x RTX 5060 Ti" \
  --db results/benchmarks.sqlite \
  --budget 5 \
  --max-hourly 1.2
```

The API key is never copied to a remote host. The account's uploaded public key must
match `~/.ssh/vast_benchmark_ed25519`, or pass another key with `--ssh-key`.

The Vast search API calls the rentable offer identifier `id` in responses but filters it
as `ask_contract_id`. The runner handles that naming mismatch explicitly.

## Parallel campaigns

`vast-benchmark-batch` launches a validated JSON manifest in parallel. Before creating
anything it requires no existing rentals, resolves every offer again, rejects duplicate
machine IDs, verifies CUDA compatibility and hourly price, and checks the combined
worst-case cost against the SQLite rental ledger. Every child has a durable log and an
independent exact-instance cleanup path.

```bash
uv run vast-benchmark-batch \
  --manifest manifests/2026-08-22-parallel-expansion.json \
  --db results/benchmarks.sqlite \
  --results-dir results \
  --project-dir . \
  --budget 10 \
  --max-hourly 1.2
```

A GPU run is accepted only when every visible CUDA device returns its concurrent worker
result. Partial totals remain inspectable but do not enter ratings or leaderboards. To
recheck old portable JSON artifacts against the current acceptance rules:

```bash
uv run python scripts/revalidate_results.py \
  --db results/benchmarks.sqlite \
  --results-dir results
```

Campaign ratings and operational notes can be regenerated from results and batch logs
with `scripts/compile_campaign.py`, or imported directly with:

```bash
uv run vast-benchmark annotate reports/2026-08-22-machine-annotations.json \
  --db results/benchmarks.sqlite
```

## Result model

The JSON artifact is the portable source record. SQLite normalizes runs and metrics for
leaderboards while retaining the complete raw JSON. Relative composite scores are the
geometric mean of each run's percent-of-best values across available categories. Raw
category metrics remain the authoritative comparison.

Disk reads use `POSIX_FADV_DONTNEED` when available, but container and host caching can
still affect results. CPU frequency reported by the Vast marketplace is not used for the
single-thread leaderboard.

## Development

```bash
uv run ruff check src tests
uv run pytest
```

The repository is prepared for a private `drivelineresearch/vast-benchmarking` remote.
Do not commit `/etc/vastai.env`, API credentials, SSH private keys, SQLite databases, or
raw result JSON files.

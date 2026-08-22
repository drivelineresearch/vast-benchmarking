<p align="center">
  <img src="src/vast_benchmarking/static/vast-benchmarking-header-v2.png" alt="Abstract GPU, CPU, memory, and storage throughput artwork" width="100%">
</p>

<h1 align="center">Vast Benchmarking</h1>

<p align="center">
  <strong>Measure the hardware capacity a rented container can actually use.</strong><br>
  GPU concurrency · effective CPU cores · memory bandwidth · durable disk speed
</p>

<p align="center">
  <a href="docs/benchmarks/2026-08-22-demo.md">📊 Demo results</a> ·
  <a href="docs/benchmark-methodology.md">🧪 Methodology</a> ·
  <a href="docs/running-on-vast.md">☁️ Vast.ai runner</a> ·
  <a href="docs/README.md">📚 Documentation</a>
</p>

## 🚀 Overview

Vast Benchmarking is a bounded Python benchmark for comparing Vast.ai Docker offers on
computer-vision GPU throughput, effective CPU concurrency, single-thread CPU speed,
memory throughput, and storage performance.

It produces portable JSON, stores normalized results in SQLite, and serves a Flask
dashboard with category rankings and machine-level notes.

> [!IMPORTANT]
> The standard profile has a hard **540-second wall-clock budget**. Marketplace core
> counts and prices are context; rankings use capacity measured inside the container.

## 📊 Measured demo

The sanitized demo snapshot contains **19 stored runs**, **15 accepted machines**, and
**60 successfully tested GPUs**. Its category leaders include:

- **118,420.80 images/s** of concurrent GPU CV throughput
- **598.504 TFLOP/s** of aggregate FP16 compute
- **368.64 effective CPU cores** measured inside one rental
- **5.333 GB/s** of single-thread SHA-256 throughput

See the [full demo benchmark snapshot](docs/benchmarks/2026-08-22-demo.md) for machine
IDs, exact results, historical rental rates, campaign cost, and acceptance caveats.

## 🧪 Workloads

| Area | What is measured |
| --- | --- |
| GPU | Concurrent FP16 GEMM, synthetic CV convolution, transport, utilization, power, and temperature |
| CPU | Effective cgroup/affinity capacity, single/all-core SHA-256, and Torch matmul |
| Memory | NumPy copy, fill, and scale bandwidth |
| Disk | Fsync-backed sequential writes and cache-advised reads |
| Dashboard | Percent-of-best rankings, historical price context, perf/$ sorting, and durable machine notes |

The detailed contracts and interpretation rules live in
[benchmark methodology](docs/benchmark-methodology.md).

## ⚡ Quick start

```bash
uv sync --extra dev --extra server

uv run vast-benchmark run \
  --profile smoke \
  --db results/benchmarks.sqlite \
  --output results/local-smoke.json

uv run vast-benchmark serve \
  --db results/benchmarks.sqlite \
  --host 127.0.0.1 \
  --port 8080
```

Open <http://127.0.0.1:8080>. Health is available at `/healthz`, and normalized data at
`/api/runs`.

## ☁️ Docker and Vast.ai

```bash
docker compose run --rm benchmark
docker compose up dashboard
```

The controller can validate a single offer or launch a bounded parallel campaign with
hourly-price checks, projected-spend enforcement, key-only SSH, exact-instance cleanup,
and partial-result rejection.

Read [running on Vast.ai](docs/running-on-vast.md) before using paid infrastructure.

> [!NOTE]
> **Referral disclosure:** [Create a Vast.ai account with this referral link](https://cloud.vast.ai/?ref_id=77898).
> If you sign up through it, the project maintainer may receive Vast.ai account credit.
> The referral has no effect on benchmark selection, rankings, methodology, or reported
> prices.

## 🛡️ Safety model

- Provider credentials stay on the controller and are never copied to rented hosts.
- Partial GPU runs and superseded results remain inspectable but do not enter rankings.
- Rental prices are historical observations captured at run time, not current quotes.
- Result databases, raw artifacts, keys, and provider logs are excluded from Git.

See [Security](SECURITY.md) and the [public-release checklist](docs/PUBLIC_RELEASE.md).

## 📚 Documentation

| Guide | Purpose |
| --- | --- |
| [Documentation index](docs/README.md) | Map of user, operator, methodology, and maintainer docs |
| [Demo benchmark snapshot](docs/benchmarks/2026-08-22-demo.md) | Measured leaders, rates, costs, and caveats |
| [Benchmark methodology](docs/benchmark-methodology.md) | Workloads, effective cores, acceptance, and scoring |
| [Running on Vast.ai](docs/running-on-vast.md) | Single-offer and parallel campaign operation |
| [Self-hosting](docs/self-hosting.md) | Generic Flask, Gunicorn, and reverse-proxy deployment |
| [Contributing](CONTRIBUTING.md) | Development and pull-request expectations |

## 🧰 Development

```bash
uv run ruff check src tests scripts
uv run pytest
node --check src/vast_benchmarking/static/app.js
uv run python scripts/check_markdown_links.py
uv run python scripts/check_public_release.py
uv build
uv run python scripts/check_distribution.py
```

## 📦 Releases

Versioned wheels, source archives, and checksums are published through
[GitHub Releases](https://github.com/drivelineresearch/vast-benchmarking/releases).
PyTorch remains an environment dependency supplied by the CUDA container.

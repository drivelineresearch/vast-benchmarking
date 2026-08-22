# Running on Vast.ai

The controller rents an exact Vast.ai offer, waits for CUDA-capable SSH, uploads the
project, runs the bounded benchmark, downloads the result, records it in SQLite, and
destroys only the instance it created.

> [!WARNING]
> These commands can spend real money. Set an explicit budget that has been authorized
> for the campaign. The runner's budget is a safety ceiling, not spending permission.

## Controller setup

Install the package and create an SSH key dedicated to disposable benchmark hosts:

```bash
uv sync --extra dev --extra server
ssh-keygen -t ed25519 -f ~/.ssh/vast_benchmark_ed25519 -C vast-benchmark
```

Store the provider credential outside the repository. The default location is
`/etc/vastai.env`:

```dotenv
VAST_API_KEY=
```

Restrict that file to the account that runs the controller. The API key and private SSH
key never leave the controller. Only the public key is attached to a rental. Put the real
API key after the equals sign in the protected controller file.

## Benchmark one offer

Resolve an offer ID immediately before running it, then use a descriptive category and
label:

```bash
uv run vast-benchmark-runner run-offer \
  --offer-id 12345678 \
  --category gpu-heavy \
  --label "8x example GPU" \
  --budget 1.00 \
  --max-hourly 1.20 \
  --max-instance-minutes 30
```

The offer ID identifies a rentable listing. The machine ID identifies the underlying
host and is stored separately in the result. Do not substitute one identifier for the
other.

## Run a bounded parallel campaign

A manifest contains only offer IDs, categories, and public labels. Start from one of the
sanitized examples in `manifests/`:

```bash
uv run vast-benchmark-batch \
  --manifest manifests/example.json \
  --budget 5.00 \
  --max-hourly 1.20 \
  --max-instance-minutes 30 \
  --profile standard
```

Before each launch, the runner checks that the offer is still rentable and within the
hourly price and CUDA limits. It also checks the rental ledger against the projected
maximum cost. Parallel workers stagger their API calls to avoid provider throttling.

## Safety sequence

1. Refuse unapproved or over-budget work before creating an instance.
2. Re-resolve the offer and verify its current hourly rate.
3. Attach only the dedicated public SSH key.
4. Enforce provisioning, SSH, benchmark, and maximum-rental deadlines.
5. Download and validate the result before ranking it.
6. Destroy the exact created instance in `finally`, then verify it is absent.

By default, the single-offer runner refuses to create a rental while another Vast
instance exists. `--allow-existing-instances` exists for controlled batch orchestration;
do not use it casually.

## Revalidate and compile

Re-ingest downloaded JSON after an acceptance-rule change:

```bash
uv run python scripts/revalidate_results.py \
  --db results/benchmarks.sqlite \
  --results-dir results
```

Compile a dated campaign report and annotation export:

```bash
uv run python scripts/compile_campaign.py \
  --db results/benchmarks.sqlite \
  --since 2026-08-22T00:00:00+00:00 \
  --batches-root results/batches \
  --annotations-output results/machine-annotations.json \
  --report-output results/campaign-report.md
```

Raw result JSON, SQLite databases, provider logs, and credentials belong under ignored
local paths. Publish only reviewed, sanitized summaries.

## Image assumptions

The default image is pinned in the source. It needs CUDA-capable PyTorch, a working
Python environment, `nvidia-smi`, SSH, and enough disk for the benchmark. If a host's
CUDA ceiling is below the image requirement, record it as incompatible rather than as a
failed performance result.

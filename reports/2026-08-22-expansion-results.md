# Vast benchmark expansion results

Generated: 2026-08-22T09:40:56.424850+00:00

- Accepted campaign runs: **12**
- Partial campaign runs excluded from ratings: **2**
- Estimated campaign rental cost: **$2.85**
- Attempted machines with no accepted result: **21**
- Ratings are campaign-local percent-of-best grades: S >=95%, A >=80%, B >=65%, C >=50%, D <50%.

## gpu-heavy

| Rank | Grade | Machine | Label | Primary result | Effective cores | Rate |
|---:|:---:|---:|---|---:|---:|---:|
| 1 | S | 137275 | 8x RTX 4070 Super 12GB / Xeon E5-2673 v4 | 116501.113 images/s | 76.8 | $0.698/hr |
| 2 | B | 59149 | 8x RTX 5060 Ti 16GB / EPYC 7742 | 77161.670 images/s | 122.87999 | $0.862/hr |
| 3 | D | 143986 | 8x RTX 4060 8GB / EPYC 7502 | 55817.190 images/s | 61.43999 | $0.428/hr |
| 4 | D | 28477 | 8x RTX 3060 12GB / Xeon E5-2682 v4 | 51321.488 images/s | 61.43999 | $0.432/hr |

## high-effective-cpu

| Rank | Grade | Machine | Label | Primary result | Effective cores | Rate |
|---:|:---:|---:|---|---:|---:|---:|
| 1 | S | 146110 | 384 listed effective cores / EPYC 9654 / RTX A2000 | 427.820 GB/s | 368.64001 | $0.939/hr |
| 2 | B | 25247 | 384 listed effective cores / EPYC 9654 / RTX 5060 Ti | 301.460 GB/s | 368.64001 | $0.830/hr |
| 3 | D | 34698 | 128 listed effective cores / EPYC 7C13 / 4x Tesla V100 | 154.915 GB/s | 122.87999 | $0.749/hr |
| 4 | D | 145482 | 128 listed effective cores / EPYC 7702 / RTX 3060 Ti | 139.934 GB/s | 122.87999 | $0.336/hr |

## fast-single-cpu

| Rank | Grade | Machine | Label | Primary result | Effective cores | Rate |
|---:|:---:|---:|---|---:|---:|---:|
| 1 | S | 141094 | Core Ultra 9 285K / RTX 5080 | 5.333 GB/s | 23.04 | $0.301/hr |
| 2 | C | 55801 | Core i9-14900K / RTX 5060 | 2.885 GB/s | 30.72 | $0.141/hr |
| 3 | C | 35039 | Ryzen 9 9950X / RTX 4080 | 2.775 GB/s | 30.71999 | $0.271/hr |
| 4 | D | 108455 | Ryzen 9 9950X3D / RTX 3060 | 2.120 GB/s | 30.71999 | $0.154/hr |

## Failed and incompatible attempts

| Machine | Category | Disposition | Tags | Note |
|---:|---|---|---|---|
| 14364 | gpu-heavy | incompatible | cuda-12.8, image-requires-12.9 | Host CUDA ceiling was 12.8; the CUDA 12.9 benchmark image produced PyTorch error 804. Rental was stopped without rating the hardware. |
| 31412 | gpu-heavy | partial | gpu-heavy, benchmark-partial, incomplete-result | Only 3/8 visible GPUs returned concurrent benchmark data; aggregate GPU totals are excluded from leaderboards. |
| 37271 | gpu-heavy | incompatible | cuda-12.8, image-requires-12.9 | Host CUDA ceiling was 12.8, below the benchmark image runtime requirement; rental was stopped before benchmarking. |
| 42085 | high-effective-cpu | known-bad | ssh-unavailable | Machine reached running state during the 2026-08-22 attempt but never exposed usable SSH within 480 seconds. |
| 49927 | gpu-heavy | inconclusive | api-rate-limit | Vast API throttled orchestration during the 2026-08-22 campaign; the machine itself was not evaluated. |
| 52572 | gpu-heavy | inconclusive | api-rate-limit | Vast API throttled orchestration during the 2026-08-22 campaign; the machine itself was not evaluated. |
| 58964 | fast-single-cpu | known-bad | ssh-unavailable | Machine reached running state during the 2026-08-22 attempt but never exposed usable SSH within 480 seconds. |
| 59070 | gpu-heavy | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |
| 62158 | high-effective-cpu | known-bad | ssh-unavailable | Machine reached running state during the 2026-08-22 attempt but never exposed usable SSH within 480 seconds. |
| 68203 | gpu-heavy | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |
| 68507 | high-effective-cpu | known-bad | ssh-unavailable | Machine reached running state during the 2026-08-22 attempt but never exposed usable SSH within 480 seconds. |
| 137456 | gpu-heavy | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |
| 137785 | fast-single-cpu | known-bad | ssh-unavailable | Machine reached running state during the 2026-08-22 attempt but never exposed usable SSH within 480 seconds. |
| 138008 | high-effective-cpu | inconclusive | api-rate-limit | Vast API throttled orchestration during the 2026-08-22 campaign; the machine itself was not evaluated. |
| 139658 | high-effective-cpu | known-bad | offline | Machine went offline during the 2026-08-22 provisioning attempt; no performance result was accepted. |
| 141127 | gpu-heavy | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |
| 141176 | gpu-heavy | partial | gpu-heavy, benchmark-partial, incomplete-result | Only 6/8 visible GPUs returned concurrent benchmark data; aggregate GPU totals are excluded from leaderboards. |
| 141626 | gpu-heavy | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |
| 145496 | high-effective-cpu | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |
| 145504 | gpu-heavy | inconclusive | redundant-hedge, canceled-before-benchmark | A redundant hedge rental was canceled while still provisioning after another machine completed the required 8/8-GPU result; this machine was not evaluated. |
| 147067 | gpu-heavy | known-bad | provisioning-timeout | Machine did not finish container provisioning within the 15-minute limit during the 2026-08-22 campaign. |

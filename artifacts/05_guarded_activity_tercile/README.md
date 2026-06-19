# Guarded-era activity-tercile conditional-predictability map (measure-only)

Cross-era replication of the validation-era conditional-predictability map
(register C3.4 / review blocker #1) on the **2017-2024 guarded walk-forward era**.
The validation map (Stage 03/04) lived only on 2013-2017; this packet measures the
SAME per-(ticker, trading_day) eligible-row-count activity proxy on the guarded
era, so the headline conditional claim is no longer single-era.

## How this was produced
Local, deterministic, measure-only re-aggregation of the frozen V2.1 prediction
dumps through the shipped + unit-tested `synthesis.build_guarded_activity_tercile`
(activity proxy reused verbatim from `diagnostics.activity_terciles`; a vectorized
twin was asserted equal on a sample before the full run). No fit, no scoring.
Provenance is the sha256 chain (code + input dumps), not a Colab run id.

## The result (TCN primary, seed-mean delta vs same-row stratified dummy)
| activity tercile | guarded delta vs dummy | macro-F1 | validation-era (C3.4) |
|---|---|---|---|
| all  | +0.0064 | 0.5072 | +0.0169 |
| low  | +0.0408 | 0.5423 | +0.0543 |
| mid  | +0.0056 | 0.5059 | +0.0191 |
| high | -0.0210 | 0.4797 (below random prior 0.5: True) | -0.0154 (0.483) |

Read against the validation-era map: this is the direct cross-era check a reviewer
asks for. Interpret descriptively only; the activity proxy is a per-day eligible-row
count (no-trade-band proxy), NOT realized volume/liquidity (register F1).

## Files
| file | what it is |
|---|---|
| `05_guarded_activity_tercile.csv` | per (activity_tercile x seed) + seed-mean: macro-F1, dummy macro-F1, delta, below-random flag |
| `guarded_activity_tercile_manifest.json` | code/input sha256, source run id, seed-mean summary, measure-only flags |

## Verify
```bash
sha256sum -c SHA256SUMS.txt
```

# Row-pooled (binding-estimand) multiplicity discount (measure-only)

Recompute of the B6 multiplicity discount on the **binding row-pooled estimand**
(register / review blocker #2). The shipped Stage 05 `05_multiplicity_discount.csv`
runs on the equal-weight companion (TCN mean_delta 0.005495); this packet centers
the discount on the row-pooled-over-all-rows pooled_delta the C4 headline cites.

## How this was produced
Local, deterministic, measure-only re-aggregation of the frozen V2.1 prediction
dumps through the shipped + unit-tested
`synthesis.build_row_pooled_multiplicity_discount`. Each (family, period) cell is the
row-pooled-within-period macro-F1 delta; each family's central mean_delta is the
row-pooled-over-ALL-rows binding estimand; PBO is CSCV (Bailey et al. 2017) over the
row-pooled block matrix. No fit, no scoring. Provenance is the sha256 chain.

## The result
TCN primary row-pooled central mean_delta = **+0.006362**
(reproduces pooled_delta_row_pooled 0.006362: True).

| family | row-pooled mean_delta (binding) | period-block LCB | positive periods |
|---|---|---|---|
| lightgbm_family_best | +0.007263 | -0.000297 | 5/7 |
| ms_dlinear_tcn_family_best | +0.006724 | -0.000249 | 6/7 |
| standard_dlinear_family_best | +0.005128 | -0.004645 | 4/7 |
| tcn_frozen_primary | +0.006362 | +0.000470 | 5/7 |

Summary: PBO = 0.5143 (cscv_odd_block_floor_ceil_adaptation); min_family_lcb =
-0.004645; median_family_lcb = -0.000273;
max_family_mean = +0.007263. Descriptive multiplicity/overfitting
discount only -- never a significance claim. Contrast directly with the equal-weight
`05_multiplicity_discount.csv` (same schema).

## Files
| file | what it is |
|---|---|
| `05_row_pooled_multiplicity.csv` | per-family (row-pooled central + block LCB + positive periods) + summary (min/median LCB, max mean, PBO) |
| `row_pooled_multiplicity_manifest.json` | code/input sha256, source run id, PBO + family aggregates, binding-reproduction flag |

## Verify
```bash
sha256sum -c SHA256SUMS.txt
```

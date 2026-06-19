# Row-pooled LOO of the binding guarded estimand (measure-only)

In-repo mirror of the **row-pooled leave-one-out** robustness of the binding
guarded `pooled_delta` (protocol §8 row union) — the one item the Stage 05
`05_loo_robustness.csv` marks `<deferred>`, because macro-F1 is **non-linear
across rows** and so the true row-pooled LOO cannot be derived from the small
per-period/per-ticker aggregates. It must recompute pooled macro-F1 from the
row-level prediction dumps.

## How this was produced (read before trusting)
Unlike the Stage 05 run artifacts (which come from provenanced Colab runs), this
is a **local, deterministic, measure-only re-aggregation** of the frozen V2.1
prediction dumps, computed through the shipped + unit-tested
`synthesis.build_row_pooled_loo`. It is reproducible by anyone: read the two
frozen dumps (sha256 below), filter to the primary model, and call the function.
No fit, no scoring, no randomness — `new_scoring_events=0`,
`no_final_model_selected=true`.

Provenance is the sha256 chain, not a Colab run id:
- code: `row_pooled_loo_code_sha256` in `row_pooled_loo_manifest.json`
  (inspect-hash of `build_row_pooled_loo` + `_row_pooled_seed_mean_delta` +
  `binary_macro_f1`); git_commit `ba77d3b`.
- inputs: `v2_1_predictions.csv` sha256 `6481f79…` (569 MB) +
  `v2_1_baseline_predictions.csv` sha256 `cd6925e…` (117 MB), both **verified
  against the V2.1 run `20260618_063559_889276` artifact_inventory** (the frozen
  record) and against the local Drive copy. The 656 MB dumps stay Drive-only
  (route guide §11); only this small derived table is mirrored.

## The result
The no-drop baseline **reproduces the native `pooled_delta_row_pooled` = 0.006362
exactly** — confirming the recompute matches `guarded_walkforward._row_pooled_pooled_delta`.
Both sweeps survive every single-slice drop (`loo_sign_flip=False`):

| sweep | worst-case drop | worst delta | baseline |
|---|---|---|---|
| row_pooled_over_periods | wf_p2 | +0.54pp | +0.64pp |
| row_pooled_over_tickers | CSCO | +0.51pp | +0.64pp |

So the **binding** estimand (the one C4 cites) does not hinge on any single
walk-forward period or ticker — the same conclusion the equal-weight LOO reached,
now on the binding row-pooled estimand. Descriptive robustness only — the
bootstrap-free LOO is a sensitivity check, never a significance test.

## Files
| file | what it is |
|---|---|
| `05_row_pooled_loo.csv` | row-pooled LOO-period (7) + LOO-ticker (5) + per-sweep summary (`LOO_ROBUSTNESS_COLUMNS` schema) |
| `row_pooled_loo_manifest.json` | code/input sha256, source run id, baseline-reproduction + sign-flip flags, measure-only flags |

## Verify
```bash
sha256sum -c SHA256SUMS.txt          # this packet
# and to reproduce the numbers from the frozen dumps:
#   python -c "import sys; sys.path.insert(0,'src'); import pandas as pd; from lst_models import synthesis; \
#     p=pd.read_csv('<drive>/v2_1_predictions.csv'); b=pd.read_csv('<drive>/v2_1_baseline_predictions.csv'); \
#     b=b[b.baseline_id=='stratified_dummy_train_prior']; \
#     print(synthesis.build_row_pooled_loo(p,b,primary_model='tcn_frozen_primary',expected_period_count=7,expected_ticker_count=5))"
```

# 00 Data Split Label Freeze Protocol

Status: draft protocol.

Scope: V2 `lst_models` route only. This document freezes the Stage 00
contract for raw-data provenance, chronological split boundaries, label
construction, baseline policy, and Stage 01 handoff. It does not run model
selection, feature search, window search, HPO, validation readout, or
holdout/test analysis.

## 1. Stage Boundary

Stage 00 answers:

- Which raw ticker files are authoritative.
- How raw 1-minute rows become canonical 5-minute bars.
- Which calendar intervals are train, official validation, and closed
  holdout/test.
- How supervised labels are built and invalidated.
- Which trivial baselines must exist by name.
- Which frozen artifacts Stage 01 must consume.

Stage 00 does not answer:

- Which feature set is best.
- Which window size is best.
- Which model family is best.
- Which hyperparameters are best.
- Whether validation or holdout/test performance supports a thesis claim.

Stage 01 owns feature/window initial screening around the target model surface.
Stage 01 must consume the Stage 00 split and label artifacts as frozen inputs;
it must not relabel, resplit, change no-trade bands, or introduce additional
label operators.

## 2. Research Question Boundary

The V2 route asks whether five-ticker, 5-minute OHLCV-derived features can
support an honest directional classifier that beats trivial same-row baselines
under chronological validation.

The Stage 00 unit of prediction is:

```text
one ticker
one completed 5-minute target bar t
one future label horizon h measured in 5-minute bars
one binary direction label if the future move is outside the no-trade band
```

The target rows are binary supervised rows only. Rows inside the no-trade band
are invalid label rows, not a third class and not missing values to impute.

## 3. Authoritative Raw Data

The raw source is the Google Drive folder and file-ID manifest documented in:

```text
configs/lst_models_data.yaml
docs/lst_models_google_drive_raw_data_guide.md
```

The ticker universe is fixed for V2 Stage 00:

```text
CSCO, JPM, KO, MSFT, WMT
```

Required raw input columns:

```text
Date, Time, Open, High, Low, Close, Volume
```

Parsing policy:

```text
date_format = %m/%d/%Y
time_format = %H:%M
timezone = source-local market timestamps; do not infer UTC conversion
regular_session = 09:30 through 16:00
```

Raw data must be downloaded by file ID into the Colab runtime. New notebooks
must not discover raw data by scanning mounted Drive folders, Drive shortcuts,
old project folders, or machine-local Windows paths.

## 4. Canonical 1-Minute To 5-Minute Bars

The 5-minute bar recipe is fixed by `configs/lst_models_data.yaml`:

```text
input_frequency  = 1min
output_frequency = 5min
resample_rule    = 5min
open             = first
high             = max
low              = min
close            = last
volume           = sum
drop_na_subset   = open, high, low, close, volume
output_columns   = ticker, timestamp, open, high, low, close, volume
```

Apply regular-session filtering before and after resampling. Sort all bars by
`(ticker, timestamp)` before split, feature, label, and window construction.
If raw files contain a `16:00` row, it may be used as raw session input but the
resampled output must exclude the partial `16:00` 5-minute bucket. The final
full 5-minute target bar in a regular session is labeled `15:55`.

## 5. Chronological Split Freeze

The V2 split is calendar-based and chronological. Random splits, shuffled
validation, stratified row splits, and `train_test_split`-style time-series
splits are forbidden.

```text
train:
  start inclusive = 1998-01-02
  end exclusive   = 2013-09-16

official_validation:
  start inclusive = 2013-09-16
  end exclusive   = 2017-01-25

closed_holdout_test:
  start inclusive = 2017-01-25
```

Validation-only stages may use `2017-01-25` only as the closed holdout/test
boundary marker. They must not read, transform, window, score, summarize, or
otherwise use bars at or after that boundary.

Train-inner folds used by later stages must be derived inside the train
interval only. The official validation interval is a readout interval, not a
feature/window/model/HPO selection source.

## 6. Label Operator Freeze

The only approved V2 Stage 00 label operator is:

```text
endpoint_cumulative_return
```

For each ticker independently, after sorting canonical 5-minute bars by
timestamp:

```text
r_h(t) = close[t + h] / close[t] - 1
theta  = no_trade_band_bps / 10000

label = 1  if r_h(t) >  theta
label = 0  if r_h(t) < -theta
label = invalid_no_trade_band otherwise
```

`h` and `no_trade_band_bps` are numeric Stage 00 config values. They must be
fixed before Stage 01 starts. Stage 01 may not search label horizons,
thresholds, or alternate label formulas.

A future-average or DeepLOB-style smoothed label is an excluded alternative for
this V2 route unless a new protocol revision explicitly replaces this section
before any Stage 01 feature/window result is inspected.

## 7. Label Invalidation Rules

Each label row must carry explicit validity flags. A row is not eligible for
model training or evaluation if any of these conditions is true:

```text
invalid_missing_future:
  close[t + h] does not exist for the same ticker.

invalid_cross_trading_day:
  any bar from t through t + h leaves the target trading day.

invalid_irregular_horizon:
  timestamp[t + h] - timestamp[t] != h * 5 minutes while the row is otherwise
  same-day.

invalid_cross_split:
  t and t + h do not belong to the same split.

invalid_no_trade_band:
  abs(r_h(t)) <= theta.
```

Invalid labels are markers. Do not fill them. Do not globally drop them before
split-boundary, trading-day, event-horizon, and window-validity checks have run.

## 8. Event Interval Contract

Every eligible target row has an event interval:

```text
event_start = target_timestamp
event_end   = horizon_end_timestamp = timestamp[t + h]
```

Later train-inner fold builders must prove that no train event interval
overlaps the corresponding validation event interval for the same ticker and
trading day. `TimeSeriesSplit`-style chronological ordering is not sufficient
by itself because it does not know ticker ownership, trading-day boundaries, or
future label horizons.

## 9. Window Validity Rules

Stage 00 does not choose a window size. It freezes the rules that Stage 01 must
use for every tested window size:

- Build windows per ticker only.
- Build windows per split only.
- Build windows per trading day only.
- No window may cross tickers.
- No window may cross a split boundary.
- No window may cross a trading-day boundary.
- The target row of a window must have a valid binary label.
- All feature rows inside the window must be finite after train-only
  preprocessing.

For tabular controls, a flattened window is still a window and must satisfy the
same ownership and boundary rules.

## 10. Train-Only Preprocessing Rule

Any preprocessing step that learns statistics must fit on train rows only.
Examples include scaling, imputation, normalization, PCA, feature selection,
target encoding, calibration, and threshold selection.

For pooled five-ticker runs:

1. Split each ticker chronologically.
2. Collect eligible train rows only.
3. Fit shared preprocessing statistics on pooled train rows.
4. Transform train and official validation with the fitted object.
5. Do not fit or refit on official validation or closed holdout/test.

## 11. Baseline Registry

Stage 00 freezes mandatory trivial baseline names and behavior. It does not run
model selection.

| baseline_id | behavior | fit source | tuning |
|---|---|---|---|
| `stratified_dummy_train_prior` | sample predictions from the empirical train label prior | train or train-inner labels only | fixed seed list only |
| `majority_train_prior` | always predict the most frequent train label | train or train-inner labels only | none |
| `constant_up` | always predict `1` | no learned statistics | none |
| `constant_down` | always predict `0` | no learned statistics | none |

Every model/control comparison in later stages must include same-row baseline
metrics on exactly the same target sample IDs. Required comparison fields:

```text
sample_id_hash
macro_f1
balanced_accuracy
accuracy
baseline_macro_f1
baseline_balanced_accuracy
delta_macro_f1_vs_baseline
delta_balanced_accuracy_vs_baseline
```

`LightGBM`, `last_step_mlp`, `dlinear_only`, `tcn_only`, and hybrid sequence
models are controls or candidate models, not trivial baselines.

## 12. Forbidden Operations

Stage 00 and downstream validation-only stages must not:

- read or summarize closed holdout/test rows;
- choose split boundaries from model results;
- choose label horizon or no-trade band from official validation or holdout/test;
- treat no-trade rows as a third supervised class unless a new protocol is
  approved before Stage 01;
- fill invalid labels;
- use random or shuffled time-series splits;
- fit preprocessing on validation or holdout/test rows;
- build windows across tickers, split boundaries, or trading days;
- compare model rows without same-row trivial baselines;
- claim profitability, Sharpe, transaction-cost robustness, or deployment
  readiness from this classification protocol.

## 13. Stage 00 Output Artifacts

An executed Stage 00 run should write a compact artifact set.

Canonical result locations:

```text
Colab runtime: /content/lst_models_results/00_data_split_label_freeze/<run_id>/
Drive backup:  My Drive/lst_models/results/00_data_split_label_freeze/<run_id>/
Repo-relative: results/00_data_split_label_freeze/<run_id>/
```

```text
results/00_data_split_label_freeze/<run_id>/
  run_manifest.json
  artifact_inventory.csv
  raw_data_manifest.json
  split_freeze.json
  label_policy.json
  baseline_registry.json
  label_validity_summary.csv
  sample_event_index.csv
```

`artifact_inventory.csv` must be portable. It must not expose a single
runtime-only absolute `path` column as the artifact locator. Required columns:

```text
artifact_name
file_name
relative_path
original_runtime_path
exists
bytes
sha256
```

Consumers must locate files as `run_folder / relative_path`.
`original_runtime_path` is provenance only and may still point at the original
Colab runtime after the run folder is copied to Drive.

Minimum `run_manifest.json` fields:

```text
route
stage_name
scope
config_sha256
notebook_sha256
input_artifacts
output_artifacts
holdout_test_contact = false
```

Minimum `sample_event_index.csv` columns:

```text
sample_id
ticker
target_timestamp
trading_day
split
horizon_k
horizon_end_timestamp
label
future_cumulative_return
valid_label
invalid_missing_future
invalid_cross_trading_day
invalid_irregular_horizon
invalid_cross_split
invalid_no_trade_band
```

Rows from the closed holdout/test interval must not appear in validation-only
Stage 00 artifacts.

## 14. Acceptance Tests To Keep In GitHub

Keep a small safety suite. Do not remove all tests from GitHub.

Required fast tests:

- raw manifest contains exactly the five approved tickers and Drive file IDs;
- raw schema errors include the exact missing path or bad column;
- 1-minute to 5-minute recipe preserves the documented output columns;
- split assignment is chronological and boundary-exclusive as specified;
- bars at or after `2017-01-25` are excluded from validation-only artifacts;
- `endpoint_cumulative_return` formula matches hand-calculated examples;
- no-trade band invalidates `abs(r_h) <= theta`;
- label horizon crossing a trading day is invalid;
- label horizon crossing a split boundary is invalid;
- event intervals do not overlap across train-inner fold boundaries;
- windows do not cross ticker, split, or trading-day boundaries;
- preprocessing fit methods receive train rows only;
- mandatory baseline IDs exist and same-row `sample_id_hash` is enforced;
- validation-only notebooks contain no active holdout/test read strings;
- run manifest records `holdout_test_contact=false`.

Heavy notebook execution, full HPO, GPU training, and large real-data
regeneration may stay local-only or slow-CI. The GitHub-visible tests must keep
the chronology, leakage, label, baseline, and manifest contract intact.

## 15. Handoff Contract To Stage 01

Stage 01 may start only when these Stage 00 items exist:

- approved Stage 00 protocol;
- Stage 00 config with exactly one primary label config for the active route;
- frozen split artifact;
- frozen label policy artifact;
- sample event index or equivalent reproducible builder;
- raw manifest reference;
- baseline registry;
- run manifest with `holdout_test_contact=false`.

Stage 01 may search:

```text
feature_set
window_size
lightweight train-inner shape/signal checks
```

Stage 01 may not search:

```text
label operator
horizon_k
no_trade_band_bps
calendar split boundaries
holdout/test wording
```

If Stage 01 discovers that the frozen label config creates empty train or
validation rows, it must stop and report the failure. It must not silently
change the label horizon, no-trade band, or split.

## 16. Evidence Basis

This protocol uses local project evidence from the previous V1 notebooks only
as implementation background for the label and split mechanics. It does not
inherit V1 validation results as V2 selection evidence.

External method anchors:

- scikit-learn `DummyClassifier`: official reference for `stratified`,
  `most_frequent`, and `constant` simple baselines.
  https://scikit-learn.org/dev/modules/generated/sklearn.dummy.DummyClassifier.html
- scikit-learn common pitfalls: split before learned preprocessing, and fit
  learned transforms on train only.
  https://scikit-learn.org/stable/common_pitfalls.html
- scikit-learn `TimeSeriesSplit`: useful chronological-split reference, but
  insufficient alone for ticker/day/horizon guards.
  https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- DeepLOB and FI-2010: context for high-frequency thresholded movement labels;
  not evidence that a smoothed LOB label or LOB model should replace the V2
  five-minute OHLCV protocol.
  https://arxiv.org/abs/1808.03668
  https://arxiv.org/abs/1705.03233
- Cawley and Talbot (2010): model-selection overfitting and selection-bias
  caution for repeated selection on finite validation evidence.
  https://jmlr.org/papers/v11/cawley10a.html

## 17. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- the target notebook or module

The implementation MUST preserve:

- Colab-first execution
- one `run_stage(config)` per executable stage
- small Python helpers, no framework expansion
- validation-only scope unless explicitly authorized
- no holdout/test read, transform, window, score, or summary
- train-only preprocessing
- dummy baseline comparison where model metrics are reported
- run manifest with `holdout_test_contact=false`
- notebook static-gate compatibility

# 01 Feature Window Search Protocol

Status: draft protocol.

Scope: V2 `lst_models` route only. This document defines Stage 01 feature-set
and window-size screening. Stage 01 is not final model selection, not formal
HPO, and not official-validation readout.

## 1. Stage Boundary

Stage 01 answers:

- Which predeclared feature-set candidates are viable under the frozen Stage 00
  label and split contract.
- Which compact window-size candidates have usable sample counts and lightweight
  train-inner signal.
- Which small set of model families should proceed to Stage 02 train-inner HPO.
- Whether the frozen Stage 00 inputs are too sparse, invalid, or unstable for a
  credible Stage 02 run.

Stage 01 does not answer:

- Which final model wins.
- Which final hyperparameters should be used.
- Whether official validation, test, or holdout performance supports a thesis
  claim.
- Whether the label horizon, no-trade band, split boundary, or target definition
  should change.

Direct answer to the route question:

```text
Stage 01 does not determine the final model. It only performs feature/window
screening and produces a model-family shortlist for Stage 02.
```

## 2. Required Stage 00 Inputs

Stage 01 may start only after Stage 00 has frozen and exported:

- `raw_data_manifest.json`
- `split_freeze.json`
- `label_policy.json`
- `baseline_registry.json`
- `sample_event_index.csv` or an equivalent reproducible event-index builder
- `run_manifest.json` with `holdout_test_contact=false`

Stage 01 must consume the Stage 00 split and label artifacts as frozen inputs.
It must not relabel rows, resplit calendars, search no-trade bands, change
`horizon_k`, or introduce an alternate label operator.

The Stage 00 input must be an exact frozen run folder, not the parent stage
folder and not a path copied from a Colab-only inventory column. Consumers must
resolve Stage 00 files as:

```text
stage00_run_folder / <required_file_name>
```

The Stage 01 config must freeze the exact Stage 00 run:

```text
stage00_run_id
stage00_runtime_run_dir
stage00_drive_path_parts
stage00_run_manifest
```

In Colab, the Stage 01 notebook may copy missing Stage 00 artifacts from Google
Drive into `stage00_runtime_run_dir`, but only by resolving the exact Drive path
parts. It must not scan for the latest run, use a stale `/content/...` path from
`artifact_inventory.csv`, or require a manual zip upload for Stage 00 results.

If `artifact_inventory.csv` is used, Stage 01 may use `relative_path`,
`file_name`, `bytes`, and `sha256` for verification. It must not use
`original_runtime_path` as the input locator after the run is backed up to Drive
or copied to another machine.

If any required Stage 00 artifact is missing, Stage 01 must raise an exact-path
error. If the frozen label config yields empty train-inner folds, Stage 01 must
stop and report the failure instead of changing the label or split.

## 3. Research Question

The Stage 01 research question is:

```text
Given the frozen V2 label/split contract, do a small number of normalized
feature sets and input window sizes produce enough train-inner signal and
sample support to justify formal Stage 02 HPO?
```

The unit of screening is:

```text
feature_set x window_size x lightweight_probe x train_inner_fold x seed
```

All screening metrics are train-inner metrics. Official validation and closed
holdout/test rows are not eligible for any feature, window, or model-family
decision in this stage.

## 4. Search Axes

### 4.1 Feature Sets

Stage 01 may search only feature sets that are declared in the Stage 01 config
before any run starts. The preferred V2 feature families are normalized and
decision-time-safe:

```text
price_action_core:
  log_return
  close_to_open_return
  high_low_range
  rolling_volatility_20

technical_price:
  log_return
  high_low_range
  rolling_volatility_20
  rsi_14
  bollinger_pctb
  normalized_macd_hist

price_volume_time:
  log_return
  close_to_open_return
  high_low_range
  rolling_volatility_20
  normalized_volume_20
  rsi_14
  bollinger_pctb
  normalized_macd_hist
  time_of_day_sin
  time_of_day_cos
```

Forbidden Stage 01 feature behavior:

- raw OHLCV levels as model features;
- raw volume without a prior-only normalization rule;
- raw MACD without scale normalization;
- features that need future bars;
- features whose learned statistics are fit on validation or holdout/test rows.

Feature construction must preserve the Stage 00 sample-event contract. A row is
screening-eligible only if its label is valid, its feature row is finite, and
its window satisfies per-ticker, per-day, and per-split ownership rules.

### 4.2 Window Sizes

The preferred V2 Stage 01 window grid is:

```text
window_size: 10, 20, 30
```

For 5-minute bars, these correspond to roughly 50, 100, and 150 minutes of
history. This is a compact grid: it includes the longer `30`-bar window suggested
by historical diagnostics while avoiding a dense multiple-comparison sweep.

Window rules:

- build windows per ticker only;
- build windows per trading day only;
- build windows per split only;
- no window may cross a split boundary;
- no window may cross a trading-day boundary;
- tabular controls that flatten windows must use the same sample IDs as sequence
  probes.

Stage 01 must report sample-count loss by feature set and window size. If
`window_size=30` materially reduces eligible early-day rows, that loss is a
documented tradeoff, not a reason to silently change the window grid.

### 4.3 Label Policy

Stage 01 may not search label policy. It inherits exactly one active Stage 00
label config, expected for the current V2 route to be:

```text
label_operator: endpoint_cumulative_return
horizon_k: frozen by Stage 00
no_trade_band_bps: frozen by Stage 00
```

If Stage 00 later predeclares a limited label-policy branch before Stage 01
starts, that branch must be documented in the Stage 00 protocol first. Otherwise
label policy is outside Stage 01 scope.

## 5. Lightweight Probe Models

Stage 01 probes are controls for input shape and signal robustness. They are not
final model winners and are not formal HPO runs.

Mandatory trivial baselines:

| probe_id | role |
|---|---|
| `stratified_dummy_train_prior` | same-row train-prior dummy baseline |
| `majority_train_prior` | same-row majority-class baseline |

Recommended lightweight probes:

| probe_id | Stage 01 role | Fixed defaults |
|---|---|---|
| `logreg_flat_control` | cheap linear sanity check on flattened windows | `solver=liblinear`, `class_weight=balanced`, `max_iter=2000` |
| `lightgbm_small` | tabular non-linear probe and last-step/window control | `n_estimators=200`, `learning_rate=0.03`, `max_depth=6`, `num_leaves=31`, `subsample=0.9`, `colsample_bytree=0.9`, `class_weight=balanced` |
| `standard_dlinear_tiny` | simple sequence linear probe aligned to the standard DLinear baseline | fixed tiny architecture, no HPO |
| `tcn_tiny` | causal convolution sequence probe | `channels=(32,32)`, `kernel_size=3`, `dropout=0.10` |
| `ms_dlinear_tcn_tiny` | Ian-aligned hybrid shape/signal probe | fixed multi-scale DLinear plus small residual TCN |

Torch probe defaults:

```text
epochs: 8
batch_size: 1024
learning_rate: 1e-3
weight_decay: 1e-4
dropout: 0.10
optimizer: AdamW
loss: class-weighted cross entropy
early_stopping: none in Stage 01 probe mode
```

These defaults are inherited as lightweight probe settings only. They must not
be copied into Stage 02 as final parameters without a formal train-inner HPO
protocol.

`simple_gru` and `shallow_lstm` are optional fixed controls only. They are not
recommended as Stage 01 search-eligible families and should not receive formal
Stage 02 HPO unless a later protocol revision explicitly adds recurrent models
to the core research question.

## 6. Validation Budget

Stage 01 should stay small enough that the stage answers the input-shape
question instead of becoming a model-selection stage.

Recommended budget:

```text
feature_sets: 2 to 3
window_sizes: 3              # 10, 20, 30
lightweight_probes: 4 to 5   # excluding dummy baselines
train_inner_folds: 2
seeds: 2
```

Predeclared screening sample cap:

```text
max_train_samples_per_fold: 50000
max_eval_samples_per_fold: 20000
sample_method: deterministic_even_stride_by_ticker_label
```

The cap is a compute guard only. It must be configured before execution and
must not be adjusted after inspecting official validation, test, or holdout
metrics.

The expected counted rows are:

```text
feature_set x window_size x probe x fold x seed
```

The config must define a hard cap before execution. Recommended cap:

```text
max_counted_probe_rows: 240
```

If the planned grid exceeds the cap, Stage 01 must fail before fitting any
probe. The operator may reduce feature sets or probes, but may not inspect
official validation or holdout/test rows to decide what to remove.

## 7. Train-Inner Fold Policy

All Stage 01 folds are derived inside the Stage 00 train interval only.

Required fold properties:

- chronological ordering;
- no shuffled or random split;
- no event interval overlap between fold-train and fold-eval rows;
- no ticker crossing;
- no trading-day crossing;
- no official validation rows;
- no closed holdout/test rows.

The fold builder must record:

```text
fold_id
train_start
train_end_exclusive
eval_start
eval_end_exclusive
purge_or_embargo_policy
n_train_samples
n_eval_samples
event_overlap_count
```

`event_overlap_count` must be zero for every fold. A non-zero value is a hard
failure.

## 8. Multiple-Comparison Control

Stage 01 is vulnerable to false wins because it scans multiple feature/window
cells with several probes. The stage must therefore:

- predeclare the grid before the first probe fit;
- write every completed, skipped, and failed probe row to a ledger;
- compare every probe against same-row dummy baselines;
- select by aggregate robustness, not one lucky probe/seed/fold;
- avoid official validation as a tie-breaker;
- report the number of candidate cells considered.

Primary screening metric:

```text
macro_f1
```

Secondary stability metrics:

```text
balanced_accuracy
mean_delta_macro_f1_vs_stratified_dummy
lcb_delta_macro_f1_vs_stratified_dummy
positive_ticker_count
seed_std_macro_f1
fold_std_macro_f1
```

A feature/window cell is Stage 02-eligible only if:

```text
mean_delta_macro_f1_vs_stratified_dummy > 0
positive_ticker_count >= 3
sample_count_loss_flag != hard_fail
no chronology/leakage guard failed
```

If no cell passes this screen, Stage 01 outputs `do_not_start_stage02` and a
failure reason.

## 9. Decision Rule And Stage 02 Handoff

Stage 01 may hand off:

```text
1 to 2 candidate feature/window configs
2 to 4 model families for Stage 02 train-inner HPO
```

The recommended Stage 02 family set is:

```text
lightgbm
standard_dlinear
tcn
ms_dlinear_tcn
```

`last_step_lightgbm_control` remains a control row. It may be run in Stage 02
for same-row comparison but should not be counted as a separate thesis model
family.

Stage 01 selection wording must use one of these forms:

```text
Selected candidate inputs for Stage 02 train-inner HPO.
Shortlisted model families for Stage 02.
No final model selected in Stage 01.
```

Forbidden Stage 01 wording:

```text
best model
final model
validation winner
holdout winner
proves MS-DLinear+TCN beats LightGBM
official validation selected
```

## 10. Stage 02 HPO Starting Space

This section is a handoff recommendation, not Stage 01 execution scope.

For Stage 02, use `window_size in [10, 20, 30]` as the input-window axis unless
Stage 01 freezes only one or two windows due to sample-count failure.

Recommended Stage 02 HPO families:

### LightGBM

Use a compact profile or sampled search space:

```text
n_estimators: 150, 200, 300
learning_rate: 0.05, 0.03, 0.02
max_depth: 3, 6, 8
num_leaves: 7, 31, 63
min_child_samples: 20, 50, 100
subsample: 0.8, 0.9, 1.0
colsample_bytree: 0.8, 0.9, 1.0
reg_lambda: 0.0, 1.0, 5.0
class_weight: balanced
```

Do not enumerate the full Cartesian product. Use profiles or bounded random
search.

### Standard DLinear

```text
moving_avg_kernel: 3, 5, 7, 11
individual_channels: false, true
dropout: 0.0, 0.05, 0.10
learning_rate: 0.0003, 0.001, 0.003
weight_decay: 0.0, 0.0001
```

`moving_avg_kernel` is conditional on `window_size`; kernels larger than the
input window must be excluded.

### TCN

```text
channels: (16,16), (32,32), (32,32,32)
kernel_size: 2, 3, 5
num_blocks: 2, 3
dilation_base: 2
dropout: 0.0, 0.10, 0.20
causal: true
residual: true
```

### MS-DLinear+TCN

Use a narrowed combination of the DLinear and TCN spaces. Predeclare two or
three multi-scale profiles, for example:

```text
moving_avg_kernels: (3,5,9)
moving_avg_kernels: (3,5,9,15)
moving_avg_kernels: (3,6,12,24)    # only for window_size=30
```

The hybrid should be interpreted as useful only if it improves over both
`standard_dlinear` and `tcn` under the same train-inner budget.

Recommended Stage 02 budget:

```text
screen_hpo:
  4 families x 8 sampled configs x 3 folds x 2 seeds = 192 fits

stability_refit:
  top 1 to 2 configs per family x 3 folds x 5 seeds
```

If compute is constrained:

```text
4 families x 6 sampled configs x 3 folds x 2 seeds = 144 fits
```

## 11. Output Artifacts

Stage 01 writes one compact result folder:

```text
results/01_feature_window_search/<run_id>/
  run_manifest.json
  artifact_inventory.csv
  01_feature_window_search_summary.csv
  01_candidate_inputs.json
  01_train_inner_probe_ledger.csv
  01_train_inner_fold_manifest.csv
```

Minimum `01_feature_window_search_summary.csv` columns:

```text
candidate_id
feature_set
window_size
n_samples_total
n_samples_by_ticker_json
n_train_inner_folds
n_seeds
n_probe_rows
mean_macro_f1
mean_balanced_accuracy
mean_delta_macro_f1_vs_stratified_dummy
lcb_delta_macro_f1_vs_stratified_dummy
positive_ticker_count
seed_std_macro_f1
fold_std_macro_f1
selected_for_stage02
selection_reason
```

Minimum `01_candidate_inputs.json` fields:

```text
route
stage_name
source_stage00_run_id
candidate_inputs
approved_model_families_for_stage02
control_models_for_stage02
decision
no_final_model_selected
holdout_test_contact
```

`no_final_model_selected` must be `true`. `holdout_test_contact` must be
`false`.

Minimum `01_train_inner_probe_ledger.csv` columns:

```text
probe_id
candidate_id
feature_set
window_size
fold_id
seed
fit_status
n_train_samples
n_eval_samples
macro_f1
balanced_accuracy
accuracy
baseline_id
baseline_macro_f1
baseline_balanced_accuracy
delta_macro_f1_vs_baseline
delta_balanced_accuracy_vs_baseline
sample_id_hash
error_message
```

Skipped and failed rows must remain in the ledger with `fit_status` and an
error message.

## 12. Minimum GitHub Tests

Keep these tests small and visible in GitHub:

- Stage 01 config schema accepts only predeclared feature sets, window sizes,
  probes, folds, seeds, and budget caps.
- Train-inner fold chronology and event-interval overlap guards reject leakage.
- Validation-only Stage 01 code cannot read, transform, window, score, or
  summarize official validation or closed holdout/test rows for selection.
- Preprocessing fit methods receive train-inner train rows only.
- Window builders reject cross-ticker, cross-day, and cross-split windows.
- Every probe comparison includes same-row dummy baseline metrics and
  `sample_id_hash`.
- `01_feature_window_search_summary.csv`,
  `01_candidate_inputs.json`, and `01_train_inner_probe_ledger.csv` match their
  required schemas.
- `run_manifest.json` records `holdout_test_contact=false`.
- Notebook static gate parses the notebook, keeps heavy cells off by default,
  and blocks forbidden active holdout/test strings.

Full notebook execution, full probe grids, GPU training, and long multi-seed
runs may be local-only or slow CI.

## 13. Reviewer Risks And Protections

| risk | why it matters | protection |
|---|---|---|
| Stage 01 becomes final model selection | inflates claims from cheap probes | protocol wording forbids final-model claims |
| official validation leakage | feature/window choices overfit the readout split | all selection is train-inner only |
| holdout/test contact | invalidates final verification | manifest and static gates require `holdout_test_contact=false` |
| multiple comparison | many cells can create chance wins | predeclared grid, ledger, budget cap, LCB/stability fields |
| HPO unfairness | more budget can make one family look better | Stage 01 fixed probes only; Stage 02 equal family budget |
| historical result inheritance | old notebooks or screenshots may bias V2 | historical evidence only motivates candidate grids |
| raw feature leakage or non-stationarity | raw levels can create spurious ticker/time effects | normalized feature sets and train-only preprocessing |
| short-window degeneration | DLinear/MS-DLinear kernels may not fit small windows | kernel choices are conditional on window size |

## 14. Evidence Basis

Local project evidence:

- `notebooks/02_config_screening_colab.ipynb` used LogReg and LightGBM for
  broad screening, then a small GRU and MS-DLinear+TCN only as a second-view
  diagnostic. Its fixed probe parameters inform Stage 01 defaults but do not
  become Stage 02 final params.
- `docs/BASELINE_REFERENCE.md` records Ian's feature-cleaning direction:
  remove raw non-stationary OHLCV/raw volume/raw MACD, use normalized
  decision-time-safe features, keep the no-trade band, and rerun LightGBM plus
  MS-DLinear+TCN only when implementations are real and fair.
- Ian's email on 2026-05-18 motivates a stock-aware multi-scale DLinear model
  with a residual TCN branch and keeps LSTM, TCN, and standard DLinear as
  baselines.
- Ian's email on 2026-05-29 motivates normalized features and rerunning
  LightGBM plus MS-DLinear+TCN before broader baseline comparison.
- Ian's email on 2026-06-04 suggests the final comparison table include Dummy,
  LightGBM, standard DLinear, TCN, and MS-DLinear+TCN.

External method anchors:

- Google Deep Learning Tuning Playbook: use a scientific tuning process,
  distinguish scientific, nuisance, and fixed hyperparameters, and avoid
  expanding search spaces without evidence.
  <https://developers.google.com/machine-learning/guides/deep-learning-tuning-playbook/scientific?hl=zh-tw>
- LightGBM parameter tuning documentation: tune tree complexity and
  regularization with parameters such as `num_leaves`, `max_depth`,
  `min_data_in_leaf`, `bagging_fraction`, `feature_fraction`, `lambda_l1`, and
  `lambda_l2`.
  <https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html>
- Zeng et al. (2022), "Are Transformers Effective for Time Series
  Forecasting?": primary DLinear/LTSF-Linear reference for simple linear
  sequence baselines.
  <https://arxiv.org/abs/2205.13504>
- Bai, Kolter, and Koltun (2018), "An Empirical Evaluation of Generic
  Convolutional and Recurrent Networks for Sequence Modeling": primary TCN
  reference for causal convolution sequence modeling.
  <https://arxiv.org/abs/1803.01271>
- Cawley and Talbot (2010): model-selection overfitting and validation reuse
  caution.
  <https://jmlr.org/papers/v11/cawley10a.html>

## 15. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- the target notebook, config, module, or test

Before writing code, the implementer MUST record a placement decision:

```text
placement_decision:
  target_file_type: <notebook|stage_config|model_search_space|python_module|test|protocol|artifact>
  target_path: <exact intended path>
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: <required when creating Python helper code>
  why_not_utils: <required when creating Python helper code>
  safety_tests: <target tests or "not applicable">
```

The implementation MUST preserve:

- Colab-first execution;
- one user-facing notebook per stage;
- one protocol doc and one config per stage;
- one `run_stage(config)` per executable stage when reusable logic exists;
- small Python helpers, no framework expansion;
- validation-only scope unless explicitly authorized;
- no official-validation selection;
- no holdout/test read, transform, window, score, or summary;
- train-only preprocessing;
- same-row dummy baseline comparison where model metrics are reported;
- run manifest with `holdout_test_contact=false`;
- notebook static-gate compatibility.

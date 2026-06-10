# 04 Diagnostics Ablation Protocol

Status: pre-registration core frozen 2026-06-09; operational detail (§9-14)
completed in Batch C on 2026-06-10 after the Stage 03 readout, strictly
within the frozen §2-8 core.

Revision record:

- 2026-06-10: replaced the §9 placeholder and §10 risk stub with the full
  operational sections §9-14 (entry gates, diagnostics definitions, ablation
  recipe, required artifacts, execution discipline, tests and risks). The
  §10 pre-registered risk rows were preserved and extended in §14. No §2-8
  sentence was changed. Implementation plan:
  `docs/lst_models_stage04_implementation_plan.md` (operational decisions
  OD1-OD9, reviewed 2026-06-10 with 8 accepted findings).

Scope: V2 `lst_models` route only. This document freezes the Stage 04
diagnostics and ablation decision rules (roadmap decision D3) before the Stage
03 official-validation readout executes. Stage 04 is diagnosis, not selection.
Stage 04 may not begin until `03_decision_record.json` is frozen; it runs
regardless of the Stage 03 outcome.

Decision provenance: D3 was frozen as the recommended default. Sign-off quoted
from `docs/lst_models_v2_route_roadmap.md` Phase 2:

> SIGN-OFF RECORD: user approved all four recommended defaults ("按推荐"),
> 2026-06-09. The choices below are frozen inputs for Batch B; changing any of
> them after the Stage 03 readout executes is forbidden.

Section freeze map: sections 2-8 are the frozen D3 core and are unchangeable
after the Stage 03 readout executes. Sections 9-14 were completed in Batch C
after the readout, strictly within the §2-8 core; they bind Stage 04
execution from their commit forward.

## 1. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- the target notebook, config, module, or test

Before writing code, the implementer MUST record a placement decision with the
AGENTS.md §2 fields. For this protocol edit:

```text
placement_decision:
  target_file_type: protocol
  target_path: docs/protocols/04_diagnostics_ablation_protocol.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; pre-registration protocol text only
  why_not_utils: not applicable; pre-registration protocol text only
  safety_tests: not applicable at core freeze; Batch C adds the Stage 04 test triad
```

Implementation must preserve:

- Colab-first execution; one user-facing Stage 04 notebook; one
  `run_stage(config)` entry point when executable logic is used.
- Validation-only scope: no holdout/test read, transform, window, score, or
  summary; no rows at or after `2017-01-25`; zero new official-validation
  fit-predict events (frozen D3, §2).
- Train-only preprocessing and same-row dummy baselines for every train-inner
  ablation fit where model metrics are reported.
- Manifest fields in §7; durable Drive result save; checkpoint plan for
  long-running ablation fits per AGENTS.md §5.

## 2. Stage Role And Input Boundary (frozen D3)

Stage 04 reads frozen Stage 03 artifacts only:

- `03_validation_predictions.csv` (per-row prediction dump)
- the `03_*` readout tables (`03_validation_readout.csv`,
  `03_per_ticker_readout.csv`, `03_seed_summary.csv`,
  `03_same_row_baselines.csv`)
- `03_decision_record.json`

New official-validation fit-predict events = 0. Stage 04 must not refit,
re-predict, re-threshold, recalibrate, or re-score any model on official
validation rows. The roadmap D3 alternative (a bounded validation-scored
ablation budget) was NOT chosen and may not be added after the readout.

## 3. Ablation Scoring Path (frozen D3)

Architectural-control ablations (`dlinear_only`, `tcn_only`, `last_step_mlp`,
`last_step_lightgbm_control`) are new fits — the four controls Stage 02
protocol §7 lists as "tracked architectural controls for future
implementation". They are fit and scored on Stage 02 train-inner folds ONLY,
under the same fold design, eligible-row, and same-row-baseline contracts
Stage 02 used (Stage 02 protocol §9, §10), with zero official-validation
contact. Ablation outcomes are diagnostic context only; they may not promote
a control to a thesis candidate or demote the frozen Stage 03 candidate.

## 4. Calibration — Measure-Only (frozen D3)

- Reliability bins, Brier score, and ECE are computed on the frozen
  `03_validation_predictions.csv` dump. Method anchor: Guo et al. 2017, "On
  Calibration of Modern Neural Networks", ICML (arXiv:1706.04599).
- NO calibrator fitting on official validation (no Platt, isotonic,
  temperature scaling, or any other fitted mapping).
- A calibrated model would require a new pre-registered protocol revision
  with a calibration set carved from the train tail; that revision is a V2.1
  item, not a Stage 04 action.

## 5. Selective / No-Trade Diagnostics (frozen D3)

- Full risk-coverage curves and AURC computed from the frozen prediction
  dump. Anchors: Geifman & El-Yaniv 2017 (arXiv:1705.08500); AURC per
  Geifman et al. 2019 (arXiv:1805.08206).
- Report whole curves. Never mark, recommend, or operationally select an
  operating point; `chosen threshold` is a forbidden string in Stage 04
  outputs, notebooks, and prose.

## 6. Robustness Slices And Failure Analysis (frozen D3)

- Per-ticker, per-seed, and per-period concentration of the pooled deltas is
  computed from the frozen dump only; flag when the pooled result is carried
  by a single ticker, seed, or period.
- Failure analysis (error concentration by ticker, time-of-day, trading day,
  volatility state) comes from the frozen dump only.
- No new validation scoring may be used to refine any slice.

## 7. Hard Boundary And Manifest Contract (frozen D3)

Stage 04 cannot change the Stage 03 outcome. Findings become limitation text
or pre-registered V2.1 items; they never reopen Stage 02/03 selection. The
Stage 04 run manifest must record:

```text
official_validation_contact=read_frozen_artifacts_only
new_validation_fit_predict_events=0
holdout_test_contact=false
```

## 8. Wording Rules (frozen)

Stage 04 inherits the Stage 03 forbidden list. Forbidden strings:
`final model`, `official validation winner`, `holdout winner`, `test winner`,
`proved best model`, `generalization proven`, `profitable`, `holdout-ready`,
`selected by official validation`, `chosen threshold`.

Allowed wording: `validation-only evidence`, `official validation readout`,
`candidate met/did not meet predeclared validation-readout criteria`.

## 9. Inputs And Entry Gates

Stage 04 consumes four exact upstream run folders, pinned by run id in
`configs/stages/04_diagnostics_ablation.yaml`:

```text
stage00_run_id: "20260610_051705_347450"
stage01_run_id: "20260610_075002"
stage02_run_id: "20260610_082130_797479"
stage03_run_id: "20260610_133305_716174"
superseded_stage02_run_ids: ["20260609_100637_704705", "20260610_010019_507648"]
```

`run_stage(config)` must fail closed, with exact-path/exact-field errors,
when any of the following gates fails:

1. Each upstream run folder resolves by exact run id; required artifacts
   resolve by `run_folder / relative_path`; when the upstream
   `artifact_inventory.csv` records `bytes`/`sha256`, required reads verify
   those values (`artifacts.require_artifacts`).
2. `03_decision_record.json` records `readout_complete=true`,
   `holdout_test_contact=false`, `official_validation_for_selection=false`,
   and `official_validation_scoring_events == len(scoring_event_ledger)`.
   The decision string is echoed into the Stage 04 diagnostics report; Stage
   04 runs for either outcome.
3. Run-id chain consistency: the decision record's
   `source_stage00/01/02_run_id` equal the config pins; the config
   `stage02_run_id` is not in `superseded_stage02_run_ids`.
4. Stage 02 packaging proof: `02_hpo_plan_ledger.csv` sha256 differs from
   `02_hpo_trial_ledger.csv` sha256.
5. Prediction-dump gates on `03_validation_predictions.csv`: exact column
   set (`candidate_role, candidate_id, model_family, hpo_profile_id, seed,
   sample_id, ticker, target_timestamp, trading_day, y_true, p_up, y_pred,
   scope`); row count equals the sum of ledger `n_rows` (production
   expectation 302,128 = 2 seeds × 151,064); a single
   `candidate_role="primary"`; uniform `scope="validation_only"`; seeds
   exactly the frozen `[101, 202]`; max `target_timestamp` strictly before
   `2017-01-25` (the boundary literal appears only as this closed-holdout
   guard).
6. Ablation rebuild parity (train rows only): rebuilt total and per-ticker
   eligible counts for the ablation candidate input equal
   `01_feature_window_search_summary.csv`, and per-fold capped
   train/eval `sample_id_hash` values equal the frozen Stage 02 plan-ledger
   hashes. A hash mismatch is a hard error: without same-row identity the
   §3 same-fold comparison is void.
7. Raw files are fetched by Drive file ID and verified against the frozen
   Stage 00 raw manifest hashes (strict for the pinned R3 chain).
8. `holdout_test_contact=false` and `official_validation_for_selection=false`
   on every upstream manifest and handoff.

## 10. Diagnostics Definitions (measure-only, frozen dump as sole source)

All diagnostics read `03_validation_predictions.csv` plus frozen Stage 03
summary artifacts. No model object is constructed in this arm; no torch or
lightgbm import may occur before the ablation arm starts.

Calibration (§4 core):

- Views: `p_up` probability calibration (primary; predicted P(up) vs
  empirical up-frequency) and `top_label_confidence` = `max(p_up, 1-p_up)`
  (secondary, Guo et al. 2017 convention; predicted label `p_up >= 0.5`,
  ties to class 1).
- Binning: equal-width primary with `n_bins=15`; sensitivity at 10 and 20;
  equal-mass (quantile) variant per Nixon et al. 2019. Reported per seed
  plus a descriptive seed-mean row; seed rows are never pooled row-wise.
- Reported values: `ece`, `mce`, `brier_score`, Murphy decomposition
  (`brier_reliability - brier_resolution + brier_uncertainty`, computed on
  the same bins; binned plugin estimators are biased — Kumar et al. 2019 —
  so all calibration numbers are descriptive measurements, never population
  claims). Per-ticker ECE is a secondary slice with the same bins.

Selective / no-trade (§5 core):

- Confidence score: `top_label_confidence`. Risk:
  `1 - accuracy_on_covered_rows`. Full-resolution per-row risk-coverage
  curve with deterministic tie-break by `sample_id`; the CSV artifact
  downsamples to a coverage grid (step 0.005, minimum coverage 0.05);
  AURC is computed at full resolution; `e_aurc = aurc - oracle_aurc`
  (oracle: same error count sorted worst-last; Geifman et al. 2019).
  `selective_macro_f1` is reported per grid point as a secondary curve.
- Whole curves only. No recommended, selected, or highlighted operating
  point anywhere in artifacts, notebook, or prose.

Same-row baseline reconstruction (slice-delta mechanism):

- Per-row `stratified_dummy_train_prior` predictions are reconstructed by
  calling the same frozen helper
  (`metrics.predict_stratified_dummy(y_refit_labels, n_eval, seed)`) with
  the rebuilt official-train refit labels, in dump row order per seed.
- Dual equality gates, tolerance 1e-9: (a) pooled macro-F1/accuracy/MCC of
  the reconstruction equal the frozen `03_same_row_baselines.csv` row, AND
  (b) per-ticker candidate-vs-dummy deltas recomputed from the
  reconstruction equal the frozen `03_per_ticker_readout.csv` deltas
  (5 tickers × 2 seeds).
- On any mismatch the reconstruction is rejected whole: every
  stratified-dummy slice delta outside the frozen ticker level and every
  leave-one-out flag is emitted as
  `not_computed_due_to_baseline_reconstruction_mismatch`. Realized-draw and
  expectation semantics must never mix in one artifact.
- Ticker-level dummy deltas are always sourced verbatim from
  `03_per_ticker_readout.csv`. `majority_train_prior`, `constant_up`, and
  `constant_down` slice values are exact analytic values of deterministic
  constant predictions and are unaffected.
- Reconstruction is a deterministic replay of frozen evidence (train labels
  + frozen seed), involves no model, and is NOT a validation scoring event
  (Stage 03 precedent: baseline rows were not events). The manifest still
  records the read contact (§13).

Robustness slices and failure analysis (§6 core):

- Slice axes: `ticker`, `seed`, `calendar_year`, `calendar_quarter`,
  `time_of_day_hour`, `activity_tercile`. All derived columns are pure dump
  transformations. The volatility-state proxy is dump-native:
  `activity_tercile` = per-ticker terciles of eligible-row count per
  `(ticker, trading_day)`; it is named an activity proxy and never called
  realized volatility (a raw-bar volatility slice is a V2.1 item).
- Concentration rule: for axes `{ticker, seed, calendar_year}` compute the
  leave-one-slice-out pooled delta vs the reconstructed stratified dummy;
  `loo_sign_flip=true` when removing one slice turns the pooled delta
  <= 0. `share_of_pooled_positive_delta` is reported descriptively.
- Failure tables: error concentration by `ticker_hour`,
  `ticker_trading_day`, `activity_tercile`, `calendar_month`; minimum slice
  size 200 rows; top-25 worst qualifying slices per axis; boundary years
  2013/2017 are partial and every slice row carries `n_rows`.
- Uncertainty context: only the frozen trading-day block bootstrap
  (`metrics.block_bootstrap_macro_f1_delta`, blocks `ticker|trading_day`,
  1000 draws, seed 12345) on pooled and per-ticker deltas. No new
  significance machinery (no McNemar, no DM test).

## 11. Ablation Recipe (train-inner only, §3 core)

- Candidate input: `price_volume_time_w20` only (the frozen primary's
  input; the ablation question is which architectural ingredient carries
  the primary's train-inner signal, not a second search).
- Fold/row contract: Stage 02's 3 chronological train-inner folds, seeds
  `[101, 202]`, 50k/20k `deterministic_even_stride_by_ticker_label` caps,
  same-row baselines recomputed via `metrics.score_registry_baseline` on
  the capped rows, byte-equal Stage 02 training defaults, class weights
  recomputed per fold fit-subset.
- Budget: `planned_rows = 4 controls × 1 candidate_input × 3 folds × 2
  seeds = 24 <= max_ablation_plan_rows 32`. The plan ledger is written
  before any fit and contains no fitted metrics.
- Predeclared control parameters (zero new HPO; deterministic copies):
  - `tcn_only`: the frozen primary's exact profile params from
    `03_decision_record.json -> primary_candidate.hpo_profile_params`;
    builder `TCNTiny`.
  - `dlinear_only`: the multi-scale DLinear branch alone; params from
    `02_best_params_by_family.json["ms_dlinear_tcn"]` keeping
    `moving_avg_kernels`, `dropout`, `learning_rate`, `weight_decay` and
    dropping `tcn_channels`, `tcn_kernel_size`; builder
    `MSDLinearOnlyTiny`.
  - `last_step_mlp`: fixed config literals (`hidden_size 32`, `dropout
    0.10`, `learning_rate 0.001`, `weight_decay 0.0001`); consumes only the
    window's last bar; builder `LastStepMLPTiny`.
  - `last_step_lightgbm_control`: params from
    `02_best_params_by_family.json["lightgbm"]`, applied to the last bar's
    feature columns only.
  Resolved profile ids and derivations are recorded per row in the ledgers.
- Reference rows, not refits: the frozen primary's train-inner evidence is
  joined read-only from `02_hpo_trial_ledger.csv` filtered to
  `(price_volume_time_w20, tcn, tcn_p01)` — exactly 6 completed rows; any
  other count is a hard error. No primary refit occurs in Stage 04.
- Stage 02 §7 rule restated: controls may not become additional thesis
  candidates after results are seen; the ablation summary carries no
  ranking or promotion column.

## 12. Required Artifacts

The required-output contract is the single list `REQUIRED_STAGE04_ARTIFACTS`
(defined in `src/lst_models/stages/diagnostics_ablation.py`; the config
outputs block, this section, the runner writer, the config-contract closure
test, and the nb04 durable-save validation all consume it):

```text
run_manifest.json
artifact_inventory.csv
04_calibration_summary.csv
04_reliability_bins.csv
04_risk_coverage_curve.csv
04_selective_summary.csv
04_robustness_slices.csv
04_failure_slices.csv
04_ablation_plan_ledger.csv
04_ablation_trial_ledger.csv
04_ablation_summary.csv
04_diagnostics_report.json
```

`drive_backup_manifest.json` is produced and uploaded LAST by the notebook
save cell itself (AGENTS.md §5) and is deliberately outside this pre-upload
validation list. Every tabular row carries `scope="validation_only"`.

Column constants (frozen with the code; the runner asserts exact equality):

```text
04_calibration_summary.csv:
  candidate_role, candidate_id, seed, ticker, view, binning_scheme, n_bins,
  n_rows, ece, mce, brier_score, brier_reliability, brier_resolution,
  brier_uncertainty, mean_predicted, base_rate_up, scope
  (ticker="pooled" for the pooled rows; per-ticker ECE rows are emitted for
  the primary view/scheme/bin-count; seed="seed_mean" rows are descriptive)
04_reliability_bins.csv:
  candidate_role, candidate_id, seed, view, binning_scheme, n_bins,
  bin_index, bin_lower, bin_upper, n_rows, mean_predicted,
  empirical_frequency, abs_gap, scope
04_risk_coverage_curve.csv:
  candidate_role, candidate_id, seed, coverage, n_covered,
  confidence_at_coverage, selective_risk, selective_accuracy,
  selective_macro_f1, scope
04_selective_summary.csv:
  candidate_role, candidate_id, seed, n_rows, aurc, oracle_aurc, e_aurc,
  full_coverage_risk, full_coverage_macro_f1, scope
04_robustness_slices.csv:
  candidate_role, candidate_id, seed, slice_axis, slice_value, n_rows,
  macro_f1, delta_macro_f1_vs_stratified_dummy_train_prior,
  delta_macro_f1_vs_majority_train_prior, delta_source,
  share_of_pooled_positive_delta, loo_pooled_delta, loo_sign_flip,
  bootstrap_delta_lcb, bootstrap_delta_ucb, scope
04_failure_slices.csv:
  candidate_role, candidate_id, seed, slice_axis, slice_value, n_rows,
  error_count, error_rate, error_rate_lift_vs_seed_pooled, support_up,
  support_down, scope
04_ablation_plan_ledger.csv:
  control_id, probe_id, candidate_id, feature_set, window_size,
  model_family, params_source, params_source_detail, fold_id, seed,
  n_train_rows, n_eval_rows, train_sample_id_hash, eval_sample_id_hash,
  baseline_ids, scope
04_ablation_trial_ledger.csv:
  plan columns (minus scope) + fit_status, error_message, macro_f1,
  balanced_accuracy, accuracy, mcc, roc_auc,
  baseline_macro_f1_stratified_dummy_train_prior,
  baseline_macro_f1_majority_train_prior,
  delta_macro_f1_vs_stratified_dummy_train_prior,
  delta_macro_f1_vs_majority_train_prior, positive_ticker_count,
  best_iteration, early_stopping_source, early_stopping_used,
  early_stopping_reason, early_stopping_train_sample_id_hash,
  early_stopping_eval_sample_id_hash, requested_device, resolved_device,
  device_fallback_reason, scope
04_ablation_summary.csv:
  control_id, probe_id, candidate_id, n_trials, n_completed, mean_macro_f1,
  mean_delta_macro_f1_vs_stratified_dummy_train_prior,
  min_delta_macro_f1_vs_stratified_dummy_train_prior,
  mean_delta_macro_f1_vs_majority_train_prior, positive_ticker_count_mean,
  reference_primary_family_mean_macro_f1,
  reference_primary_family_mean_delta_vs_stratified_dummy,
  gap_to_reference_mean_delta, scope
```

`04_diagnostics_report.json` fields: route, stage_name,
`source_stage00/01/02/03_run_id`, `superseded_stage02_run_ids`, the Stage 03
decision echo, dump row counts per seed, `baseline_reconstruction_status`
(`verified_identical` | `mismatch_deltas_not_computed`), concentration-flag
summary, ablation plan/completed counts per control,
`new_validation_fit_predict_events=0`, `official_validation_scoring_events=0`,
`official_validation_rows_read`, `frozen_prediction_dump_read=true`,
`no_reselection=true`, `no_final_model_selected=true`,
`holdout_test_contact=false`, and the deferred-items list
(`raw_bar_volatility_slice`, `shap_permutation_importance` —
V2.1-eligible; validation-side permutation/SHAP would create new prediction
events and is forbidden).

## 13. Execution Discipline

- Read-contact accounting is separate from the fit-predict budget: the
  manifest records `official_validation_contact=read_frozen_artifacts_only`,
  `new_validation_fit_predict_events=0`,
  `official_validation_scoring_events=0`, AND
  `official_validation_rows_read=<dump rows>` +
  `frozen_prediction_dump_read=true`, so the Stage 05 budget ledger cannot
  misread "zero events" as "zero validation contact".
- Manifest also mirrors the Stage 03 shape: device provenance
  (`requested_device`, `resolved_device`, `cuda_available`,
  `gpu_name_or_null`, `device_fallback_reason`), git-commit fields,
  config/notebook sha256, exact upstream run ids,
  `feature_rebuild_code_sha256` match flag vs the Stage 02 manifest (the
  ablation rebuild uses the same provenance-hashed mechanism), and
  `stage04_diagnostics_code_sha256` over the new metric helpers and the
  runner's diagnostics/ablation entry functions.
- Checkpoints: local checkpoint after each completed control (4 natural
  units), mirrored as compact archives to
  `My Drive/lst_models/checkpoints/04_diagnostics_ablation/<run_id>/`
  (config `checkpoint_drive_path_parts`). `checkpoint_manifest.json`
  records `stage_name`, `run_id`, `status=incomplete`, completed/pending
  controls, timestamp, and resume instructions with
  `resume_mode=exact_run_checkpoint_only` and
  `latest_parent_scan_allowed=false`.
- Resume requires the exact `run_id` and checkpoint folder; completed
  controls are never refit; a `run_id` mismatch is a hard error.
- Pre-flight feasibility (before any fit): dump size check plus estimated
  ablation materialized bytes vs the predeclared cap; abort cleanly with
  zero fits if exceeded.
- Durable save: nb04 validates the twelve `REQUIRED_STAGE04_ARTIFACTS`
  (imported, not retyped) and REFUSES upload unless the manifest records
  `new_validation_fit_predict_events == 0`,
  `official_validation_contact == "read_frozen_artifacts_only"`, and
  `holdout_test_contact == false`. Results go to
  `My Drive/lst_models/results/04_diagnostics_ablation/<run_id>/`;
  duplicate Drive folder/file matches are hard errors;
  `drive_backup_manifest.json` is written and uploaded last with a null
  self-size.
- One compact progress line per completed control×fold×seed; no per-epoch
  spam.

## 14. Tests And Risks

Minimum test surface (all CPU-safe; torch-dependent dispatch tests are
env-gated):

- `tests/contracts/test_stage04_config_contract.py`: scope/zero-event
  flags, exact four-stage run-id pins, byte-equal training defaults vs
  Stage 02, budget arithmetic closure, controls list, measure-only flags,
  required-artifact closure against `REQUIRED_STAGE04_ARTIFACTS`,
  checkpoint Drive contract, forbidden wording.
- `tests/stages/test_stage04_run_stage_smoke.py`: fail-closed entry gates
  (incomplete readout, chain mismatch, superseded id, dump schema/row
  gates, holdout-boundary poison row); calibration/selective schema and
  golden behavior; reconstruction equality gate and mismatch semantics
  (`not_computed_…`, no mixing); LOO flag behavior; ablation plan/budget,
  Stage 02 hash parity, validation-row guard (no ablation fit may touch a
  dump `sample_id`), reference-row count gate, checkpoint manifest
  contract, exact-run resume; artifact schemas; manifest fields; wording
  scan.
- `tests/notebooks/test_stage04_notebook_static.py`: parse/AST/empty
  outputs, `RUN_STAGE04=False`, pinned commit, four run-id strings,
  runtime-injection lines, durable-save refusal conditions, duplicate-Drive
  hard-error helper, forbidden patterns (holdout/test reads, boundary
  literal outside the guard echo, selection-on-validation strings, the ten
  forbidden wording strings, calibrator-fitting tokens
  `CalibratedClassifierCV`/`IsotonicRegression`/`temperature_scal`/`Platt`).
- `tests/contracts/test_metrics.py`: golden tests for reliability bins,
  ECE/MCE, Brier decomposition identity, risk-coverage curve, AURC/E-AURC.
- A contract test greps `src/lst_models/stages/diagnostics_ablation.py` for
  the calibrator-fitting tokens (must be absent).

Risk register (preserves and extends the pre-registered §10 rows):

- Risk: diagnostics silently become reselection. Protection: §2 zero-event
  rule, §7 hard boundary and manifest fields, §8 forbidden strings.
- Risk: a calibrator or operating threshold is fitted on official validation.
  Protection: §4/§5 measure-only rules, frozen before the readout; static
  calibrator-token gates (§14).
- Risk: ablation fits leak official-validation signal. Protection: §3
  train-inner-only path under Stage 02 fold/row/baseline contracts; the
  smoke-test validation-row guard; §9 gate 6 hash parity.
- Risk: post-readout edits to the frozen core. Protection: the section
  freeze map; changes after the readout are forbidden and visible in git
  history.
- Risk: reconstruction mismatch silently degrades slice deltas into
  expectation values. Protection: §10 not-computed semantics; mixing
  realized and expectation deltas is forbidden by contract and test.
- Risk: reference-row join drift. Protection: exactly-6-rows hard error.
- Risk: control budget creep. Protection: §11 formula + config cap +
  contract test.
- Risk: partial boundary years misread as full periods. Protection:
  `n_rows` on every slice row; §10 partial-period note.
- Risk: Colab loss mid-ablation. Protection: §13 per-control checkpoints,
  Drive mirror, exact-run resume.

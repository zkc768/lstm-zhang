# Stage 04 Bundle (Batch C) Implementation Plan

Revision record:

- 2026-06-10 (Colab execution regression fix, first nb04 run): all 24
  control fits completed, then `_ablation_summary` crashed on a
  fixture-invented column name — the REAL `02_hpo_trial_ledger.csv` names
  its delta `delta_macro_f1_vs_baseline` (with `baseline_id` identifying the
  baseline), not `delta_macro_f1_vs_stratified_dummy_train_prior`. Fix:
  reference rows now read `REFERENCE_DELTA_SOURCE_COLUMN` with a hard
  `baseline_id == stratified_dummy_train_prior` gate, the reference
  schema/count/baseline gates moved BEFORE the fit loop (schema mismatches
  must fail in seconds, never after compute), the smoke fixture mirrors the
  real ledger schema, and two regression tests pin the gate ordering and the
  baseline-id requirement. Recovery path: exact-run resume of the crashed
  run id (completed controls never refit). Lesson recorded: every consumer
  of a REAL upstream artifact schema must be verified against the producing
  stage's column constants, not against fixture assumptions.
- 2026-06-10 (implementation correction record, post-Batch-C build): the
  700-line stage-module ratchet forced the planned T6-T9 layout to shed
  domain logic during implementation; the as-built placement supersedes the
  task text below where they differ. As built: measure-only diagnostics
  frame builders + dump gates + column constants live in the NEW domain
  module `src/lst_models/diagnostics.py` (route-guide tables updated in the
  same change); control fit/score mechanics + `resolve_control_profile` +
  `fit_stage_control`/`fit_and_score_control_trial` live in `fitting.py`;
  `build_capped_fold_rows` + `require_recorded_fold_hash_parity` live in
  `windows.py`; `feature_rebuild_gate_fields` (deduped with Stage 03),
  `load_incremental_checkpoint`/`write_incremental_checkpoint`, and the
  shared gate helpers live in `artifacts.py`;
  `aggregate_trial_device_fields` lives in `device.py`. Column-constant
  corrections: `04_calibration_summary.csv` gained a `ticker` column
  (per-ticker ECE rows; "pooled"/"seed_mean" markers); ablation ledgers use
  `fold_id` (matching the Stage 02 plan-ledger join key); the diagnostics
  risk-coverage constant is `RISK_COVERAGE_CURVE_COLUMNS`. Protocol §12 was
  synced in the same change. `diagnostics_ablation.py` landed at exactly
  700 lines; the fast suite is 165 passed / 2 env-gated torch skips.
- 2026-06-10 (pre-implementation review, 8 findings, all accepted): added
  `agent_capabilities_and_skill_routing.md` to required reading; closed the
  required-artifact list with `REQUIRED_STAGE04_ARTIFACTS` (12 names, drive
  manifest excluded by design); moved `CONTROL_PROBE_BY_ID` from
  `fitting.py` to the stage module; OD2 mismatch now emits
  `not_computed_…` instead of analytic-expectation substitution (no mixed
  delta semantics); manifest separates read-contact accounting
  (`official_validation_rows_read`, `frozen_prediction_dump_read`) from the
  fit-predict budget; checkpoint Drive path parts + manifest/resume
  contract tests added; stage-module LOC budgets + artifacts.py helper
  moves made explicit; Ian/Lan email block reframed as non-blocking
  provenance with verbatim extracts at `docs/ian_lan_requirement_extracts.md`.

> **For agentic workers:** Execute task-by-task with review checkpoints.
> Required reading before any code (AGENTS.md §2): `AGENTS.md`,
> `docs/lst_models_code_style_and_route_guide.md`,
> `docs/lst_models_v2_route_roadmap.md` (Phase 5 / Batch C, decision D3 frozen
> 2026-06-09), `docs/protocols/04_diagnostics_ablation_protocol.md` (frozen
> core §2-8), `docs/protocols/02_model_hpo_train_inner_protocol.md` (§7, §9,
> §10 ablation contracts), `docs/protocols/03_frozen_validation_readout_protocol.md`,
> `docs/agent_capabilities_and_skill_routing.md` (this plan references
> connectors, Gmail-derived provenance, and codegraph — AGENTS.md §2 routing
> rule; connector/KB material is background provenance ONLY and never
> overrides the Stage 04 contract), and the target files of each task. Steps
> use checkbox syntax for tracking.
> Git commits only when the user has authorized committing (AGENTS.md §13);
> each task lists its commit point for when that authorization exists.

**Goal:** Implement the complete Stage 04 sidecar bundle (protocol operational
detail, config, runner, notebook, tests) so that diagnostics and ablations run
over the frozen Stage 03 readout with ZERO new official-validation fit-predict
events and zero reselection pressure, per the D3 core frozen on 2026-06-09.

**Architecture:** `run_stage(config)` in a new
`src/lst_models/stages/diagnostics_ablation.py` with two strictly separated
arms:

1. **Diagnostics arm (read-only):** loads the frozen
   `03_validation_predictions.csv` dump and computes calibration
   (reliability/ECE/Brier), selective risk-coverage/AURC, robustness slices,
   and failure analysis. No model object is ever constructed in this arm.
2. **Ablation arm (train-inner only):** rebuilds the Stage 02 train-inner
   fold data with the same frozen domain builders, fits the four predeclared
   architectural controls on those folds, scores them against same-row
   baselines, and joins the frozen Stage 02 primary-family rows as read-only
   reference. Official validation rows are never touched by this arm.

Reusable metric logic (reliability bins, ECE, Brier decomposition,
risk-coverage, AURC/E-AURC) goes to `metrics.py`; new tiny model builders go
to `src/lst_models/models/`; control dispatch extends `fitting.py`. The stage
module is orchestration only (AGENTS.md anti-spaghetti gates: no cross-stage
imports, stage module < 700 LOC, `run_stage` body < 90 lines).

**Tech stack:** existing project stack only — pandas/numpy/sklearn/lightgbm/
torch via `src/lst_models/` helpers. No new dependencies.

**Non-blocking provenance note — Ian/Lan email requirements.** This block is
requirement provenance, NOT executable Stage 04 contract; the Stage 04
contract is the frozen protocol plus this plan's tasks. Verbatim dated
extracts are preserved in-repo at `docs/ian_lan_requirement_extracts.md`
(source: Gmail thread "Progress update on DLinear stock direction
experiments", ian Deng <yancongdeng@gmail.com>, read 2026-06-10). Ian's
2026-06-04 instruction list and where the route answers each item:

| Ian requirement (2026-06-04) | Route answer | Status |
|---|---|---|
| "small ablation study with standard DLinear, multi-scale DLinear, and MS-DLinear+TCN ... show whether each part of the proposed model is useful" | Stage 04 ablation arm: `dlinear_only` control IS multi-scale DLinear alone (new fits); `standard_dlinear`, `tcn`, `ms_dlinear_tcn` rows joined read-only from the frozen Stage 02 trial ledger; same folds, same rows, same baselines | this plan (T3/T8) |
| "checking selective prediction" (2026-05-29) | Stage 04 C2 risk-coverage/AURC whole-curve diagnostics on the frozen dump | this plan (T2/T7) |
| "run the current model on 2–3 additional walk-forward holdout periods ... report tested results" | NOT Stage 04 (would violate the frozen D3 zero-event rule and D4 holdout closure). Requires a pre-registered V2.1 guarded walk-forward protocol on the post-2017 segment (V1-contacted, so "guarded historically-contacted" wording; Ian acknowledged the contamination caveat in the 2026-06-01 mail). Draft in parallel; execute after Stage 04 | V2.1 pre-registration (separate doc) |
| "one final comparison table ... Dummy, LightGBM, standard DLinear, TCN, and MS-DLinear+TCN" | Train-inner: assembled from frozen Stage 02 ledger + Stage 04 ablation summary. Validation: primary vs baselines only (one-shot readout, by design). All-family same-period rows belong in the V2.1 walk-forward pre-registration if Ian wants them on held-out periods | Stage 05 tables + V2.1 |
| "start writing the paper ... Introduction, Related Work, Method, Dataset, Experimental Setup (ACM template)" | Stage 05 scaffolding starts in parallel with Batch C; Results section waits for frozen 04 artifacts | Batch D (parallel start) |
| Timeline: experiments 1–2 weeks (from 06-04), draft+revision 2 weeks after | Batch C execution + V2.1 pre-registration inside the experiment window | active constraint |

Earlier Ian guidance already absorbed by the frozen route (no action):
chronological train/val/test with no test-set early stopping (2026-03-13 →
Stage 00 split freeze), same-day windows/RTH-only (→ Stage 00 §9), 5-minute
bars (2026-03-25), pooled multi-stock training with per-ticker evaluation
(2026-04-19 → `pooled_five_ticker` + per-ticker readout), macro-F1 /
balanced-accuracy / confusion-matrix / dummy-delta reporting (2026-05-04 →
B7 metric contract), no-trade-band labels (2026-05-18 → Stage 00 ±3.0 bps
band), stationary normalized feature set incl. time-of-day (2026-05-29 →
the frozen `price_volume_time` candidate), LightGBM as strong tabular
control (2026-05-22 → HPO family + frozen fallback). Fill-points for Stage
06 §5 mapping rows (Batch E) inherit this table.

```text
placement_decision:
  target_file_type: protocol  # implementation planning document
  target_path: docs/lst_models_stage04_implementation_plan.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: planning document; per-task placement decisions below cover code
  why_not_utils: per-task decisions; metric logic -> metrics.py, builders ->
    models/, control dispatch -> fitting.py, orchestration -> stage module
  safety_tests: tests/contracts/test_stage04_config_contract.py,
    tests/stages/test_stage04_run_stage_smoke.py,
    tests/notebooks/test_stage04_notebook_static.py,
    tests/contracts/test_metrics.py (calibration/selective golden tests)
```

---

## 0. Stage 03 Outcome Snapshot (frozen evidence basis)

All Stage 04 pins below are verified against the durable Drive artifacts
(read 2026-06-10). This section is evidence, not aspiration.

| Field | Value |
|---|---|
| Stage 03 run id | `20260610_133305_716174` |
| Decision | `met_predeclared_validation_readout_criteria` (all three predeclared criteria true) |
| `readout_complete` / `fallback_activated` / `resumed_from_checkpoint` | `true` / `false` / `false` |
| Scoring events | 2 (seed 101 @ 2026-06-10T13:40:30Z, seed 202 @ 13:42:51Z; 151,064 validation rows each) |
| Refit rows | 736,685 official-train rows; tail early stopping `inner_train_chronological_tail`, best epoch 8 (seed 101) / 15 (seed 202), reason `patience_exhausted` |
| Primary candidate | `price_volume_time_w20`, family `tcn`, profile `tcn_p01` (`channels [16,16]`, `kernel_size 2`, `dropout 0.0`, `lr 0.001`, `wd 0.0001`), window 20 |
| Fallback (never activated, never scored) | `price_action_core_w20`, family `lightgbm`, profile `lgbm_p02` |
| Aggregate (mean over seeds) | macro-F1 0.51703; delta vs `stratified_dummy_train_prior` +0.01689; delta vs `majority_train_prior` +0.18833; positive tickers 5/5 |
| Per-seed macro-F1 (delta vs dummy) | seed 101: 0.51764 (+0.01625); seed 202: 0.51641 (+0.01752) |
| Per-ticker mean delta vs dummy | CSCO +0.02208, KO +0.01959, MSFT +0.01792, WMT +0.01415, JPM +0.01001 |
| Same-row baselines (seed 101) | stratified dummy macro-F1 0.50139; majority 0.32869; constant_up 0.33791 (accuracy 0.51037 → validation up-rate ≈ 51.04%, train majority class = down) |
| Upstream chain | Stage 00 `20260610_051705_347450`, Stage 01 `20260610_075002`, Stage 02 `20260610_082130_797479`; superseded Stage 02 ids `["20260609_100637_704705", "20260610_010019_507648"]` |
| Execution provenance | git commit `142646000a7bdd11f0985e915fc627a9eea101fd` (bundle `1426460`, notebook pin `c89d3ca`), Tesla T4, cuda; `feature_rebuild_code_sha256` matched Stage 02 (`0bf0752c…`) |
| Drive (durable results) | `My Drive/lst_models/results/03_frozen_validation_readout/20260610_133305_716174/` (folder id `1-zHreb4SFs_M1xWOiX5POC3BjdnGCR51`); prediction dump 43,659,700 bytes |
| Drive (checkpoints) | `My Drive/lst_models/checkpoints/03_frozen_validation_readout/20260610_133305_716174/` (folder id `1qPlBteatrxz0U6lelQA9fAEBa9bJl2ZU`) |

Scoring-event semantics precedent (binding for Stage 04 wording): Stage 03
counted only candidate fit-predict events in
`official_validation_scoring_events`; the four same-row baselines scored
inside those events are frozen evidence rows, not separate events. Stage 04
adds zero events of either kind.

Expected dump shape: 302,128 rows (2 seeds × 151,064), columns exactly
`candidate_role, candidate_id, model_family, hpo_profile_id, seed, sample_id,
ticker, target_timestamp, trading_day, y_true, p_up, y_pred, scope`; all rows
`candidate_role="primary"`, `scope="validation_only"`; max `target_timestamp`
strictly before `2017-01-25`; validation window starts `2013-09-16` (boundary
years 2013/2017 are partial — slice tables must carry `n_rows` so partial
periods read honestly).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `docs/protocols/04_diagnostics_ablation_protocol.md` | Modify (§9-10 → §9-14) | operational detail; frozen §1-8 untouched (T1) |
| `src/lst_models/metrics.py` | Modify | calibration + selective metric helpers (T2) |
| `tests/contracts/test_metrics.py` | Modify | golden tests for T2 helpers (T2) |
| `src/lst_models/models/ms_dlinear_only.py` | Create | multi-scale DLinear branch control builder (T3) |
| `src/lst_models/models/last_step_mlp.py` | Create | last-bar MLP control builder (T3) |
| `src/lst_models/fitting.py` | Modify | control probe dispatch + last-bar slice (T3) |
| `tests/stages/test_stage01_run_stage_smoke.py` | No change | (listed to confirm no cross-stage test edits needed) |
| `configs/stages/04_diagnostics_ablation.yaml` | Create | frozen execution parameters (T4) |
| `tests/contracts/test_stage04_config_contract.py` | Create | config contract gates (T5) |
| `src/lst_models/stages/diagnostics_ablation.py` | Create | `run_stage(config)` (T6-T9) |
| `tests/stages/test_stage04_run_stage_smoke.py` | Create | gate/behavior/schema tests (T6-T9) |
| `notebooks/04_diagnostics_ablation_colab.ipynb` | Create | user-facing execution surface (T11) |
| `scripts/notebooks/generate_04_diagnostics_ablation_colab.py` | Create | agent notebook generator (T11) |
| `tests/notebooks/test_stage04_notebook_static.py` | Create | static gate (T11) |
| `docs/lst_models_v2_route_roadmap.md` | Modify | check off Phase 5 items (T12) |

Size targets (guide §10 + AGENTS.md ratchet): stage module ≤ 700 LOC,
`run_stage` body ≤ 90 lines, each new model builder ≤ ~60 LOC, metrics.py
additions ≤ ~150 LOC.

---

## 1. Frozen Boundaries (D3 recap — nothing below may weaken these)

From `04_diagnostics_ablation_protocol.md` §2-8, frozen 2026-06-09, readout
executed 2026-06-10 — these are now unchangeable:

1. Stage 04 reads frozen Stage 03 artifacts only; new official-validation
   fit-predict events = 0. No refit, re-predict, re-threshold, recalibrate,
   or re-score of any model on official validation rows.
2. Ablations are exactly the four Stage 02 §7 tracked architectural controls
   (`dlinear_only`, `tcn_only`, `last_step_mlp`,
   `last_step_lightgbm_control`), fit and scored on Stage 02 train-inner
   folds ONLY, under Stage 02's fold/eligible-row/same-row-baseline
   contracts. They may not promote a control or demote the frozen candidate.
3. Calibration is measure-only (Guo et al. 2017 anchor): no Platt, isotonic,
   temperature scaling, or any fitted mapping on official validation.
4. Selective/no-trade diagnostics report whole risk-coverage curves and AURC
   (Geifman & El-Yaniv 2017; Geifman et al. 2019); no recommended operating
   point; `chosen threshold` is a forbidden string.
5. Robustness slices and failure analysis come from the frozen dump only.
6. Manifest contract: `official_validation_contact=read_frozen_artifacts_only`,
   `new_validation_fit_predict_events=0`, `holdout_test_contact=false`.
7. Wording: full Stage 03 forbidden list inherited (ten strings); allowed
   wording unchanged.
8. Stage 04 runs regardless of the Stage 03 outcome; the outcome here was
   `met_predeclared_validation_readout_criteria`, so downstream wording keeps
   validation-only claims.

---

## 2. Operational Decisions Fixed By This Plan (within the frozen core)

These are the Batch C operational choices the frozen core left open. They are
declared here BEFORE any Stage 04 artifact is produced and are copied into
protocol §9-14 by T1.

- [ ] **OD1 Calibration views, bins, and metrics.** Primary view: `p_up`
  probability calibration (predicted P(up) vs empirical up-frequency).
  Secondary view: top-label confidence `max(p_up, 1-p_up)` (Guo et al. 2017
  convention). Binning: equal-width primary with `n_bins=15`, sensitivity at
  10 and 20; equal-mass (quantile) binning as the adaptive variant (Nixon et
  al. 2019). Reported per seed (plus a descriptive seed-mean row; seeds are
  never pooled row-wise): `ece`, `mce`, `brier_score`, and the Murphy (1973)
  decomposition `brier_reliability − brier_resolution + brier_uncertainty`
  computed on the same bins (binning dependence stated as a caveat; plugin
  binned estimators are biased — Kumar et al. 2019 — reported as measured
  descriptive values, not population claims). Per-ticker ECE is a secondary
  slice with the same bins.
- [ ] **OD2 Same-row baseline reconstruction for slice deltas.** The dump
  has candidate predictions only; per-slice deltas need per-row baseline
  predictions. Mechanism: reconstruct `stratified_dummy_train_prior`
  per-row predictions by calling the SAME frozen helper
  (`metrics.predict_stratified_dummy(y_refit_labels, n_eval, seed)`) with the
  rebuilt official-train refit labels (the ablation arm rebuilds the train
  event list anyway), in dump row order per seed. Dual equality gates make
  this reconstruction-or-nothing: (a) pooled macro-F1/accuracy/MCC of the
  reconstructed draw must equal the frozen `03_same_row_baselines.csv` row to
  ≤ 1e-9, AND (b) per-ticker candidate-vs-dummy deltas recomputed from the
  reconstruction must equal the frozen `03_per_ticker_readout.csv` deltas to
  ≤ 1e-9 (5 tickers × 2 seeds). On any mismatch the reconstruction is
  REJECTED whole: every stratified-dummy slice delta outside the frozen
  ticker level and every LOO sign-flip flag is emitted as
  `not_computed_due_to_baseline_reconstruction_mismatch` (no analytic
  expectation substitute — realized-draw and expectation deltas must never
  mix in one artifact). Ticker-level dummy deltas are always sourced
  verbatim from the frozen `03_per_ticker_readout.csv` regardless of
  reconstruction outcome. `baseline_reconstruction_status`
  (`verified_identical` | `mismatch_deltas_not_computed`) is recorded in the
  diagnostics report, and every slice row carries a `delta_source` column
  (`reconstructed_realized` | `frozen_stage03_artifact` |
  `analytic_constant_prediction` |
  `not_computed_due_to_baseline_reconstruction_mismatch`). Reconstruction
  is a deterministic replay of frozen evidence (train labels + frozen seed),
  involves no model and no new information, and is NOT a validation scoring
  event (precedent: Stage 03 baseline rows were not events).
  `majority_train_prior`, `constant_up`, `constant_down` per-slice values
  are exact analytic values of deterministic constant predictions (not
  expectations) and are unaffected by the reconstruction outcome.
- [ ] **OD3 Ablation scope and budget.** Controls run on the frozen
  primary's candidate input ONLY (`price_volume_time_w20`) — the ablation
  question is "which architectural ingredient of the frozen primary carries
  its train-inner signal", not a second search. Fold/row contract: Stage 02's
  3 chronological train-inner folds, seeds `[101, 202]`, 50k/20k
  `deterministic_even_stride_by_ticker_label` caps, same-row baselines.
  Budget formula (Stage 02 §8 style):
  `planned_rows = 4 controls × 1 candidate_input × 3 folds × 2 seeds = 24 ≤
  max_ablation_plan_rows 32`. Predeclared params per control (zero new HPO;
  every value is a deterministic copy from frozen artifacts or a fixed config
  literal):
  - `tcn_only`: the frozen primary's exact profile params from
    `03_decision_record.json → primary_candidate.hpo_profile_params`
    (`channels [16,16]`, `kernel_size 2`, `dropout 0.0`, `lr 0.001`,
    `wd 0.0001`). Builder: existing `TCNTiny`. Reading: fresh fits of the
    primary architecture under control labeling (also a seed-stability
    replication of the primary's train-inner behavior).
  - `dlinear_only`: the multi-scale DLinear branch of the hybrid alone.
    Params source: `02_best_params_by_family.json["ms_dlinear_tcn"]` —
    keep `moving_avg_kernels`, `dropout`, `learning_rate`, `weight_decay`;
    drop `tcn_channels`, `tcn_kernel_size`; record the resolved profile id
    and the derivation in the plan ledger. Builder: new `MSDLinearOnlyTiny`.
  - `last_step_mlp`: fixed literals in the Stage 04 config — `hidden_size
    32`, `dropout 0.10`, `learning_rate 0.001`, `weight_decay 0.0001`;
    consumes ONLY the window's last bar (window-depth control). Builder: new
    `LastStepMLPTiny`.
  - `last_step_lightgbm_control`: params source
    `02_best_params_by_family.json["lightgbm"]` (resolved profile id
    recorded), applied to the last bar's feature columns only.
  Same training defaults as Stage 02 (byte-equal config blocks, asserted by
  the contract test). Class weights recomputed per fold fit-subset, as in
  Stage 02.
- [ ] **OD4 Reference rows, not refits.** The frozen primary's train-inner
  evidence is JOINED read-only from `02_hpo_trial_ledger.csv` filtered to
  `(candidate_id=price_volume_time_w20, model_family=tcn,
  hpo_profile_id=tcn_p01)` — exactly 6 completed rows (3 folds × 2 seeds);
  any other count is a hard error. No primary refit happens in Stage 04.
- [ ] **OD5 Volatility-state proxy is dump-native.** Frozen §6 requires
  failure analysis "from the frozen dump only", so realized-vol from raw
  validation-period bars is out of scope (a raw-bar vol slice is recorded as
  a V2.1-eligible item). Predeclared proxy: per `(ticker, trading_day)`
  eligible-row count terciles (computed per ticker over its validation
  trading days; eligible rows = band-exceeding labels, so day-level row
  density proxies band-pass activity). Named `activity_tercile` in all
  artifacts and explicitly NOT called realized volatility.
- [ ] **OD6 SHAP/permutation importance: deferred.** The route guide stage
  table mentions "SHAP/permutation" for Stage 04; the frozen D3 core does
  not include it. Validation-side permutation/SHAP would create new
  prediction events on official validation rows (forbidden). Train-inner
  permutation importance would be allowed scope-wise but adds heavy compute
  with no decision value for a frozen route. Decision: deferred, recorded as
  a V2.1-eligible item in protocol §14 and the diagnostics report. Not
  implemented in Batch C.
- [ ] **OD7 Figures are notebook-rendered; CSVs are canonical.** nb04
  display cells render a reliability diagram and risk-coverage curve from
  the CSV artifacts (compact, matplotlib). No PNG is a required artifact;
  Stage 05 produces thesis figures from the frozen CSVs.
- [ ] **OD8 Uncertainty context device is unchanged.** Only the already
  frozen trading-day block bootstrap
  (`metrics.block_bootstrap_macro_f1_delta`, blocks = `ticker|trading_day`,
  1000 draws, seed 12345) is reported, on the pooled per-seed delta and
  per-ticker deltas (using OD2 reconstructed baseline rows). No new
  significance machinery (no McNemar, no DM test) — diagnostics must not
  acquire a second judgment device after the readout.
- [ ] **OD9 Robustness concentration rule.** Per axis in `{ticker, seed,
  calendar_year}`: compute leave-one-slice-out pooled delta vs the
  reconstructed stratified dummy; flag `loo_sign_flip=true` when removing a
  single slice's rows turns the pooled delta ≤ 0. Additionally report each
  slice's `share_of_pooled_positive_delta` descriptively. Axes
  `{calendar_quarter, time_of_day_hour, activity_tercile}` are reported
  without the LOO flag (descriptive slices). Minimum slice size for failure
  tables: `n_rows ≥ 200`; failure tables list top-25 worst slices per axis
  by error rate among qualifying slices.

---

## Task 1: Complete protocol §9-14 (operational detail)

**Files:** Modify `docs/protocols/04_diagnostics_ablation_protocol.md`

- [ ] **Step 1.1** Replace §9 ("Operational Detail (to be completed in Batch
  C)") with the full operational sections, leaving §1-8 byte-identical:
  - §9 Inputs And Entry Gates: the full gate list from T6 (exact run-id
    pins incl. Stage 03 `20260610_133305_716174`, inventory sha256
    verification, decision-record consistency, dump schema/row-count gate,
    holdout boundary assert, chain consistency, superseded-id rejection,
    rebuild parity for the ablation candidate input).
  - §10 Diagnostics Definitions: OD1, OD2, OD5, OD8, OD9 verbatim.
  - §11 Ablation Recipe: OD3, OD4 verbatim + budget formula + plan/trial
    ledger contract + "controls may not become thesis candidates" sentence
    from Stage 02 §7.
  - §12 Required Artifacts: the `REQUIRED_STAGE04_ARTIFACTS` list (T9 —
    twelve files: ten `04_*` artifacts + `run_manifest.json` +
    `artifact_inventory.csv`) with the exact column constants from T9
    (copy them in so doc and code freeze together).
    `drive_backup_manifest.json` is produced and uploaded LAST by the
    notebook save cell itself (AGENTS.md §5), so it is deliberately outside
    the pre-upload validation list; state this in §12.
  - §13 Execution Discipline: checkpoint cadence (after each control),
    Drive layout (`results/04_diagnostics_ablation/<run_id>/`,
    `checkpoints/04_diagnostics_ablation/<run_id>/`), exact-run-id resume
    (Stage 03 contract reuse), durable-save refusal conditions, pre-flight
    feasibility estimate (dump bytes + ablation materialized bytes vs
    predeclared cap) BEFORE any fit.
  - §14 Tests And Risks: the test triad + metrics golden tests; risk table
    = frozen §10 rows plus: reconstruction mismatch (→ OD2 fallback),
    reference-row count mismatch (→ hard error), control budget creep
    (→ formula + cap), partial-period misreading (→ `n_rows` columns).
- [ ] **Step 1.2** Keep the section freeze map sentence and extend it:
  "sections 9-14 were completed in Batch C after the readout, strictly
  within the §2-8 core; they bind Stage 04 execution from their commit
  forward."
- [ ] **Step 1.3 Commit point:**
  `docs(stage04): complete diagnostics-ablation protocol operational detail`.

## Task 2: `metrics.py` calibration + selective helpers

**Files:** Modify `src/lst_models/metrics.py`, modify
`tests/contracts/test_metrics.py`

```text
placement_decision:
  target_file_type: python_module
  target_path: src/lst_models/metrics.py
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: reusable, safety-critical, golden-testable metric logic
  why_not_utils: metrics.py is the domain home for metric functions
  safety_tests: tests/contracts/test_metrics.py
```

- [ ] **Step 2.1 Failing golden tests first** (hand-computed values, no
  sklearn dependence in expectations):

```python
def test_reliability_bins_and_ece_equal_width_golden() -> None:
    y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0])
    p_up = np.array([0.9, 0.8, 0.7, 0.65, 0.3, 0.2, 0.25, 0.1])
    bins = metrics.reliability_bins(y_true, p_up, n_bins=2, scheme="equal_width")
    # bin [0,0.5): rows {0.3,0.2,0.25,0.1} -> mean_p=0.2125, freq=1/4
    # bin [0.5,1]: rows {0.9,0.8,0.7,0.65} -> mean_p=0.7625, freq=3/4
    assert bins["n_rows"].tolist() == [4, 4]
    assert bins["mean_predicted"].tolist() == pytest.approx([0.2125, 0.7625])
    assert bins["empirical_frequency"].tolist() == pytest.approx([0.25, 0.75])
    ece = metrics.expected_calibration_error(bins)
    assert ece == pytest.approx(0.5 * 0.0375 + 0.5 * 0.0125)

def test_brier_decomposition_identity_golden() -> None:
    y_true = np.array([1, 0, 1, 0])
    p_up = np.array([0.8, 0.8, 0.4, 0.4])
    out = metrics.brier_score_decomposition(y_true, p_up, n_bins=2, scheme="equal_mass")
    assert out["brier_score"] == pytest.approx(np.mean((p_up - y_true) ** 2))
    recomposed = out["brier_reliability"] - out["brier_resolution"] + out["brier_uncertainty"]
    assert recomposed == pytest.approx(out["brier_score"], abs=1e-12)

def test_risk_coverage_and_aurc_golden() -> None:
    # confidence desc: c=[.9,.8,.7,.6], correct=[1,1,0,1]
    correct = np.array([1, 1, 0, 1], dtype=bool)
    confidence = np.array([0.9, 0.8, 0.7, 0.6])
    curve = metrics.risk_coverage_curve(confidence, correct)
    assert curve["coverage"].tolist() == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert curve["selective_risk"].tolist() == pytest.approx([0.0, 0.0, 1/3, 0.25])
    out = metrics.aurc_metrics(confidence, correct)
    assert out["aurc"] == pytest.approx(np.mean([0.0, 0.0, 1/3, 0.25]))
    # oracle: error sorted last -> risks [0,0,0,0.25]
    assert out["oracle_aurc"] == pytest.approx(0.0625)
    assert out["e_aurc"] == pytest.approx(out["aurc"] - 0.0625)
```

- [ ] **Step 2.2 Run** `E:/codex_workspace/_envs/py311_shared/python.exe -m
  pytest tests/contracts/test_metrics.py -q` → expected FAIL (missing
  attributes).
- [ ] **Step 2.3 Implement** in `metrics.py` (after the baseline helpers):
  - `reliability_bins(y_true, p_up, *, n_bins, scheme)` → DataFrame with
    `bin_index, bin_lower, bin_upper, n_rows, mean_predicted,
    empirical_frequency, abs_gap`; `scheme ∈ {"equal_width", "equal_mass"}`
    (equal-mass = quantile edges with duplicate-edge dedupe); empty bins
    dropped (recorded via `bin_index` gaps).
  - `expected_calibration_error(bins)` → Σ (n_b/N)·|freq_b − mean_pred_b|;
    `maximum_calibration_error(bins)` → max |gap|.
  - `brier_score_decomposition(y_true, p_up, *, n_bins, scheme)` → dict with
    `brier_score, brier_reliability, brier_resolution, brier_uncertainty`
    (Murphy 1973, computed on the same binning; identity holds exactly for
    binned decomposition with within-bin means).
  - `risk_coverage_curve(confidence, correct, *, tie_break=None)` → full
    per-row prefix curve sorted by confidence desc with deterministic
    tie-break (caller passes `sample_id` order); columns `coverage,
    n_covered, confidence_at_coverage, selective_risk, selective_accuracy`.
  - `aurc_metrics(confidence, correct)` → `{aurc, oracle_aurc, e_aurc,
    full_coverage_risk}`; AURC = mean selective risk over the full-resolution
    per-row curve (Geifman et al. 2019); oracle = same error count sorted
    worst-last; E-AURC = AURC − oracle AURC.
  - Top-label view helper: `top_label_confidence(p_up)` → `max(p_up, 1−p_up)`
    with predicted label `(p_up >= 0.5)` (ties to class 1, documented).
- [ ] **Step 2.4 Run again** → PASS. Commit point:
  `feat(metrics): calibration and selective-prediction measurement helpers`.

## Task 3: Control builders + fitting dispatch

**Files:** Create `src/lst_models/models/ms_dlinear_only.py`,
`src/lst_models/models/last_step_mlp.py`; modify `src/lst_models/fitting.py`;
add tests in `tests/stages/test_stage04_run_stage_smoke.py` (fitting-level
tests may live in a `tests/contracts/test_fitting_controls.py` if cleaner).

```text
placement_decision:
  target_file_type: python_module
  target_path: src/lst_models/models/*.py + src/lst_models/fitting.py
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: model builders and fit dispatch are reused by run_stage and tests
  why_not_utils: models/ is the builder home; fitting.py is the fit-dispatch home
  safety_tests: last-bar slice contract test, control dispatch tests, CPU-safe
```

- [ ] **Step 3.1 Failing test — last-bar slice contract** (the load-bearing
  correctness fact for both last-step controls;
  `windows.materialize_window_matrix` flattens time-major via
  `window.reshape(-1)`, so the last bar is the LAST `n_features` columns):

```python
def test_last_bar_slice_matches_unflattened_window() -> None:
    # synthetic dataset: window=3, features=2, values encode (t, f)
    x_flat = np.array([[t * 10 + f for t in range(3) for f in range(2)]], dtype=np.float32)
    last = fitting.last_bar_slice(x_flat, n_features=2)
    assert last.tolist() == [[20.0, 21.0]]  # t=2 rows only
```

- [ ] **Step 3.2 Implement builders.**
  - `MSDLinearOnlyTiny(window_size, n_features, defaults)`: copy the
    multi-scale trend/residual head structure from `ms_dlinear_tcn.py`
    (reuse `moving_average_same` + `odd_kernel_within_window` imports), mean
    the per-scale summed logits, return them directly (no TCN branch, no mix
    layer). Consumes `moving_avg_kernels`, `dropout`.
  - `LastStepMLPTiny(n_features, defaults)`: `Linear(n_features, hidden) →
    ReLU → Dropout → Linear(hidden, 2)`; consumes `hidden_size`, `dropout`.
- [ ] **Step 3.3 Extend `fitting.py`.**
  - `last_bar_slice(x_flat, n_features)` → `x_flat[:, -n_features:]`
    (with a width-divisibility assert).
  - Extend `fit_torch_sequence_probe` model dispatch with
    `"ms_dlinear_only_tiny"` and `"last_step_mlp_tiny"` (the latter slices
    to the last bar before tensor reshape and trains on `(n, n_features)`).
  - Extend `fit_probe` dispatch: `"ms_dlinear_only_tiny"`,
    `"last_step_mlp_tiny"` route to the torch path;
    `"last_step_lightgbm_control"` slices via `last_bar_slice` then reuses
    `fit_lightgbm_probe`. `fitting.py` gains ONLY generic probe
    implementations and `last_bar_slice` — nothing Stage 04-specific.
  - `CONTROL_PROBE_BY_ID = {"dlinear_only": "ms_dlinear_only_tiny",
    "tcn_only": "tcn_tiny", "last_step_mlp": "last_step_mlp_tiny",
    "last_step_lightgbm_control": "last_step_lightgbm_control"}` lives in
    `src/lst_models/stages/diagnostics_ablation.py` (T6+): the control-id →
    probe-id mapping is Stage 04 ledger/orchestration semantics, not a
    shared fitting helper (route guide layering; AGENTS.md anti-spaghetti).
    The config `ablation.controls.<id>.probe_id` values must match it.
  - All early-stopping/device/provenance behavior is inherited unchanged
    (chronological-tail early stopping, `ProbeFitResult` fields).
- [ ] **Step 3.4 Dispatch tests** (env-gated torch skips where needed,
  pattern: existing fitting tests): each control id produces a completed fit
  on a tiny two-class fixture; `tcn_only` routes to `TCNTiny`;
  `last_step_lightgbm_control` receives `n_features`-wide x (spy on
  `LGBMClassifier.fit`). Run → PASS.
- [ ] **Step 3.5 Commit point:**
  `feat(fitting,models): four stage04 architectural-control builders + dispatch`.

## Task 4: Stage 04 config

**Files:** Create `configs/stages/04_diagnostics_ablation.yaml`

- [ ] **Step 4.1 Write the config** (complete; run ids are frozen pins, the
  ONLY permitted later edit is a documented Stage 03 supersession, which
  would itself be a route event):

```yaml
stage_name: 04_diagnostics_ablation
route: lst_models
scope: validation_only
holdout_test_contact: false
official_validation_contact: read_frozen_artifacts_only
official_validation_for_selection: false
new_validation_fit_predict_events: 0

inputs:
  stage00_run_id: "20260610_051705_347450"
  stage00_runtime_run_dir: /content/lst_models_results/00_data_split_label_freeze/20260610_051705_347450
  stage00_drive_path_parts: [lst_models, results, 00_data_split_label_freeze, "20260610_051705_347450"]
  required_stage00_artifacts:
    - raw_data_manifest.json
    - split_freeze.json
    - label_policy.json
    - baseline_registry.json
    - sample_event_index.csv
    - run_manifest.json
    - artifact_inventory.csv
  stage01_run_id: "20260610_075002"
  stage01_runtime_run_dir: /content/lst_models_results/01_feature_window_search/20260610_075002
  stage01_drive_path_parts: [lst_models, results, 01_feature_window_search, "20260610_075002"]
  required_stage01_artifacts:
    - run_manifest.json
    - artifact_inventory.csv
    - 01_candidate_inputs.json
    - 01_feature_window_search_summary.csv
  stage02_run_id: "20260610_082130_797479"
  stage02_runtime_run_dir: /content/lst_models_results/02_model_hpo_train_inner/20260610_082130_797479
  stage02_drive_path_parts: [lst_models, results, 02_model_hpo_train_inner, "20260610_082130_797479"]
  superseded_stage02_run_ids: ["20260609_100637_704705", "20260610_010019_507648"]
  required_stage02_artifacts:
    - run_manifest.json
    - artifact_inventory.csv
    - 02_hpo_plan_ledger.csv
    - 02_hpo_trial_ledger.csv
    - 02_baseline_control_summary.csv
    - 02_frozen_candidate.json
    - 02_best_params_by_family.json
    - 02_stage03_handoff.json
  stage03_run_id: "20260610_133305_716174"
  stage03_runtime_run_dir: /content/lst_models_results/03_frozen_validation_readout/20260610_133305_716174
  stage03_drive_path_parts: [lst_models, results, 03_frozen_validation_readout, "20260610_133305_716174"]
  required_stage03_artifacts:
    - run_manifest.json
    - artifact_inventory.csv
    - 03_validation_readout.csv
    - 03_per_ticker_readout.csv
    - 03_seed_summary.csv
    - 03_same_row_baselines.csv
    - 03_validation_predictions.csv
    - 03_decision_record.json
  raw_data_manifest: configs/lst_models_data.yaml
  raw_data_dir: /content/lst_models_raw_stock_data
  notebook_path: notebooks/04_diagnostics_ablation_colab.ipynb

outputs:
  output_dir: /content/lst_models_results/04_diagnostics_ablation
  manifest: run_manifest.json
  artifact_inventory: artifact_inventory.csv
  calibration_summary: 04_calibration_summary.csv
  reliability_bins: 04_reliability_bins.csv
  risk_coverage_curve: 04_risk_coverage_curve.csv
  selective_summary: 04_selective_summary.csv
  robustness_slices: 04_robustness_slices.csv
  failure_slices: 04_failure_slices.csv
  ablation_plan_ledger: 04_ablation_plan_ledger.csv
  ablation_trial_ledger: 04_ablation_trial_ledger.csv
  ablation_summary: 04_ablation_summary.csv
  diagnostics_report: 04_diagnostics_report.json

diagnostics:
  source: stage03_validation_predictions_only
  expected_dump_rows: 302128
  expected_seeds: [101, 202]
  calibration:
    probability_views: [p_up, top_label_confidence]
    primary_view: p_up
    binning_schemes: [equal_width, equal_mass]
    primary_scheme: equal_width
    bin_counts: [10, 15, 20]
    primary_bin_count: 15
    no_calibrator_fitting: true
  selective:
    confidence_score: top_label_confidence
    risk_definition: one_minus_accuracy_on_covered_rows
    curve_resolution: per_row_full_resolution
    csv_coverage_grid_step: 0.005
    csv_coverage_grid_minimum: 0.05
    report_macro_f1_on_covered_rows: true
    no_operating_point: true
  baseline_reconstruction:
    enabled: true
    baseline_id: stratified_dummy_train_prior
    equality_tolerance: 1.0e-9
    pooled_gate_artifact: 03_same_row_baselines.csv
    per_ticker_gate_artifact: 03_per_ticker_readout.csv
    on_mismatch: mark_not_computed_keep_frozen_ticker_rows
  robustness_slices:
    slice_axes: [ticker, seed, calendar_year, calendar_quarter, time_of_day_hour, activity_tercile]
    loo_sign_flip_axes: [ticker, seed, calendar_year]
    activity_proxy: eligible_rows_per_ticker_trading_day_terciles
  failure_slices:
    slice_axes: [ticker_hour, ticker_trading_day, activity_tercile, calendar_month]
    minimum_slice_rows: 200
    top_k_per_axis: 25
  bootstrap:
    device: trading_day_block_bootstrap
    block_id: ticker_trading_day
    iterations: 1000
    seed: 12345

ablation:
  candidate_input: price_volume_time_w20
  fold_source: stage02_train_inner_contract
  n_folds: 3
  seeds: [101, 202]
  hpo_sample_policy:
    max_train_samples_per_fold: 50000
    max_eval_samples_per_fold: 20000
    sample_method: deterministic_even_stride_by_ticker_label
  controls:
    tcn_only:
      probe_id: tcn_tiny
      params_source: stage03_decision_record_primary_hpo_profile_params
    dlinear_only:
      probe_id: ms_dlinear_only_tiny
      params_source: stage02_best_params_by_family_ms_dlinear_tcn_dlinear_branch
      dropped_keys: [tcn_channels, tcn_kernel_size]
    last_step_mlp:
      probe_id: last_step_mlp_tiny
      params_source: fixed_in_config
      fixed_params:
        hidden_size: 32
        dropout: 0.10
        learning_rate: 0.001
        weight_decay: 0.0001
    last_step_lightgbm_control:
      probe_id: last_step_lightgbm_control
      params_source: stage02_best_params_by_family_lightgbm
  budget:
    max_ablation_plan_rows: 32
  reference_rows:
    source: 02_hpo_trial_ledger.csv
    candidate_id: price_volume_time_w20
    model_family: tcn
    hpo_profile_id: tcn_p01
    expected_row_count: 6
  same_row_baselines:
    mandatory:
      - stratified_dummy_train_prior
      - majority_train_prior
      - constant_up
      - constant_down
    sample_hash_parity_artifact: 02_hpo_plan_ledger.csv

lightgbm_training_defaults:
  eval_metric: binary_logloss
  early_stopping_rounds: 25
  early_stopping_validation_source: inner_train_chronological_tail
  early_stopping_validation_fraction: 0.2
  minimum_early_stopping_train_samples: 128
  minimum_early_stopping_validation_samples: 128

probe_training_defaults:
  torch:
    epochs: 64
    batch_size: 1024
    learning_rate: 0.001
    weight_decay: 0.0001
    device: auto
    require_gpu: false
    optimizer: AdamW
    loss: class_weighted_cross_entropy
    early_stopping: inner_train_chronological_tail
    early_stopping_validation_fraction: 0.2
    minimum_early_stopping_train_samples: 128
    minimum_early_stopping_validation_samples: 128
    early_stopping_patience: 8
    early_stopping_min_delta: 0.0
    gradient_clip_norm: 1.0

checkpointing:
  enabled: true
  checkpoint_after_each_control: true
  checkpoint_dir: /content/lst_models_checkpoints/04_diagnostics_ablation
  checkpoint_drive_path_parts: [lst_models, checkpoints, 04_diagnostics_ablation]

resume:
  enabled: false
  run_id: null
  checkpoint_dir: null

forbidden:
  wording:
    - final model
    - official validation winner
    - holdout winner
    - test winner
    - proved best model
    - generalization proven
    - profitable
    - holdout-ready
    - selected by official validation
    - chosen threshold
```

  The two training-defaults blocks are byte-equal copies of the Stage 02/03
  frozen values; T5 asserts the equality so drift is impossible.
- [ ] **Step 4.2 Commit point:** `feat(stage04): diagnostics-ablation config`.

## Task 5: Config contract test

**Files:** Create `tests/contracts/test_stage04_config_contract.py`

- [ ] **Step 5.1 Write the tests** (loading pattern of
  `test_stage03_config_contract.py`):

```python
CONFIG = load_yaml(REPO_ROOT / "configs/stages/04_diagnostics_ablation.yaml")
STAGE02_CONFIG = load_yaml(REPO_ROOT / "configs/stages/02_model_hpo_train_inner.yaml")
STAGE03_CONFIG = load_yaml(REPO_ROOT / "configs/stages/03_frozen_validation_readout.yaml")

def test_scope_and_zero_event_flags() -> None:
    assert CONFIG["scope"] == "validation_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["official_validation_contact"] == "read_frozen_artifacts_only"
    assert CONFIG["official_validation_for_selection"] is False
    assert CONFIG["new_validation_fit_predict_events"] == 0

def test_upstream_run_id_chain_matches_stage03_config() -> None:
    inputs = CONFIG["inputs"]
    assert inputs["stage03_run_id"] == "20260610_133305_716174"
    for key in ("stage00_run_id", "stage01_run_id", "stage02_run_id"):
        assert inputs[key] == STAGE03_CONFIG["inputs"][key]
    assert inputs["stage02_run_id"] not in inputs["superseded_stage02_run_ids"]
    assert inputs["stage03_run_id"] in inputs["stage03_runtime_run_dir"]

def test_frozen_training_defaults_match_stage02() -> None:
    assert CONFIG["lightgbm_training_defaults"] == STAGE02_CONFIG["lightgbm_training_defaults"]
    assert CONFIG["probe_training_defaults"]["torch"] == (
        STAGE02_CONFIG["probe_training_defaults"]["torch"]
    )

def test_ablation_budget_arithmetic_closes() -> None:
    ablation = CONFIG["ablation"]
    planned = len(ablation["controls"]) * 1 * ablation["n_folds"] * len(ablation["seeds"])
    assert planned == 24
    assert planned <= ablation["budget"]["max_ablation_plan_rows"]
    assert set(ablation["controls"]) == {
        "dlinear_only", "tcn_only", "last_step_mlp", "last_step_lightgbm_control",
    }
    assert ablation["candidate_input"] == "price_volume_time_w20"
    assert ablation["seeds"] == [101, 202]
    assert ablation["hpo_sample_policy"] == STAGE02_CONFIG["hpo_sample_policy"]

def test_diagnostics_measure_only_flags() -> None:
    diag = CONFIG["diagnostics"]
    assert diag["source"] == "stage03_validation_predictions_only"
    assert diag["calibration"]["no_calibrator_fitting"] is True
    assert diag["selective"]["no_operating_point"] is True
    assert diag["expected_dump_rows"] == 302128
    assert diag["baseline_reconstruction"]["on_mismatch"] == (
        "mark_not_computed_keep_frozen_ticker_rows"
    )

def test_required_artifact_list_closes_with_runner_constant() -> None:
    from lst_models.stages.diagnostics_ablation import REQUIRED_STAGE04_ARTIFACTS
    outputs = CONFIG["outputs"]
    stage_artifacts = sorted(
        value for key, value in outputs.items() if key not in ("output_dir",)
    )
    assert sorted(REQUIRED_STAGE04_ARTIFACTS) == stage_artifacts
    assert len(REQUIRED_STAGE04_ARTIFACTS) == 12
    assert "drive_backup_manifest.json" not in REQUIRED_STAGE04_ARTIFACTS

def test_checkpoint_drive_contract_declared() -> None:
    checkpointing = CONFIG["checkpointing"]
    assert checkpointing["checkpoint_drive_path_parts"] == [
        "lst_models", "checkpoints", "04_diagnostics_ablation",
    ]
    assert checkpointing["checkpoint_after_each_control"] is True

def test_required_artifacts_and_wording() -> None:
    outputs = CONFIG["outputs"]
    for key in ("calibration_summary", "reliability_bins", "risk_coverage_curve",
                "selective_summary", "robustness_slices", "failure_slices",
                "ablation_plan_ledger", "ablation_trial_ledger",
                "ablation_summary", "diagnostics_report"):
        assert outputs[key].startswith("04_")
    for phrase in ["chosen threshold", "selected by official validation", "final model"]:
        assert phrase in CONFIG["forbidden"]["wording"]
    assert CONFIG["ablation"]["reference_rows"]["expected_row_count"] == 6
```

- [ ] **Step 5.2 Run** → PASS against the T4 config. Commit point:
  `test(stage04): config contract`.

## Task 6: Runner — config validation, entry gates, dump load

**Files:** Create `src/lst_models/stages/diagnostics_ablation.py`; create
`tests/stages/test_stage04_run_stage_smoke.py`

Imports: domain modules ONLY (`artifacts`, `config`, `data`, `features`,
`splits`, `windows`, `fitting`, `metrics`, `device`). NO
`from lst_models.stages import frozen_validation_readout` — the module
structure gate (`tests/contracts/test_module_structure.py`) enforces this.

Size-ratchet enforcement (finding from the 2026-06-10 plan review): the
stage module is orchestration ONLY. Before writing Stage 04 gate code,
identify the Stage 03 runner helpers Stage 04 also needs — at minimum the
inventory-verified run-folder artifact loading and the
manifest-flag/run-id-chain assertion helpers — and MOVE them to
`artifacts.py` as shared domain functions (move-not-copy; Stage 03 runner
and its smoke suite updated to import them in the same task, suite kept
green). Metric math stays in `metrics.py` (T2), fit mechanics in
`fitting.py` (T3), builders in `models/` (T3). Per-section LOC budget for
`diagnostics_ablation.py`: gates+loaders ≤ 150, diagnostics orchestration
≤ 200, ablation orchestration ≤ 200, artifacts/manifest ≤ 120, constants
+ `run_stage` ≤ 90 — total within the 700-line ratchet with margin. If any
section exceeds its budget, extract to the named domain module BEFORE
continuing, not after.

- [ ] **Step 6.1 Failing gate tests first.** Fixture: extend the Stage 03
  smoke fixture pattern with a fake Stage 03 run folder containing a small
  synthetic dump (two seeds × ~600 rows, 5 tickers, several trading days,
  p_up values spanning bins), `03_decision_record.json`,
  `03_same_row_baselines.csv`, `03_per_ticker_readout.csv`,
  `03_seed_summary.csv`, `03_validation_readout.csv`, manifest + inventory
  with real sha256 values. The fixture's dummy-baseline rows are GENERATED
  with `metrics.predict_stratified_dummy` so the OD2 reconstruction gate can
  pass end-to-end on the fixture.

```python
def test_blocks_when_readout_incomplete(stage_dirs) -> None:
    stage_dirs.write_stage03_decision_record(readout_complete=False)
    with pytest.raises(ValueError, match="readout_complete"):
        run_stage(stage_dirs.config())

def test_blocks_on_run_id_chain_mismatch(stage_dirs) -> None:
    stage_dirs.write_stage03_decision_record(source_stage02_run_id="wrong_id")
    with pytest.raises(ValueError, match="run id"):
        run_stage(stage_dirs.config())

def test_blocks_on_superseded_stage02_run_id(stage_dirs) -> None:
    config = stage_dirs.config()
    config["inputs"]["stage02_run_id"] = config["inputs"]["superseded_stage02_run_ids"][0]
    with pytest.raises(ValueError, match="superseded"):
        run_stage(config)

def test_blocks_on_dump_schema_or_rowcount_mismatch(stage_dirs) -> None:
    stage_dirs.corrupt_dump_drop_column("p_up")
    with pytest.raises(ValueError, match="03_validation_predictions"):
        run_stage(stage_dirs.config())

def test_blocks_on_holdout_boundary_row(stage_dirs) -> None:
    stage_dirs.poison_dump_with_row(target_timestamp="2017-01-25T10:00:00")
    with pytest.raises(ValueError, match="2017-01-25"):
        run_stage(stage_dirs.config())
```

- [ ] **Step 6.2 Implement** `_validate_config` (stage_name, scope, contact
  flags incl. the literal `read_frozen_artifacts_only`, zero-event field,
  diagnostics/ablation blocks present, budget formula recomputed),
  `_verify_entry_gates(config)` → `Stage04Inputs` dataclass implementing:
  exact Stage 00/01/02/03 folders by run id; `require_artifacts` with
  inventory sha256 verification for all four; decision-record gates
  (`readout_complete=true`, `holdout_test_contact=false`,
  `official_validation_for_selection=false`,
  `official_validation_scoring_events == len(scoring_event_ledger)`, seeds
  == config `diagnostics.expected_seeds`); chain consistency (decision
  record `source_stage0X_run_id` == config ids); superseded-id rejection;
  plan-vs-trial ledger sha256 difference (Stage 02 packaging proof, same as
  Stage 03 gate 5); dump gates (exact column set, row count ==
  Σ ledger `n_rows` == `expected_dump_rows` in production config, single
  `candidate_role="primary"`, `scope` uniform, max `target_timestamp` <
  2017-01-25, seeds exactly the frozen pair).
- [ ] **Step 6.3 Dump loader** `_load_frozen_predictions(config, inputs)` →
  DataFrame with parsed timestamps + derived columns `correct`,
  `confidence` (top-label), `calendar_year`, `calendar_quarter`,
  `time_of_day_hour`, `calendar_month`; derivations are pure dump
  transformations (no external data). Run gate tests → PASS.
- [ ] **Step 6.4 Commit point:** `feat(stage04): entry gates + frozen dump loader`.

## Task 7: Runner — diagnostics arm

**Files:** Modify runner + smoke tests

- [ ] **Step 7.1 Failing tests:**

```python
def test_calibration_outputs_schema_and_views(stage_dirs) -> None:
    run_stage(stage_dirs.config())
    bins = pd.read_csv(stage_dirs.read_path("04_reliability_bins.csv"))
    assert set(bins["view"]) == {"p_up", "top_label_confidence"}
    assert set(bins["binning_scheme"]) == {"equal_width", "equal_mass"}
    summary = pd.read_csv(stage_dirs.read_path("04_calibration_summary.csv"))
    assert list(summary.columns) == CALIBRATION_SUMMARY_COLUMNS
    assert (summary["scope"] == "validation_only").all()

def test_risk_coverage_never_marks_an_operating_point(stage_dirs) -> None:
    run_stage(stage_dirs.config())
    curve = pd.read_csv(stage_dirs.read_path("04_risk_coverage_curve.csv"))
    assert list(curve.columns) == RISK_COVERAGE_COLUMNS  # no recommended/selected column
    report = json.loads(stage_dirs.read_output("04_diagnostics_report.json"))
    assert report["no_reselection"] is True
    assert report["new_validation_fit_predict_events"] == 0

def test_baseline_reconstruction_equality_gate(stage_dirs) -> None:
    run_stage(stage_dirs.config())
    report = json.loads(stage_dirs.read_output("04_diagnostics_report.json"))
    assert report["baseline_reconstruction_status"] == "verified_identical"

def test_baseline_reconstruction_mismatch_never_mixes_delta_semantics(stage_dirs) -> None:
    stage_dirs.write_stage03_same_row_baselines(perturb_macro_f1=1e-3)
    run_stage(stage_dirs.config())
    report = json.loads(stage_dirs.read_output("04_diagnostics_report.json"))
    assert report["baseline_reconstruction_status"] == "mismatch_deltas_not_computed"
    slices = pd.read_csv(stage_dirs.read_path("04_robustness_slices.csv"))
    non_ticker = slices[slices["slice_axis"] != "ticker"]
    dummy_col = "delta_macro_f1_vs_stratified_dummy_train_prior"
    assert non_ticker[dummy_col].isna().all()
    assert (non_ticker["delta_source"]
            == "not_computed_due_to_baseline_reconstruction_mismatch").all()
    assert non_ticker["loo_sign_flip"].isna().all()
    ticker_rows = slices[slices["slice_axis"] == "ticker"]
    assert (ticker_rows["delta_source"] == "frozen_stage03_artifact").all()

def test_loo_sign_flip_flag_fires_on_single_carrier(stage_dirs_single_carrier) -> None:
    run_stage(stage_dirs_single_carrier.config())
    slices = pd.read_csv(stage_dirs_single_carrier.read_path("04_robustness_slices.csv"))
    ticker_rows = slices[slices["slice_axis"] == "ticker"]
    assert ticker_rows["loo_sign_flip"].any()
```

- [ ] **Step 7.2 Implement** `_run_diagnostics(dump, inputs, config)`:
  per-seed loops calling the T2 metric helpers for both views × schemes ×
  bin counts; seed-mean descriptive rows; per-ticker ECE; risk-coverage
  full-resolution curves with CSV downsampling to the 0.005 coverage grid
  (≥ 0.05) plus AURC/E-AURC at full resolution; OD2 reconstruction with the
  dual equality gates and analytic fallback path; OD9 slices with LOO flags
  and bootstrap context on (pooled, per-ticker) deltas; OD5 activity
  terciles; failure tables with min-n filter and top-k. Everything pure
  pandas/numpy — assert no torch/lightgbm import occurs in this arm (the
  smoke test monkeypatches `fitting.fit_probe` to raise if called before the
  ablation arm starts).
- [ ] **Step 7.3 Run tests → PASS.** Commit point:
  `feat(stage04): measure-only validation diagnostics arm`.

## Task 8: Runner — ablation arm (train-inner only)

**Files:** Modify runner + smoke tests

- [ ] **Step 8.1 Failing tests:**

```python
def test_ablation_plan_matches_budget_and_contracts(stage_dirs) -> None:
    run_stage(stage_dirs.config())
    plan = pd.read_csv(stage_dirs.read_path("04_ablation_plan_ledger.csv"))
    assert len(plan) == 4 * 1 * stage_dirs.n_folds * 2
    assert set(plan["control_id"]) == {
        "dlinear_only", "tcn_only", "last_step_mlp", "last_step_lightgbm_control"}
    assert (plan["candidate_id"] == "price_volume_time_w20").all()

def test_ablation_rows_share_stage02_sample_hashes(stage_dirs) -> None:
    run_stage(stage_dirs.config())
    plan = pd.read_csv(stage_dirs.read_path("04_ablation_plan_ledger.csv"))
    stage02_plan = stage_dirs.read_stage02_plan_ledger()
    merged = plan.merge(stage02_plan, on=["fold", "seed"], suffixes=("", "_02"))
    assert (merged["train_sample_id_hash"] == merged["train_sample_id_hash_02"]).all()
    assert (merged["eval_sample_id_hash"] == merged["eval_sample_id_hash_02"]).all()

def test_ablation_never_touches_validation_rows(stage_dirs, monkeypatch) -> None:
    validation_ids = set(stage_dirs.dump["sample_id"])
    real_fit = fitting.fit_probe
    def guard(probe_id, x_train, train_meta, x_eval, eval_meta, *args, **kwargs):
        assert not (set(eval_meta["sample_id"]) & validation_ids)
        assert not (set(train_meta["sample_id"]) & validation_ids)
        return real_fit(probe_id, x_train, train_meta, x_eval, eval_meta, *args, **kwargs)
    monkeypatch.setattr(fitting, "fit_probe", guard)
    run_stage(stage_dirs.config())

def test_reference_join_requires_exactly_six_rows(stage_dirs) -> None:
    stage_dirs.drop_stage02_trial_rows(model_family="tcn", keep=4)
    with pytest.raises(ValueError, match="reference"):
        run_stage(stage_dirs.config())

def test_checkpoint_manifest_contract_after_each_control(stage_dirs) -> None:
    run_stage(stage_dirs.config())
    manifest = json.loads(stage_dirs.read_checkpoint("checkpoint_manifest.json"))
    assert manifest["stage_name"] == "04_diagnostics_ablation"
    assert manifest["run_id"] == stage_dirs.run_id
    assert manifest["resume_instructions"]["resume_mode"] == "exact_run_checkpoint_only"
    assert manifest["resume_instructions"]["latest_parent_scan_allowed"] is False
    assert set(manifest["completed_controls"]) | set(manifest["pending_controls"]) == {
        "dlinear_only", "tcn_only", "last_step_mlp", "last_step_lightgbm_control"}

def test_resume_requires_exact_run_id_and_never_refits_completed_controls(
    stage_dirs, monkeypatch
) -> None:
    stage_dirs.run_until_controls_complete(["dlinear_only", "tcn_only"])
    config = stage_dirs.config()
    config["resume"] = {"enabled": True, "run_id": stage_dirs.run_id,
                        "checkpoint_dir": str(stage_dirs.checkpoint_dir)}
    fitted = []
    monkeypatch.setattr(fitting, "fit_probe", stage_dirs.recording_fit(fitted))
    run_stage(config)
    assert {call["control_id"] for call in fitted} == {
        "last_step_mlp", "last_step_lightgbm_control"}
    config_wrong = stage_dirs.config()
    config_wrong["resume"] = {"enabled": True, "run_id": "wrong_id",
                              "checkpoint_dir": str(stage_dirs.checkpoint_dir)}
    with pytest.raises(ValueError, match="run_id"):
        run_stage(config_wrong)
```

- [ ] **Step 8.2 Implement the rebuild + plan.** Rebuild bars → features →
  window dataset for `price_volume_time_w20` via the domain builders
  (`data`/`features`/`windows`), train events via
  `splits.valid_events_for_split(..., "train")`, folds via
  `splits.build_train_inner_folds(train_events, n_folds=3)`; per fold/seed:
  `windows.fold_indices` + `windows.cap_indices` (50k/20k) →
  `windows.sample_id_hash` for both sides; row-count parity vs
  `01_feature_window_search_summary.csv`
  (`windows.validate_rebuilt_candidate_counts`) and hash parity vs the
  Stage 02 plan ledger (hard error on mismatch — same-row comparability is
  the whole point). Write `04_ablation_plan_ledger.csv` BEFORE any fit
  (metrics-free, mirroring the Stage 02 plan-vs-trial separation).
- [ ] **Step 8.3 Implement the fit loop.** For each control × fold × seed:
  resolve params per OD3 (record `params_source_detail` + resolved profile
  id in the ledger), `fitting.fit_probe(CONTROL_PROBE_BY_ID[control], ...)`
  with the byte-equal training defaults; same-row baselines recomputed via
  `metrics.score_registry_baseline` on the capped fold rows; deltas vs both
  baselines; one compact progress line per completed control×fold×seed;
  local checkpoint + compact Drive-archive mirror after each control
  (`checkpoint_manifest.json` with `status=incomplete`, completed/pending
  controls, exact-run-id resume instructions — Stage 03 §11 contract
  reused). Exact-run resume: `resume.enabled` requires `run_id` +
  `checkpoint_dir`; never scan-latest.
- [ ] **Step 8.4 Reference join + summary.** Filter the frozen
  `02_hpo_trial_ledger.csv` to the six primary-family rows (OD4; hard error
  otherwise); write `04_ablation_summary.csv` per control with
  mean/min deltas, mean positive-ticker count, and the read-only reference
  columns; descriptive `gap_to_reference_mean_delta`. No ranking column, no
  promotion column.
- [ ] **Step 8.5 Run tests → PASS.** Commit point:
  `feat(stage04): train-inner architectural-control ablation arm`.

## Task 9: Runner — artifacts, manifest, diagnostics report

**Files:** Modify runner + smoke tests

- [ ] **Step 9.1 Column constants** (copied verbatim into protocol §12 by
  T1; every output row carries `scope="validation_only"`):

```python
CALIBRATION_SUMMARY_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "view", "binning_scheme",
    "n_bins", "n_rows", "ece", "mce", "brier_score", "brier_reliability",
    "brier_resolution", "brier_uncertainty", "mean_predicted",
    "base_rate_up", "scope",
]
RELIABILITY_BINS_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "view", "binning_scheme",
    "n_bins", "bin_index", "bin_lower", "bin_upper", "n_rows",
    "mean_predicted", "empirical_frequency", "abs_gap", "scope",
]
RISK_COVERAGE_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "coverage", "n_covered",
    "confidence_at_coverage", "selective_risk", "selective_accuracy",
    "selective_macro_f1", "scope",
]
SELECTIVE_SUMMARY_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "n_rows", "aurc",
    "oracle_aurc", "e_aurc", "full_coverage_risk", "full_coverage_macro_f1",
    "scope",
]
ROBUSTNESS_SLICES_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "slice_axis", "slice_value",
    "n_rows", "macro_f1", "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "delta_source",
    "share_of_pooled_positive_delta", "loo_pooled_delta", "loo_sign_flip",
    "bootstrap_delta_lcb", "bootstrap_delta_ucb", "scope",
]
FAILURE_SLICES_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "slice_axis", "slice_value",
    "n_rows", "error_count", "error_rate", "error_rate_lift_vs_seed_pooled",
    "support_up", "support_down", "scope",
]
ABLATION_PLAN_COLUMNS = [
    "control_id", "probe_id", "candidate_id", "feature_set", "window_size",
    "model_family", "params_source", "params_source_detail", "fold", "seed",
    "n_train_rows", "n_eval_rows", "train_sample_id_hash",
    "eval_sample_id_hash", "baseline_ids", "scope",
]
ABLATION_TRIAL_COLUMNS = ABLATION_PLAN_COLUMNS[:-1] + [
    "fit_status", "error_message", "macro_f1", "balanced_accuracy",
    "accuracy", "mcc", "roc_auc",
    "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "positive_ticker_count",
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason", "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash", "requested_device",
    "resolved_device", "device_fallback_reason", "scope",
]
ABLATION_SUMMARY_COLUMNS = [
    "control_id", "probe_id", "candidate_id", "n_trials", "n_completed",
    "mean_macro_f1", "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "min_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_delta_macro_f1_vs_majority_train_prior",
    "positive_ticker_count_mean", "reference_primary_family_mean_macro_f1",
    "reference_primary_family_mean_delta_vs_stratified_dummy",
    "gap_to_reference_mean_delta", "scope",
]

REQUIRED_STAGE04_ARTIFACTS = [
    "run_manifest.json",
    "artifact_inventory.csv",
    "04_calibration_summary.csv",
    "04_reliability_bins.csv",
    "04_risk_coverage_curve.csv",
    "04_selective_summary.csv",
    "04_robustness_slices.csv",
    "04_failure_slices.csv",
    "04_ablation_plan_ledger.csv",
    "04_ablation_trial_ledger.csv",
    "04_ablation_summary.csv",
    "04_diagnostics_report.json",
]
# Single source of truth for the required-output contract: the config outputs
# block, protocol section 12, the runner writer, the T5 closure test, and the
# nb04 durable-save validation all consume THIS list (12 names).
# drive_backup_manifest.json is written and uploaded last by the notebook
# save cell itself and is intentionally not part of the pre-upload list.
```

- [ ] **Step 9.2 Diagnostics report + manifest.**
  `04_diagnostics_report.json` fields: route, stage_name,
  source_stage00/01/02/03_run_id, superseded_stage02_run_ids,
  stage03_decision echo (`met_predeclared_validation_readout_criteria`),
  dump row counts per seed, `baseline_reconstruction_status`,
  concentration-flag summary (axes with any `loo_sign_flip`), ablation
  plan/completed counts per control, `new_validation_fit_predict_events=0`,
  `official_validation_scoring_events=0`, `no_reselection=true`,
  `no_final_model_selected=true`, `holdout_test_contact=false`,
  deferred-items list (`raw_bar_volatility_slice`,
  `shap_permutation_importance` → V2.1-eligible). Manifest mirrors the
  Stage 03 shape plus: `official_validation_contact="read_frozen_artifacts_only"`,
  `new_validation_fit_predict_events=0`,
  `official_validation_rows_read=<dump row count>` and
  `frozen_prediction_dump_read=true` (read-contact accounting is recorded
  separately from the fit-predict budget so the Stage 05 ledger cannot
  misread "zero events" as "zero validation contact"),
  `stage04_diagnostics_code_sha256` (sha256 over `inspect.getsource` of the
  T2 metric helpers + the runner's diagnostics/ablation entry functions),
  `feature_rebuild_code_sha256` match flag vs the Stage 02 manifest (ablation
  rebuild), device provenance fields (AGENTS.md §10), git-commit fields,
  config/notebook sha256, exact upstream run ids.
- [ ] **Step 9.3 Schema tests:** every output exists with exactly the
  declared columns; inventory sha256 covers all outputs; manifest field
  asserts; forbidden-wording scan over all written text artifacts (reuse the
  Stage 02/03 wording-gate helper if one exists, else a local scan in the
  smoke test). Run → PASS.
- [ ] **Step 9.4 Commit point:**
  `feat(stage04): artifacts + zero-event manifest + diagnostics report`.

## Task 10: Full suite + codegraph audit

- [ ] **Step 10.1 Run the full fast suite:**
  `E:/codex_workspace/_envs/py311_shared/python.exe -m pytest tests/data
  tests/stages tests/notebooks tests/contracts -q -rs` → expected green
  (env-gated torch skips allowed); Stage 01/02/03 suites must stay green
  untouched (any helper move per T6 keeps both call sites tested).
- [ ] **Step 10.2 Codegraph audit (mandatory: new stage entry point, ≥3
  modules touched):** `find_cycles` (expect none), `semantic_search` for
  duplicate metric/builder helper names before finalizing, `context` on
  `fitting.fit_probe` and `metrics.score_registry_baseline` callers. Record
  `codegraph: run` + summary in the task report, or `codegraph: unavailable`
  + fallback (`rg`, `py_compile`, targeted pytest) honestly.

## Task 11: Notebook + static gate

**Files:** Create `notebooks/04_diagnostics_ablation_colab.ipynb`,
`scripts/notebooks/generate_04_diagnostics_ablation_colab.py`,
`tests/notebooks/test_stage04_notebook_static.py`

- [ ] **Step 11.1 Generate the notebook** (pattern:
  `generate_03_frozen_validation_readout_colab.py`). Cell map:
  1. markdown — title, research question ("which architectural ingredient
     carries the frozen primary's train-inner signal, and how do the frozen
     validation predictions behave under calibration/selective/robustness
     diagnostics — with zero new validation contact"), frozen protocol
     summary, scope.
  2. bootstrap/config cell — `PROJECT_BOOTSTRAP_MODE="github_commit"`,
     `PROJECT_REPO_COMMIT=<full-bundle commit>` (two-step pin, T12).
  3. control cell — `RUN_STAGE04 = False`, `RUN_UPSTREAM_DRIVE_SYNC = False`,
     `RUN_STAGE04_DRIVE_BACKUP = True`; exact upstream run ids printed
     (00/01/02/03).
  4. config-load + TRUE runtime injection cell — inject `raw_data_dir`,
     `stage00/01/02/03_runtime_run_dir`, `output_dir`, `checkpoint_dir`
     BEFORE contract asserts (post-`0ff50c0` pattern).
  5. upstream sync cell — fetch the FOUR exact run folders from Drive by
     `*_drive_path_parts` + raw files by Drive file ID (duplicate match =
     hard error).
  6. pre-flight feasibility cell — dump size check + ablation materialized
     bytes estimate vs a predeclared cap BEFORE any fit; abort cleanly.
  7. run cell — `result = run_stage(stage04_config)` under `RUN_STAGE04`.
  8. durable save cell — immediately after; validate the twelve
     `REQUIRED_STAGE04_ARTIFACTS` (imported from the stage module, not
     retyped); REFUSE upload unless manifest records
     `new_validation_fit_predict_events == 0` AND
     `official_validation_contact == "read_frozen_artifacts_only"` AND
     `holdout_test_contact is False`; duplicate Drive folder/file matches
     under the exact target parent are hard errors (reuse the nb03 helper);
     Drive API upload + `drive_backup_manifest.json` (written and uploaded
     last, self-size null, outside the pre-upload validation list).
  9. display cells — compact calibration table + reliability diagram;
     risk-coverage curve plot (whole curve, no marked point); robustness
     slice table with LOO flags; ablation summary vs reference rows.
  10. markdown — honest interpretation template: validation-only wording
      reminder, "diagnosis, not selection" sentence, and the deferred-items
      list. No external-source (email/connector) references in the
      notebook: the executable surface cites only repo and Drive-run
      artifacts.
- [ ] **Step 11.2 Static gate** (pattern:
  `test_stage03_notebook_static.py`): parses; code cells AST-parse; outputs
  empty; `RUN_STAGE04 = False` enforced; pinned commit matches expected
  constant; exact run-id strings for all four upstream stages present;
  durable-save refusal conditions present; injection lines present;
  forbidden patterns absent — active holdout/test reads, `2017-01-25`
  outside the frozen boundary echo, selection-on-validation strings, the
  ten forbidden wording strings, AND calibrator-fitting tokens
  (`CalibratedClassifierCV`, `IsotonicRegression`, `temperature_scal`,
  `Platt`) anywhere in the notebook. Add the same calibrator-token scan
  over `src/lst_models/stages/diagnostics_ablation.py` as a contract test.
- [ ] **Step 11.3 Commit point:** `feat(stage04): colab notebook + static gate`.

## Task 12: Pin sequence + roadmap bookkeeping

- [ ] **Step 12.1** After user authorization: full-bundle commit
  (protocol+config+src+tests+notebook+generator), then the notebook-pin
  commit setting `PROJECT_REPO_COMMIT` (AGENTS.md §5 two-step pin); verify
  with `git ls-tree -r <pin> --name-only` that the pinned tree contains
  `docs/protocols/04_*`, `configs/stages/04_*`,
  `src/lst_models/stages/diagnostics_ablation.py`,
  `src/lst_models/models/ms_dlinear_only.py`,
  `src/lst_models/models/last_step_mlp.py`, `notebooks/04_*`, and the three
  test files. Update the static-gate expected-pin constant in the same
  commit.
- [ ] **Step 12.2** Roadmap: check off Phase 4 items 4.2/4.3 (Stage 03
  executed; run id recorded; Stage 04 pointers frozen) and Phase 5 C1-C6 as
  they land, with commit hashes. Record in the roadmap that Stage 04's
  validation scoring-event count is 0 by construction (feeds the Stage 05
  S5.1 budget ledger).
- [ ] **Step 12.3** Execution: user runs nb04 once on Colab GPU; durable
  save + diagnostics report verified before the session ends; record the
  Stage 04 run id in the roadmap and (when Batch D starts) the Stage 05
  config pointers.

---

## Self-Review Notes

- Spec coverage: roadmap C1 → OD1/T2/T7 (calibration, measure-only, Guo
  anchor); C2 → OD1/T2/T7 (risk-coverage/AURC whole curves, Geifman
  anchors); C3 → OD9/T7 (slices + LOO concentration flags); C4 → OD3/OD4/
  T3/T8 (four controls, train-inner only, same fold/row/baseline contracts,
  reference rows from frozen Stage 02 ledger); C5 → OD5/T7 (failure
  analysis, dump-native activity proxy); C6 → §1 recap + manifest fields +
  wording gates throughout. Protocol §9 completion → T1.
- The single genuinely novel mechanism is OD2 (baseline reconstruction with
  dual equality gates). It exists because per-slice deltas vs the stratified
  dummy are otherwise impossible without either re-scoring validation
  (forbidden) or silently switching to expectation values that would not
  reconcile with the frozen Stage 03 deltas. The fallback path is
  predeclared, mechanical, and visible in the diagnostics report.
- Reused symbols verified against HEAD during planning (2026-06-10):
  `splits.valid_events_for_split` / `splits.build_train_inner_folds` /
  `splits.FOLD_COLUMNS`; `windows.build_window_dataset` /
  `windows.materialize_window_matrix` (time-major flatten confirmed at
  `windows.py:102`) / `windows.fold_indices` / `windows.cap_indices` /
  `windows.sample_id_hash` / `windows.validate_rebuilt_candidate_counts`;
  `fitting.fit_probe` dispatch (`fitting.py:154-190`),
  `fitting.fit_torch_sequence_probe` model dispatch (`:315-320`),
  `fitting.PROBE_BY_FAMILY`, `fitting.lightgbm_hpo_params`,
  `fitting.probe_trial_config`, `fitting.torch_training_defaults`;
  `metrics.predict_stratified_dummy(y_train, n_eval, seed)` (`metrics.py:94`,
  deterministic given labels+seed — reconstruction feasibility),
  `metrics.predict_majority`, `metrics.score_registry_baseline`,
  `metrics.score_classifier`, `metrics.per_class_metrics`,
  `metrics.ticker_delta_macro_f1`, `metrics.block_bootstrap_macro_f1_delta`
  (block CI device, seed 12345); `artifacts.require_artifacts` /
  `write_json` / `write_artifact_inventory`. Re-verify at execution time.
- Type consistency: T9 column constants match T4 config output names, T5
  assertions, and T7/T8 writer dict keys; `CONTROL_PROBE_BY_ID` keys match
  the config `ablation.controls` keys and the protocol §11 list.
- Known tensions resolved: route guide mentions SHAP/permutation (OD6:
  deferred, reasons recorded); frozen §6 "dump only" vs realized-vol slicing
  (OD5: dump-native proxy); per-slice dummy deltas vs zero-event rule (OD2);
  `tcn_only` vs the already-run tcn family (OD3: control labeling +
  replication reading, never a candidate).
- Risks of this plan: OD2 alignment could fail against the real dump (dump
  row order vs Stage 03 eval order) → dual equality gates catch it; on
  mismatch the affected deltas/LOO flags are emitted as
  `not_computed_due_to_baseline_reconstruction_mismatch` (never an
  expectation substitute), so realized and expectation semantics can never
  mix in one artifact and every frozen Stage 03 number stays authoritative.
  Fixture-driven smoke tests cannot prove real-dump alignment — the
  production gates run at execution. Reference-row join could find ≠ 6 rows
  if the Stage 02 trial ledger schema drifted → hard error, no silent
  recovery.

## References

Frozen protocol anchors (committed before the readout):

- Guo, Pleiss, Sun & Weinberger 2017, "On Calibration of Modern Neural
  Networks", ICML (arXiv:1706.04599) — calibration measurement (ECE,
  reliability, top-label confidence convention).
- Geifman & El-Yaniv 2017, "Selective Classification for Deep Neural
  Networks" (arXiv:1705.08500) — risk-coverage trade-off, reject option.
- Geifman, Uziel & El-Yaniv 2019, "Bias-Reduced Uncertainty Estimation for
  Deep Neural Classifiers", ICLR (arXiv:1805.08206) — AURC / Excess-AURC.

Supplementary measurement context (verified 2026-06-10):

- Nixon, Dusenberry, Jerfel, Nguyen, Liu, Zhang & Tran 2019, "Measuring
  Calibration in Deep Learning" (arXiv:1904.01685) — adaptive (equal-mass)
  binning rationale; binning sensitivity reporting.
- Kumar, Liang & Ma 2019, "Verified Uncertainty Calibration", NeurIPS
  (arXiv:1909.10155) — plugin binned ECE estimators are biased; motivates
  reporting bin-count sensitivity and treating ECE as descriptive.
- Naeini, Cooper & Hauskrecht 2015, "Obtaining Well Calibrated Probabilities
  Using Bayesian Binning", AAAI — ECE formulation.
- Brier 1950 (Monthly Weather Review) — Brier score; Murphy 1973 —
  reliability/resolution/uncertainty decomposition.
- Zadrozny 2004, ICML — sample-selection bias: why Stage 02 capped-subsample
  absolute metrics and Stage 04 ablation absolute metrics are not comparable
  to Stage 03 full-row absolute metrics (deltas on identical rows only).
- Dwork et al. 2015, Science 349(6248) — reusable-holdout discipline; Stage
  04's zero-event rule is the project's enforcement of it.

Local knowledge base (`E:/codex_workspace/projects/hf_stock_ml_references2/`):
DLinear/TSLib/FEDformer/LTSF-Linear repos for the control builders (KB
warning honored: odd moving-average kernels only —
`odd_kernel_within_window` already enforces this); KB DO-NOT list applies to
Stage 04 prose: do not call DLinear-classification a "published standard";
do not present drop-neutral binary results as full-market deployment
performance.

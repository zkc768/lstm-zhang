# Stage 03 Protocol: Frozen Validation Readout

Status: pre-registered official-validation readout contract. Decisions D1-D4
were frozen by user sign-off on 2026-06-09
(`docs/lst_models_v2_route_roadmap.md` Phase 2) and are binding inputs to this
protocol.

This document is the pre-registration instrument for the one-shot Stage 03
readout. Stage 03 scores official-validation rows for the first time in the V2
route, exactly once per frozen seed and candidate, under decision rules that
are committed in this text before the readout executes. Sections 5 through 10
are frozen: changing any of them after a Stage 03 scoring event has occurred is
forbidden. A change would require a new pre-registered protocol revision and a
fresh run, recorded as such.

Stage sidecars covered by this contract:

```text
notebooks/03_frozen_validation_readout_colab.ipynb
configs/stages/03_frozen_validation_readout.yaml
src/lst_models/stages/frozen_validation_readout.py
docs/protocols/03_frozen_validation_readout_protocol.md
```

## 1. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- the target notebook, config, module, or test

Before writing code, the implementer MUST record:

```text
placement_decision:
  target_file_type: <notebook|stage_config|model_search_space|python_module|test|protocol|artifact>
  target_path: <exact intended path>
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: <required when creating Python helper code>
  why_not_utils: <required when creating Python helper code>
  safety_tests: <target tests or "not applicable">
```

For this protocol edit:

```text
placement_decision:
  target_file_type: protocol
  target_path: docs/protocols/03_frozen_validation_readout_protocol.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; this is a stage protocol document
  why_not_utils: not applicable; this is a stage protocol document
  safety_tests: static protocol/config/code consistency review
```

Implementation must preserve:

- Colab-first execution.
- One user-facing Stage 03 notebook.
- One Stage 03 config sidecar.
- One Stage 03 protocol sidecar.
- One `run_stage(config)` entry point.
- No holdout/test read, transform, window, score, or summary.
- Official validation scored exactly once per frozen seed and candidate, and
  never used for selection, tuning, early stopping, thresholding, or ranking.
- Train-only preprocessing: every learned statistic, including class weights,
  is fit on refit fit-subset rows only.
- Same-row trivial baseline comparison wherever candidate metrics are reported.
- `holdout_test_contact=false` in manifests, handoffs, and the decision record.
- `official_validation_for_selection=false` and `no_final_model_selected=true`
  in Stage 03 outputs.
- Durable Drive result-save cell immediately after a successful
  `run_stage(config)`.
- Checkpoints for the long-running refit loop under
  `My Drive/lst_models/checkpoints/03_frozen_validation_readout/<run_id>/`.
- Runtime paths computed by the notebook injected into the stage config before
  `run_stage(config)` and before config contract assertions.
- GPU/CUDA device provenance recorded in the manifest and refit records.
- Exact-commit Colab bootstrap pinned to a full-bundle commit that contains the
  Stage 03 sidecars, not only the notebook.
- Notebook static-gate compatibility.

## 2. Stage Role

Stage 03 is the frozen official-validation readout. It is the first and only
stage in the V2 route that is authorized to read, window, score, or summarize
official-validation rows. Stage 04 and later stages may only read the frozen
Stage 03 artifacts; they may not re-score official validation.

Stage 03 inputs are exactly one primary candidate and exactly one fallback
candidate from the superseding Stage 02 run. The Stage 02 freeze gate requires
both roles before it sets `ready_for_stage03=true`; a handoff with zero or one
frozen candidate blocks Stage 03.

Stage 03 does:

- Verify the full Stage 00 -> 01 -> 02 frozen artifact chain (section 4).
- Refit the frozen primary candidate per frozen seed on all eligible
  official-train rows under the mechanism-frozen recipe (section 5).
- Window and score all eligible official-validation rows exactly once per
  frozen seed and candidate (sections 5, 6, 11).
- Score the four Stage 00 registry baselines on the identical validation rows
  (section 6).
- Judge the readout against predeclared criteria (section 7) and write the
  frozen readout artifacts and decision record (section 10).

Stage 03 does NOT do:

- HPO or any hyperparameter retuning.
- Model, feature, or window selection.
- Threshold tuning.
- Loss selection.
- Calibrator fitting.
- Holdout/test contact of any kind.

Scope semantics: the project-level config keeps `scope: validation_only`,
which retains its project meaning "no test or holdout contact". Within that
scope, Stage 03 additionally records `official_validation_contact=true` and
`official_validation_for_selection=false`: official validation is contacted
for the readout, and the contact is never a selection event.

Legacy provenance: "Stage 00/01 runs predate hash-provenance fields;
consistency was established by code-diff audit and Stage 02 row-count parity."
This sentence must be carried into Stage 03 and Stage 05 reporting wherever
upstream integrity is summarized.

## 3. Wording Rules

Forbidden wording in Stage 03 outputs, notebook text, handoff notes, and any
downstream text based on Stage 03 evidence:

```text
final model
official validation winner
holdout winner
test winner
proved best model
generalization proven
profitable
holdout-ready
selected by official validation
chosen threshold
```

Allowed wording:

```text
validation-only evidence
official validation readout
candidate met/did not meet predeclared validation-readout criteria
```

`no_final_model_selected=true` is retained in Stage 03 outputs. The readout
characterizes one frozen candidate against predeclared criteria; it does not
crown a model, and it does not upgrade validation evidence into holdout/test
or deployment claims.

## 4. Entry Gates

Stage 03 must fail closed before any refit or scoring when any gate below
fails. Gate failures raise exact-path/exact-field errors. A gate failure that
blocks the run as a whole produces a `do_not_start_stage03_*` decision record
with `official_validation_scoring_events=0`. A failure specific to
reconstructing or refitting the primary candidate is handled by the fallback
policy in section 8.

Required entry-gate chain:

1. Exact Stage 02 run folder resolved by exact run id
   (`inputs.stage02_run_id`); never inferred from a parent-folder scan.
2. `02_stage03_handoff.json` records `ready_for_stage03=true`.
3. Exactly one primary AND exactly one fallback candidate are frozen in the
   Stage 02 handoff and frozen-candidate artifacts (the Stage 02 source
   requires both: `model_hpo_train_inner.py:1628-1635`).
4. The full Stage 02 artifact list is present, with `artifact_inventory.csv`
   `bytes` and `sha256` verified via `artifacts.require_artifacts`, not
   existence-only:

```text
02_model_hpo_train_inner_summary.csv
02_hpo_plan_ledger.csv
02_hpo_trial_ledger.csv
02_hpo_summary.csv
02_baseline_control_summary.csv
02_frozen_candidate.json
02_frozen_candidate.md
02_best_params_by_family.json
02_stage03_handoff.json
frozen_params/*.yaml
run_manifest.json
artifact_inventory.csv
```

5. The `02_hpo_plan_ledger.csv` sha256 MUST differ from the
   `02_hpo_trial_ledger.csv` sha256. A byte-identical plan ledger is the
   defect signature of the pre-`6182508` packaging path and blocks Stage 03.
6. Exact Stage 00 run folder with required artifacts:

```text
raw_data_manifest.json
split_freeze.json
label_policy.json
baseline_registry.json
sample_event_index.csv
run_manifest.json
artifact_inventory.csv
```

7. Exact Stage 01 run folder with required artifacts:

```text
run_manifest.json
artifact_inventory.csv
01_candidate_inputs.json
01_feature_window_search_summary.csv
```

8. Raw files are downloaded by Google Drive file ID; per-file `sha256` and
   `bytes` are verified when present in the frozen Stage 00 raw manifest.
   Verification is legacy-tolerant: when the frozen manifest predates the hash
   fields, the missing verification is recorded with an explicit reason and is
   never fabricated as a match.
9. Run-id chain consistency: the config `stage00_run_id`, `stage01_run_id`,
   and `stage02_run_id` values must equal the `source_stage00_run_id` and
   `source_stage01_run_id` fields recorded inside the Stage 02 handoff and
   frozen candidate.
10. `stage01.feature_rebuild_code_sha256()` computed at the Stage 03 execution
    commit must equal the Stage 02 manifest's
    `stage02_feature_rebuild_code_sha256`. A mismatch means the rebuild code
    drifted after Stage 02 froze its candidates and blocks Stage 03.
11. Rebuilt train-row totals and per-ticker counts for the scored candidate
    must equal `01_feature_window_search_summary.csv` — the same parity check
    Stage 02 ran against Stage 01. A mismatch means Stage 03 would refit on a
    different finite-row contract than the one that produced the frozen
    candidate.
12. `holdout_test_contact=false` and `official_validation_for_selection=false`
    on every upstream manifest and handoff (Stage 00, Stage 01, Stage 02).

Superseded-run rejection: the completed Stage 02 run `20260609_100637_704705`
predates the `6182508` packaging fix and MUST be rejected as a Stage 03 input.
The config freezes the upstream pins and the rejection list:

```text
stage00_run_id: "20260609_015034_927813"
stage01_run_id: "20260609_070204"
stage02_run_id: "<NEW_STAGE02_RUN_ID>"   # roadmap Phase 0.3 output; filling
                                         # this value is the ONLY permitted
                                         # config edit afterward
superseded_stage02_run_ids: ["20260609_100637_704705"]
```

The runner must raise when `stage02_run_id` is the unfilled placeholder or
appears in `superseded_stage02_run_ids`. The config contract test enforces the
same rule statically.

Legacy provenance (roadmap Phase 0.4, quoted): "Stage 00/01 runs predate
hash-provenance fields; consistency was established by code-diff audit and
Stage 02 row-count parity." Gates 8 and 10 are therefore legacy-tolerant for
the frozen Stage 00/01 runs only, with the tolerance reason recorded in the
Stage 03 manifest; they are strict for all newer upstream runs.

## 5. Refit Recipe (D1 + D2, Frozen)

Decision D1 (frozen 2026-06-09): the refit mechanism is frozen, not the
iteration count. `02_frozen_candidate.json` carries profile parameters but no
per-trial `best_iteration`/best-epoch; Stage 03 therefore re-derives the
stopping point with the identical Stage 02 mechanism on the refit rows and
records the per-refit outcome.

Decision D2 (frozen 2026-06-09): full-row policy. Refit uses ALL eligible
official-train rows (no 50k cap); scoring uses ALL eligible
official-validation rows (no 20k cap, natural label distribution).

Frozen refit procedure, executed once per seed in the frozen seed list
`[101, 202]`:

- LightGBM families: parameters are built from the frozen profile; the
  effective `n_estimators` is resolved by early stopping on a chronological
  tail carved from the refit rows only, with the same
  `_lightgbm_inner_train_early_stopping_split` semantics Stage 02 used:
  `early_stopping_validation_source=inner_train_chronological_tail`,
  `early_stopping_validation_fraction=0.2`, minimum 128 fit-subset rows and
  minimum 128 tail rows, `early_stopping_rounds=25`. The scored
  official-validation rows are never passed as the early-stopping `eval_set`.
- Torch families: early stopping uses `inner_train_chronological_tail` with
  fraction 0.2, minimum 128 fit-subset rows and minimum 128 tail rows,
  `early_stopping_patience=8`, maximum 64 epochs, and best-epoch restoration.
  The scored official-validation rows are never used for epoch selection.
- Class weights are recomputed on the refit fit-subset rows (the refit rows
  minus the early-stopping tail), never on validation rows.
- Tail-split fallback reasons (tail too small, single-class tail) are recorded
  per refit, together with per-refit `best_iteration`/`best_epoch` and the
  early-stopping train/tail sample-id hashes, in the readout artifacts and
  `refit_records`.

Frozen config blocks (`configs/stages/03_frozen_validation_readout.yaml`):

```yaml
readout:
  seeds: [101, 202]
  refit_rows: all_eligible_official_train_rows
  scoring_rows: all_eligible_official_validation_rows
  refit_recipe: frozen_mechanism_chronological_tail_early_stopping
  score_each_seed_candidate_exactly_once: true
  max_materialized_train_bytes: 2000000000
```

```yaml
lightgbm_training_defaults:
  eval_metric: binary_logloss
  early_stopping_rounds: 25
  early_stopping_validation_source: inner_train_chronological_tail
  early_stopping_validation_fraction: 0.2
  minimum_early_stopping_train_samples: 128
  minimum_early_stopping_validation_samples: 128
```

```yaml
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
```

The two training-defaults blocks are byte-equal copies of the frozen Stage 02
values (`configs/stages/02_model_hpo_train_inner.yaml`); the config contract
test asserts the equality so the refit mechanism cannot drift from the tuning
mechanism.

Non-comparability declaration: Stage 02 absolute metrics and Stage 03 absolute
metrics are NOT comparable. Stage 02 trials were fit and scored on stylized
equal-allocation per-`(ticker, label)` subsamples (50k train / 20k eval per
fold); Stage 03 refits and scores on the natural row distribution. Comparing
the absolute levels across that sampling change is a sample-selection-bias
error (Zadrozny 2004). Only Stage 03 same-row deltas against the section 6
baselines support claims.

Feasibility clause (frozen before execution): the notebook pre-flight cell
estimates materialized train/validation tensor bytes from
`sample_event_index.csv` row counts BEFORE any scoring event and compares the
estimate against `readout.max_materialized_train_bytes`. If the estimate is
infeasible for the Colab runtime, Stage 03 aborts with zero scoring events;
the config is then amended to the predeclared fallback sample policy — the
same `deterministic_even_stride_by_ticker_label` method Stage 02 used, with a
raised cap declared in config — and a fresh run starts. The sample policy is
never tuned after a scoring event has occurred.

## 6. Validation Windowing And Same-Row Baselines

Stage 03 windows official-validation rows for the first time in the route.
Validation windowing obeys the frozen Stage 00 section 9 rules, identically to
how train rows were windowed in Stages 01/02:

- Windows are built per ticker, per split, per trading day.
- No window may cross tickers, split boundaries, or trading-day boundaries.
- No lookback across `2013-09-16`: official validation starts at that boundary
  and validation windows may not include train-interval bars.
- Day-start warmup rows are ineligible: a window must fit entirely inside the
  target row's trading day, so the first `window_size - 1` bars of each
  trading day cannot be window targets.
- The target row of a window must have a valid binary label.
- All feature rows inside the window must be finite after train-only
  preprocessing.

The eligible-row contract is computed by the same frozen builder used for
train rows (`stage01._build_window_dataset`); Stage 03 introduces no new
windowing code path. The resulting validation row set is recorded as
`n_scored_validation_samples` plus `eval_sample_id_hash` in the readout
artifacts, so the exact scored rows are auditable and reproducible.

Same-row baselines: the four Stage 00 section 11 registry baselines are scored
on the identical validation rows (same sample ids, enforced by per-key
`eval_sample_id_hash` equality):

```yaml
baseline_controls:
  mandatory:
    - stratified_dummy_train_prior
    - majority_train_prior
    - constant_up
    - constant_down
```

Baseline fitting rules: the train-prior baselines are fit on the refit rows'
labels only; `stratified_dummy_train_prior` is seeded with the trial seed;
`constant_up` and `constant_down` learn nothing. Every candidate readout row
reports BOTH deltas — `delta_macro_f1_vs_stratified_dummy_train_prior` AND
`delta_macro_f1_vs_majority_train_prior` — on the same rows.

## 7. Predeclared Readout Criteria (Frozen)

The readout is judged on the seed-aggregate (mean over seeds), with per-seed
values reported alongside. All three conditions must hold:

1. `mean(delta_macro_f1_vs_stratified_dummy_train_prior) > 0` over the frozen
   seeds.
2. `mean(delta_macro_f1_vs_majority_train_prior) > 0` over the frozen seeds.
3. `positive_ticker_count >= 3`, where each ticker's delta versus the
   stratified dummy is first averaged across seeds and the positives are then
   counted (floor of 3 of the 5 tickers).

Frozen config block:

```yaml
predeclared_criteria:
  aggregate: mean_over_seeds
  require_delta_macro_f1_vs_stratified_dummy_train_prior_positive: true
  require_delta_macro_f1_vs_majority_train_prior_positive: true
  minimum_positive_ticker_count: 3
  per_ticker_aggregation: mean_delta_across_seeds_then_count_positive
```

The decision field takes exactly one of two values:

```text
met_predeclared_validation_readout_criteria
did_not_meet_predeclared_validation_readout_criteria
```

Outcome semantics:

- Met: Stages 04/05 proceed with validation-only claims. The wording rules of
  section 3 still apply; meeting the criteria does not produce a `final model`
  claim.
- Not met: the decision record stores
  `did_not_meet_predeclared_validation_readout_criteria`. There is NO fallback
  activation and NO retuning. The only forward path is honest reporting plus
  an optional pre-registered V2.1 revision upstream.

Stages 04 and 05 run either way: diagnostics and honest synthesis are not
conditional on a positive readout.

## 8. Fallback Policy (Frozen)

The fallback candidate exists for mechanical failure of the primary, not for
weak results. Frozen config block:

```yaml
fallback_policy:
  allowed_triggers:
    - missing_frozen_artifact
    - schema_or_hash_mismatch
    - refit_crash_before_any_scoring
    - candidate_not_reconstructable
  forbidden_triggers:
    - weak_validation_metrics
    - below_dummy
    - per_ticker_instability
  after_first_scoring_event: never_activate
```

Rules:

- The fallback may activate ONLY before the first scoring event of the
  primary, and only on the four allowed mechanical triggers.
- Weak metrics, below-dummy deltas, and per-ticker instability never activate
  the fallback. They are readout outcomes, not failures.
- After the first scoring event, nothing activates the fallback. A crash in a
  later seed is recorded as an incomplete readout
  (`readout_complete=false`), never as a fallback switch.
- When the fallback activates, the identical frozen procedure of sections 5-7
  runs for the fallback candidate, and the activation reason is recorded.
- Every fallback activation and every scoring event is recorded in
  `03_decision_record.json`.

## 9. Metrics

Required candidate metrics on the scored validation rows:

- `macro_f1` (primary readout metric).
- `balanced_accuracy`.
- `accuracy` (auxiliary only; the natural distribution makes raw accuracy
  prior-sensitive).
- `mcc`.
- `roc_auc`, when defined for the scored labels.
- Per-class precision, recall, F1, and support, by class and by ticker.
- Both same-row baseline deltas, keeping the Stage 02 column naming:
  `delta_macro_f1_vs_stratified_dummy_train_prior` and
  `delta_macro_f1_vs_majority_train_prior`.
- Per-ticker metrics (`03_per_ticker_readout.csv`).
- Seed summary across the frozen seeds (`03_seed_summary.csv`).

Uncertainty reporting: confidence intervals or lower confidence bounds are
allowed ONLY as the predeclared trading-day block bootstrap
(`metrics.block_bootstrap_macro_f1_delta`, resampling blocks =
`ticker|trading_day`). Block-bootstrap output is uncertainty context for the
readout; it is never a selection device, never a gate substitute, and never a
standalone significance claim.

## 10. Required Artifacts

Stage 03 writes seven required outputs to the run folder:

```text
03_validation_readout.csv      pooled per candidate x seed + aggregate rows
03_per_ticker_readout.csv      per-ticker rows per candidate x seed
03_seed_summary.csv            seed-aggregate rows + criteria booleans
03_same_row_baselines.csv      four registry baselines per seed, same rows
03_validation_predictions.csv  REQUIRED per-row prediction dump
03_decision_record.json        criteria, outcomes, scoring-event ledger
run_manifest.json + artifact_inventory.csv + drive_backup_manifest.json
```

`03_validation_readout.csv` contains one row per scored candidate x seed plus
an `aggregate_mean` row in the `seed` column.

`03_validation_predictions.csv` is the load-bearing interface to Stage 04.
Without it, Stage 04 calibration, selective/no-trade, robustness, and failure
analysis would require re-scoring official validation, which is forbidden.
Prediction dumps stay out of git (route guide section 11); they live in the
run folder and the Drive backup, with `sha256` recorded in
`artifact_inventory.csv`.

Frozen column contracts (verbatim copies of the runner constants; doc and code
freeze together):

```text
VALIDATION_READOUT_COLUMNS = [
    "candidate_role", "candidate_id", "feature_set", "window_size",
    "model_family", "hpo_profile_id", "seed", "n_refit_train_samples",
    "n_scored_validation_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "macro_f1", "balanced_accuracy", "accuracy",
    "mcc", "roc_auc",
    "precision_down", "recall_down", "f1_down", "support_down",
    "precision_up", "recall_up", "f1_up", "support_up",
    "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior",
    "delta_balanced_accuracy_vs_stratified_dummy_train_prior",
    "positive_ticker_count", "best_iteration", "early_stopping_source",
    "early_stopping_used", "early_stopping_reason",
    "early_stopping_train_sample_id_hash", "early_stopping_eval_sample_id_hash",
    "requested_device", "resolved_device", "device_fallback_reason",
    "fit_status", "error_message", "scope",
]
```

```text
PER_TICKER_READOUT_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "ticker", "n_rows",
    "support_up", "support_down", "macro_f1", "balanced_accuracy",
    "accuracy", "f1_up", "f1_down",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "scope",
]
```

```text
SEED_SUMMARY_COLUMNS = [
    "candidate_role", "candidate_id", "n_seeds",
    "mean_macro_f1", "std_macro_f1",
    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "min_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_delta_macro_f1_vs_majority_train_prior",
    "min_delta_macro_f1_vs_majority_train_prior",
    "positive_ticker_count_mean_across_seeds",
    "criteria_delta_vs_stratified_dummy_met",
    "criteria_delta_vs_majority_met", "criteria_ticker_floor_met",
    "met_predeclared_criteria", "scope",
]
```

```text
SAME_ROW_BASELINE_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "baseline_id", "fit_status",
    "n_train_samples", "n_eval_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "sample_id_hash", "macro_f1",
    "balanced_accuracy", "accuracy", "roc_auc", "mcc", "error_message",
    "scope",
]
```

```text
VALIDATION_PREDICTION_COLUMNS = [
    "candidate_role", "candidate_id", "model_family", "hpo_profile_id",
    "seed", "sample_id", "ticker", "target_timestamp", "trading_day",
    "y_true", "p_up", "y_pred", "scope",
]
```

Every output row carries `scope="validation_only"`.

`03_decision_record.json` required fields:

```text
route
stage_name
source_stage00_run_id
source_stage01_run_id
source_stage02_run_id
superseded_stage02_run_ids
primary identity block (from 02_frozen_candidate.json)
fallback identity block (from 02_frozen_candidate.json)
predeclared_criteria echo (the frozen config block)
per-seed outcome rows
aggregate values
per-criterion booleans
decision
fallback_activated + fallback_reason
readout_complete
official_validation_scoring_events
scoring_event_ledger (list; one entry per scoring event:
  candidate_role, candidate_id, seed, n_rows, timestamp_utc)
refit_records (role, seed, best_iteration, early-stopping fields)
holdout_test_contact = false
official_validation_for_selection = false
no_final_model_selected = true
```

`run_manifest.json` mirrors the Stage 02 manifest shape (Stage 02 protocol
section 16: route, stage name, scope, config/notebook sha256, exact upstream
run ids, input/output artifacts, `holdout_test_contact=false`) and
additionally records:

```text
official_validation_contact = true
official_validation_scoring_events = <n>
stage03_readout_code_sha256 (sha256 over the Stage 03 data-context source
  composed with stage01.feature_rebuild_code_sha256(); composition documented
  in the manifest)
source_stage02_feature_rebuild_code_sha256 + match flag (reason recorded when
  legacy-tolerant)
requested_device, resolved_device, cuda_available, gpu_name_or_null,
  device_fallback_reason
repo_url, git_commit (git_commit=null with explicit reason when the workspace
  is not a git repository)
```

## 11. Execution Discipline

- One scoring event per seed x candidate: each frozen seed-candidate pair
  contacts official-validation rows exactly once. With the frozen seeds
  `[101, 202]` and no fallback activation, the expected count is 2; the
  expected count is always `len(seeds) x candidates_actually_scored`.
- No early stopping, threshold selection, loss selection, calibration, or
  ranking ever uses official-validation rows.
- Every scoring event is appended to the `scoring_event_ledger` in
  `03_decision_record.json`, and `official_validation_scoring_events` must
  equal the ledger length. Same-row trivial baseline scoring on the identical
  rows is required context (section 6) and is recorded with the readout; it is
  not a candidate scoring event.
- Per-seed checkpoints: after each seed refit, write a checkpoint to
  `My Drive/lst_models/checkpoints/03_frozen_validation_readout/<run_id>/`
  with a `checkpoint_manifest.json` recording `stage_name`, `run_id`,
  `status=incomplete`, completed units, pending units, timestamp, and resume
  instructions. Checkpoints are recovery state, not evidence artifacts. Write
  locally first, then mirror compact files/archives to Drive.
- Durable result save: immediately after `run_stage(config)` returns, the
  notebook validates the seven required outputs and uploads them to
  `My Drive/lst_models/results/03_frozen_validation_readout/<run_id>/` via the
  Drive API, refusing upload unless the manifest records
  `official_validation_for_selection=false` and `holdout_test_contact=false`,
  and writing/uploading `drive_backup_manifest.json`. Duplicate Drive folders
  or files under the exact target parent are a hard error.
- Resume requires the exact `run_id` and checkpoint folder. Resuming from the
  latest checkpoint found by a parent-directory scan is forbidden. A resumed
  run must not repeat a scoring event already present in the ledger.

## 12. Minimum Tests

- `tests/contracts/test_stage03_config_contract.py` — guards the frozen
  config: scope/contact flags, exact upstream run-id chain, rejection of the
  `<NEW_STAGE02_RUN_ID>` placeholder and the superseded Stage 02 run id,
  byte-equality of the two training-defaults blocks with Stage 02, and the
  frozen criteria/fallback/baseline/wording lists.
- `tests/stages/test_stage03_run_stage_smoke.py` — guards runner behavior on a
  tiny chronology-safe fixture: fail-closed entry gates, refit early-stopping
  tail drawn from refit rows only, exactly one scoring event per seed, weak
  metrics never activating the fallback, and the output/decision-record/
  manifest schemas.
- `tests/notebooks/test_stage03_notebook_static.py` — guards the notebook
  surface: parse/AST/empty outputs, `RUN_STAGE03 = False` default, exact
  pinned commit and upstream run ids, runtime-path injection lines, the
  durable-save cell with manifest-flag refusals, and forbidden
  holdout/test/selection-on-validation patterns.
- `tests/contracts/test_metrics.py` (`per_class_metrics`) — guards the
  per-class precision/recall/F1/support contract over fixed labels {0, 1},
  including zero-division behavior when a class is absent.

## 13. Scientific Risks And Protections

| Risk | Protection |
|---|---|
| Validation budget creep | Scoring-event ledger in `03_decision_record.json`; one scoring event per seed x candidate; Stage 04 default is zero new validation fit-predict events; Stage 05 aggregates the route-wide budget. |
| Decision standards chosen after seeing the readout | Sections 5-10 and D1-D4 are frozen in committed protocol/config text before nb03 executes; the config contract test pins the frozen values. |
| Refit regime differs from tuning regime | D1 freezes the Stage 02 early-stopping mechanism; D2 full-row policy is predeclared; Stage 02 vs Stage 03 absolute metrics are declared non-comparable (section 5). |
| Fallback abuse (weak primary rescued by fallback) | Mechanical-only triggers, allowed only before the first scoring event; weak metrics are explicit forbidden triggers; after the first scoring event nothing activates the fallback. |
| Wording drift | Section 3 forbidden/allowed lists; `forbidden.wording` in config; notebook static-gate forbidden-pattern checks. |
| Colab loss mid-refit | Per-seed checkpoints under `My Drive/lst_models/checkpoints/03_frozen_validation_readout/<run_id>/` with `status=incomplete`, pending units, and exact-run-id resume; durable Drive result save immediately after `run_stage`. |
| Stale run ids after the Stage 02 re-run | Config contract test rejects the `<NEW_STAGE02_RUN_ID>` placeholder and the superseded id `20260609_100637_704705`; hardcoded ids in tests/static gates are updated in the same task as the config repoint. |

## 14. Evidence Basis

Internal evidence basis:

- `docs/protocols/00_data_split_label_freeze_protocol.md`: frozen splits
  (section 5), window validity rules (section 9), train-only preprocessing
  (section 10), baseline registry (section 11).
- `docs/protocols/01_feature_window_search_protocol.md`: frozen candidate
  inputs and screening boundary.
- `docs/protocols/02_model_hpo_train_inner_protocol.md`: train-inner HPO
  contract, frozen primary/fallback handoff (section 15), manifest and device
  provenance shape (section 16).
- `docs/lst_models_v2_route_roadmap.md`: decisions D1-D4, frozen by user
  sign-off 2026-06-09 (Phase 2); Stage 02 supersede requirement (Phase 0).

External method anchors:

- Cawley and Talbot (2010): model-selection overfitting and selection-bias
  caution; the reason official validation is scored once under predeclared
  criteria instead of being reused for selection.
  https://jmlr.org/papers/v11/cawley10a.html
- Dwork et al. (2015): "The reusable holdout: preserving validity in adaptive
  data analysis", Science 349(6248); the adaptive-analysis hazard behind the
  one-shot readout, the scoring-event ledger, and the frozen criteria.
  https://arxiv.org/abs/1506.02629
- Zadrozny (2004): "Learning and evaluating classifiers under sample selection
  bias", ICML; the basis for declaring equal-allocation subsample metrics
  non-comparable to natural-distribution metrics.
  https://dl.acm.org/doi/10.1145/1015330.1015425
- scikit-learn `DummyClassifier`: official reference for `stratified`,
  `most_frequent`, and `constant` simple baselines.
  https://scikit-learn.org/dev/modules/generated/sklearn.dummy.DummyClassifier.html

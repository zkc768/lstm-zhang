# Stage 02 Protocol: Train-Inner Model HPO

Status: active formal Stage 02 train-inner HPO contract.

This document defines the Stage 02 research contract and the current executable
sidecar behavior. Stage 02 now runs bounded, predeclared HPO profiles on
train-inner folds only. It still does not read official validation, test, or
holdout rows, and it still does not select a final model.

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
  target_path: docs/protocols/02_model_hpo_train_inner_protocol.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; this is a stage protocol update
  why_not_utils: not applicable; this is a stage protocol update
  safety_tests: static protocol/config/code consistency review
```

Implementation must preserve:

- Colab-first execution.
- One user-facing Stage 02 notebook.
- One Stage 02 config sidecar.
- One Stage 02 protocol sidecar.
- One `run_stage(config)` entry point when executable logic is used.
- No official validation, test, or holdout read during Stage 02 HPO.
- Train-only preprocessing inside each train-inner fold.
- Same-row dummy baseline comparison where model metrics are reported.
- `holdout_test_contact=false` in manifests and handoff artifacts.

## 2. Stage Role

Stage 02 is the formal HPO stage for Stage 01-approved model families, but its
optimization scope is train-inner only.

Stage 02 may compare:

- Candidate model families.
- Same-row baselines.
- Predeclared controls and ablations.
- Predeclared HPO profiles or search trials.

Stage 02 may not read, summarize, rank, tune against, or indirectly optimize for:

- Official validation rows.
- Test rows.
- Holdout rows.
- Any metric computed outside Stage 00's frozen training partition.

The project-level config may still use `scope: validation_only` to mean "no
test or holdout contact." Within that broader safety scope, Stage 02's specific
research scope is stricter: HPO and model-family comparison must use only
train-inner folds.

## 3. Current Executable Status

The current Stage 02 executable contract is a formal train-inner HPO runner for
the Stage 01-approved families enabled in the Stage 02 config.

Current active outputs are:

- `02_model_hpo_train_inner_summary.csv`
- `02_hpo_plan_ledger.csv`, a planned-trial ledger with candidate, family,
  profile, fold, seed, sample-count, sample-hash, and baseline identifiers only
- `02_hpo_trial_ledger.csv`
- `02_hpo_summary.csv`
- `02_baseline_control_summary.csv`
- `02_frozen_candidate.json`
- `02_frozen_candidate.md`
- `02_best_params_by_family.json`
- `02_stage03_handoff.json`
- frozen params YAML files under the run folder's `frozen_params/` directory,
  when a primary/fallback freeze succeeds
- `run_manifest.json`
- `artifact_inventory.csv`

Current runner behavior:

- Rebuilds Stage 02 train-inner data from frozen Stage 00 artifacts and raw data.
- Consumes the exact Stage 01 candidate handoff run configured in the Stage 02
  config.
- Executes every approved enabled family/profile/fold/seed HPO row, subject to
  the declared budget.
- Scores required same-row baselines on the exact same fold rows.
- Writes formal HPO trial, summary, baseline/control, frozen-candidate, and
  Stage 03 handoff artifacts.
- Writes `02_hpo_plan_ledger.csv` as a distinct plan artifact. It must not be a
  byte-identical copy of `02_hpo_trial_ledger.csv` and must not contain fitted
  model metrics, `fit_status`, or Stage 03 selection flags.
- Sets Stage 03 readiness to true only when a primary and fallback candidate are
  frozen from completed train-inner HPO rows and all configured gates pass.
- Keeps `holdout_test_contact=false`.

Stage 03 is authorized to read official validation only when
`02_stage03_handoff.json` records `ready_for_stage03=true`. A completed HPO run
that fails the freeze gates must still block Stage 03.

## 4. Upstream Inputs

Stage 02 may start only after Stage 00 and Stage 01 artifacts are complete and
internally consistent.

Required Stage 00 inputs:

- Frozen chronological split assignment.
- Frozen label policy, including horizon and no-trade band.
- Frozen sample-validity policy.
- Frozen ticker universe.
- Train-only preprocessing contract.
- Stage 00 run manifest and portable artifact inventory.

Required Stage 01 inputs:

- `01_candidate_inputs.json`.
- `01_feature_window_search_summary.csv`.
- `01_train_inner_probe_ledger.csv`.
- `01_train_inner_fold_manifest.csv`.
- `01_train_label_band_diagnostic.csv`, when produced by Stage 01.
- Stage 01 run manifest and portable artifact inventory.

`01_candidate_inputs.json` is the handoff source for:

- `candidate_inputs`.
- `approved_model_families_for_stage02`.
- `stage02_modeling_scope_axis`.
- `family_lcb_selection_policy`.
- `holdout_test_contact=false`.
- `no_final_model_selected=true`.

Stage 02 must treat Stage 00 and Stage 01 decisions as frozen inputs. It may not
reopen the label policy, broad feature universe, window search, ticker set, or
sample-validity rules inside Stage 02.

Current selected Stage 01 handoff for this Stage 02 config:

- Stage 01 run id: `20260609_070204`.
- Stage 01 runtime run folder:
  `/content/lst_models_results/01_feature_window_search/20260609_070204`.
- Stage 01 Drive backup folder:
  `My Drive/lst_models/results/01_feature_window_search/20260609_070204`
  (`1RofmvfGI1_peaPmB7yvphHJllx949fKJ`).
- Source Stage 00 run id: `20260609_015034_927813`.
- Stage 01 decision: `selected_candidate_inputs_for_stage02_train_inner_hpo`.
- Safety flags: `holdout_test_contact=false`,
  `official_validation_for_selection=false`,
  `no_final_model_selected=true`.

Current Stage 02 candidate inputs from the Stage 01 handoff:

| candidate_id | feature_set | window_size | Stage 01 screening family | median_family_lcb_delta |
|---|---|---:|---|---:|
| `price_action_core_w20` | `price_action_core` | 20 | `tcn` | 0.003667 |
| `price_volume_time_w20` | `price_volume_time` | 20 | `lightgbm` | 0.006686 |

These Stage 01 screening values are handoff provenance only. They do not rank
Stage 02 HPO trials, do not authorize official validation readout, and do not
select a final model.

## 5. Start Gate

The Stage 02 notebook and runner must fail closed if any required input is
missing, stale, or unsafe.

Required checks:

- `inputs.stage01_run_id` is explicit.
- The configured Stage 01 run folder resolves by exact run id.
- Upstream artifacts resolve by `run_folder / relative_path` or explicit exact
  artifact paths, not by stale runtime-only `/content/...` inventory values.
- When an upstream `artifact_inventory.csv` includes `bytes` and `sha256`,
  required artifact reads must verify those values instead of checking existence
  only.
- Stage 01 manifest records `holdout_test_contact=false`.
- Stage 01 handoff records `holdout_test_contact=false`.
- Stage 01 handoff records `no_final_model_selected=true`.
- Stage 01 handoff contains at least one candidate input before HPO planning or
  fitting proceeds.
- Every Stage 01-approved family is enabled in the Stage 02 config.
- If the Stage 01 manifest records `feature_rebuild_code_sha256`, it must match
  the current Stage 02 feature-rebuild code hash before Stage 02 rebuilds
  feature/window data.
- If the frozen Stage 00 raw manifest records per-file `sha256` or `bytes`,
  Stage 02 must verify the local raw files before resampling.
- Stage 02 must compare each rebuilt candidate's total and per-ticker eligible
  sample counts against `01_feature_window_search_summary.csv`; a mismatch blocks
  HPO because Stage 02 would no longer be training on the same finite-row
  contract that Stage 01 screened.
- No official validation, test, or holdout artifact is configured as an HPO input.
- HPO search space, folds, seeds, budget, objective, and tie-break rules are
  declared before any fitting trial starts.

The configured Stage 01 run id is a handoff value, not a permanent invariant.
After a newer Stage 01 run completes and is selected for Stage 02, update the
Stage 02 config and any contract tests that accidentally hard-code an old run id.
Tests should validate exact-run shape and consistency, not preserve stale
transient run ids.

If Stage 01 is still running, Stage 02 documentation may be edited, but
executable Stage 02 config must wait for the completed Stage 01 run id.

## 6. Candidate Families And Roles

Stage 02 must not silently demote or promote model families after Stage 01 has
frozen its handoff.

Active rule:

- Stage 01 decides `approved_model_families_for_stage02`.
- Stage 02 verifies that every approved family is enabled in
  `hpo_families`.
- Stage 02 applies the predeclared budget and start gates.
- If the approved set is too large for the declared budget, Stage 02 blocks and
  requests an upstream or config correction. It must not secretly drop a family.

Recommended thesis-scale target:

- Upstream Stage 01 should normally keep the formal HPO candidate set to two or
  three main families before it freezes `approved_model_families_for_stage02`.
- If Stage 01 approves four families, Stage 02 may only run all four when the
  budget arithmetic closes and the protocol records that all four are formal HPO
  candidates.
- Stage 02 does not invent input-side primary/fallback family tiers. Primary and
  fallback candidates are Stage 02 outputs after formal HPO, not family labels
  assigned before fitting.

Controls and ablations must be labeled separately from formal HPO candidates.
They may be fixed-param controls or small-budget controls, but they must not be
reported as thesis candidate families unless Stage 01 approved them and Stage 02
budgeted them before execution.

## 7. Baselines And Controls

Required same-row baselines:

- `stratified_dummy_train_prior` or the Stage 01/Stage 02 configured equivalent.
- `majority_train_prior`.
- `constant_up`.
- `constant_down`.

Tracked architectural controls for future implementation:

- `last_step_mlp`.
- `last_step_lightgbm_control`.
- `dlinear_only`.
- `tcn_only`.

Baseline and control rules:

- Baselines and candidates must be scored on identical eligible rows per fold.
- Candidate deltas must state which baseline was used.
- `stratified_dummy` style baselines must use controlled random seeds.
- Controls may not read official validation, test, or holdout rows.
- Controls may not become additional thesis candidates after results are seen.

The current config uses `stratified_dummy_train_prior` as the primary selection
baseline and reports all four mandatory baseline controls in
`02_baseline_control_summary.csv`. Output schemas must retain the Stage 00
baseline registry names above or update config, code, tests, and docs together.
The current active runner does not produce `last_step_mlp`,
`last_step_lightgbm_control`, `dlinear_only`, or `tcn_only` artifacts. Those
controls are non-blocking future controls unless config, budget arithmetic,
runner code, tests, and this protocol are updated before execution.

## 8. Budget Arithmetic

Budget must be countable before any Stage 02 fitting starts.

For the current formal HPO runner, planned rows are:

```text
planned_rows =
  candidate_input_count
  * sum(profile_count for each approved enabled family)
  * train_inner.n_folds
  * len(train_inner.seeds)
```

When every approved family has the same number of profiles, this simplifies to:

```text
planned_rows =
  candidate_input_count
  * approved_enabled_family_count
  * profile_count_per_family
  * train_inner.n_folds
  * len(train_inner.seeds)
```

Add any extra search axis to this formula before execution, including:

- `modeling_scope` variants.
- Loss choices.
- Threshold policies.
- Class/sample-weighting choices, when represented as independent trials.
- Any per-ticker versus pooled evaluation branch.

The active config currently declares:

- `budget.max_hpo_plan_rows = 240`.
- `budget.max_profiles_per_family = 8`.
- `train_inner.n_folds = 3`.
- `train_inner.seeds = [101, 202]`.

The current search-space files contain four profiles per enabled core family.
Verify this against the search-space files before execution. With two Stage 01
candidate inputs, four approved families, four profiles, three folds, and two
seeds, the current plan is:

```text
2 * 4 * 4 * 3 * 2 = 192 rows <= 240
```

If Stage 02 also evaluates two independent `modeling_scope` variants as a cross
product, the same setup becomes:

```text
2 * 4 * 4 * 3 * 2 * 2 = 384 rows > 240
```

That is not allowed under the current cap. To stay compliant, Stage 02 must do
one of the following before execution:

- Reduce candidate inputs.
- Reduce approved families.
- Reduce profiles.
- Treat `modeling_scope` as metadata inherited from a candidate input rather
  than a crossed HPO branch.
- Increase the cap with a protocol, config, and test update.

Trial budgets such as "40 to 80 trials" are only valid when the trial unit is
defined. This project should report budgets in ledger rows or in the explicit
factorized formula above.

`max_profiles_per_family` is only a per-family profile-file cap. It does not
guarantee that the full plan fits under `max_hpo_plan_rows` after Stage 01
chooses one or two candidate inputs. Recompute the planned-row formula after the
final Stage 01 handoff is selected.

## 9. Fold Design

All Stage 02 comparisons must use chronological train-inner folds built only
from Stage 00's frozen training partition.

Required fold rules:

- Use rolling, expanding-window, or purged/embargoed time-series folds.
- Do not use shuffled splits.
- Preserve per-ticker chronology.
- Do not let a label horizon cross split boundaries or trading-day boundaries.
- Fit preprocessing, scaling, imputation, class/sample weighting, early
  stopping, and model-specific transforms only on each inner-train slice.
- Evaluate each trial only on the corresponding inner-validation slice.
- Reuse the same folds across candidate families whenever row eligibility
  permits it.

For multi-ticker modeling, the fold manifest must state whether rows are pooled
across tickers, split per ticker, or ticker-aware. If calendar alignment across
tickers is used, the implementation must document why it does not leak later
information into earlier train-inner evaluation rows.

## 10. Same-Row Candidate Comparability

Same-row fairness must cover both candidate-versus-baseline and
candidate-versus-candidate comparisons.

Required contracts:

- For every candidate trial, same-row baselines are computed on exactly the same
  eligible rows.
- Cross-family ranking may compare candidates directly only when they share a
  common eligible row contract.
- If two candidate inputs have different finite-row eligibility, Stage 02 must
  either rank within each candidate-input group or compute a declared common
  eligible row intersection before global ranking.
- The ledger must identify the candidate input, feature set, window size, family,
  fold, seed, and row contract used for every score.

This rule matters because feature/window choices can change finite-row
eligibility through warmup, rolling windows, missing values, or sequence-window
construction. A candidate can be fairly compared to its own dummy baseline while
still being unfairly compared to another candidate on a different row set.

## 11. Selection Objective And Gates

The current config declares:

```text
selection_rules.primary_metric = macro_f1
selection_rules.baseline = stratified_dummy_train_prior
```

Formal Stage 02 may keep this primary metric only if the threshold, class
weighting, and decision-policy contract are fixed before trials. If Stage 02
searches loss functions, class/sample weights, or thresholds, the protocol and
config must predeclare how macro F1 is computed and whether a threshold-free
metric is used as the primary ranking key.

Required reported metrics:

- `macro_f1`.
- `balanced_accuracy`.
- `mcc`.
- `roc_auc` when defined for the fold labels.
- Per-class precision, recall, and F1.
- Support counts by class and ticker.
- Delta versus the configured stratified dummy baseline.
- Delta versus majority baseline.

Required selection gates for a frozen primary candidate:

- Positive delta versus same-row stratified dummy on the selected aggregate.
- Positive delta versus same-row majority baseline on the selected aggregate.
- Per-ticker robustness recomputed on Stage 02 fitted candidates. The active
  config declares `selection_rules.minimum_positive_ticker_count=3`; a
  candidate below that floor cannot be frozen for Stage 03.
- No fold chronology, preprocessing, or artifact-contract violation.
- No official validation, test, or holdout contact.

Stage 01 currently uses `family_lcb_selection_policy=median_stage02_family_lcb`
and a `positive_ticker_count` floor. Stage 02 should inherit this robustness
concept or explicitly declare a replacement before fitting. Do not reduce
per-ticker robustness to a tie-break only.

Lower confidence bounds must declare their resampling unit. The current runner
uses fold/seed-level LCB only as a conservative ranking statistic after the
baseline and ticker-robustness gates pass; it does not treat the LCB as a
standalone significance claim. Block/ticker deltas remain ledger audit fields.
If Stage 02 later claims statistical confidence rather than a bounded HPO
ranking, block-level resampling must replace or supplement the current LCB.

## 12. Search Axes

Stage 02 may only search axes declared in config or model search-space files
before execution.

LightGBM allowed axes:

- `num_leaves`.
- `max_depth`.
- `min_data_in_leaf`.
- `learning_rate`.
- `n_estimators`, selected by early stopping on a chronological tail split
  carved from the inner-train rows only. The scored inner-eval fold may not be
  passed as the LightGBM early-stopping `eval_set`.
- `feature_fraction`.
- `bagging_fraction`.
- `bagging_freq`.
- `lambda_l1`.
- `lambda_l2`.
- Predeclared class/sample weighting.

Deep sequence allowed axes:

- Hidden size or channel width.
- Number of layers.
- `kernel_size`.
- Dilation pattern.
- Dropout.
- Learning rate.
- Weight decay.
- Batch size.
- Maximum epochs.
- `early_stopping_patience`.
- Gradient clipping.
- Optional predeclared loss choice.

For the current active runner, deep sequence profiles train for a predeclared
maximum epoch count and use an inner-train chronological tail split for early
stopping and best-epoch restoration when enough rows and both classes are
available. That stopping split is carved only from the trial's inner-train rows;
the scored inner-eval fold is never used for epoch selection. If the tail split
is too small or single-class, the trial must record the fallback reason in the
HPO ledger.

The active Stage 02 search-space files must include only parameters consumed by
the implemented builders. For the current TCN builder, depth is represented by
the length of `channels`; causal padding, dilation base, and residual skip
behavior are fixed implementation choices unless code and tests wire them into
the model before execution. For the current TCN, `learning_rate` and
`weight_decay` are active training axes, not inherited constants. For the current
`standard_dlinear` builder, `individual_channels` is not an active axis.

MS-DLinear+TCN additional axes:

- `moving_avg_window`.
- DLinear branch width or projection size.
- TCN residual channels.
- Fusion hidden size.
- Fusion dropout.
- Branch weighting or fusion method, if predeclared.

Forbidden search axes:

- Stage 00 label horizon.
- Stage 00 no-trade band.
- Stage 00 split boundaries.
- Stage 00 sample-validity policy.
- Broad feature universe beyond Stage 01 candidate inputs.
- Broad window universe beyond Stage 01 candidate inputs.
- Official validation threshold or tie-breaker.
- Test or holdout wording.

If a defect in Stage 00 or Stage 01 is discovered during Stage 02, stop and issue
an upstream correction request. Do not silently repair the upstream decision
inside Stage 02.

## 13. Modeling Scope Axis

Stage 01 may hand off `stage02_modeling_scope_axis`, such as:

- `pooled_five_ticker`.
- `stock_aware_per_ticker_or_ticker_embedding`.

Stage 02 must decide whether this axis is:

- Metadata describing the candidate input.
- A crossed HPO branch.
- A blocked future feature.

The decision must be explicit before execution. If the axis is crossed with
families or candidate inputs, it counts in the budget formula. If the current
code does not model this axis, the protocol, config, and tests must not pretend
that the active ledger already contains `modeling_scope`.

Future formal HPO ledgers should include `modeling_scope` once the implementation
supports it. Until then, Stage 02 should record the Stage 01 handoff axis in the
manifest or blocked decision without using it as an unimplemented comparison
dimension.

## 14. Feature Semantics And MACD

Stage 02 inherits feature semantics from Stage 01. It does not reinterpret,
recompute, or retune feature definitions.

Current executable Stage 02 rebuilds feature/window tensors from frozen Stage 00
artifacts and raw files. Because of that rebuild, integrity checks are part of
the Stage 02 start gate:

- Stage 00 must freeze raw file `bytes` and `sha256` in `raw_data_manifest.json`
  for newly produced runs.
- Stage 01 must write `feature_rebuild_code_sha256` in its run manifest.
- Stage 02 verifies raw file hashes when those hashes are present in the frozen
  Stage 00 raw manifest.
- Stage 02 compares Stage 01's `feature_rebuild_code_sha256` against the current
  rebuild code hash when the Stage 01 field exists. A mismatch blocks Stage 02.
- Legacy Stage 00/01 runs that predate these fields must be marked in the Stage
  02 manifest as missing provenance; Stage 02 must not fabricate a match.

For `normalized_macd_hist`:

- Stage 01 currently defines normalized MACD features as day-local, per-ticker
  features.
- Stage 02 must consume the Stage 01 candidate input as-is.
- If upstream documentation or artifacts disagree about day-local versus
  continuous-per-ticker semantics, Stage 02 must block and request an upstream
  clarification.
- Stage 02 may record inherited warmup limitations, but it may not fix them by
  changing feature construction inside HPO.

Known limitation to preserve in handoff notes: day-local EMA/MACD reset avoids
overnight carryover but can create early-day warmup behavior. If this becomes a
material concern, Stage 00/01 must revise the feature-validity policy before
Stage 02 consumes it.

## 15. Frozen Selection And Stage 03 Handoff

Formal Stage 02 HPO freezes:

- One primary candidate for Stage 03.
- One fallback candidate for Stage 03.

Freeze requirements:

- Complete params.
- Feature/window artifact references.
- Fold design.
- Row contract.
- Preprocessing contract.
- Seed policy.
- Device provenance.
- HPO ledger reference.
- Baseline/control summary reference.
- `holdout_test_contact=false`.
- `no_final_model_selected=true` until Stage 03 makes the authorized validation
  readout.

Current formal handoff:

- Writes `02_stage03_handoff.json`.
- Sets `ready_for_stage03=true` only when a primary and fallback train-inner HPO
  candidate are frozen.
- Uses a fail-closed `do_not_start_stage03_*` decision when candidate inputs are
  missing, trials fail, or no candidate clears the baseline gates.

Stage 03 may read official validation only after Stage 02 writes a formal frozen
candidate handoff. Stage 03 may not reopen Stage 02 HPO.

## 16. Manifest And Device Provenance

The active manifest contract uses:

```text
holdout_test_contact=false
```

This is the canonical project field for no test/holdout contact. Stage 02 also
records:

- `official_validation_for_selection=false`.
- `no_final_model_selected=true`.
- `stage02_execution_mode`.
- Source Stage 01 run id.
- Input and output artifact names.
- Config hash.
- Notebook hash.

Formal HPO implementation must also record:

- HPO method and budget.
- Search-space hash for every approved family.
- Fold-design hash.
- Random seeds.
- Requested device.
- Resolved device.
- `cuda_available`.
- GPU name or null.
- Device fallback reason.

Do not introduce replacement manifest fields such as
`official_validation_contacted`, `test_contacted`, or `holdout_contacted` unless
the config, code, tests, and downstream consumers are updated together. They may
be added as extra fields, but they do not replace the current
`holdout_test_contact=false` contract.

If the workspace is not a git repository, the manifest should record
`git_commit=null` with an explicit reason rather than fabricating a commit id.

## 17. Required Tests And Static Gates

Minimum tests for the active formal HPO runner:

- Config preserves `scope=validation_only` and `holdout_test_contact=false`.
- Config points to exact Stage 00 and Stage 01 run folders.
- Config points to an exact Stage 01 run folder.
- Config declares enabled HPO families and existing search-space files.
- Budget test validates `max_hpo_plan_rows` and train-inner fold/seed settings.
- Formal output names and baseline controls are declared.
- Optional recurrent controls are not promoted to HPO by default.
- Forbidden search axes are declared.
- `run_stage(config)` blocks when Stage 01 has no candidate inputs.
- `run_stage(config)` runs formal HPO rows for Stage 01 candidates under a
  monkeypatched tiny chronology-safe test fixture.
- HPO trial ledger schema.
- Baseline same-row contract across candidate-versus-baseline comparisons.
- Candidate selection ranks within candidate-input groups first, then chooses
  primary/fallback from candidate winners while respecting configured family
  caps where possible.
- Per-ticker robustness floor blocks Stage 03 readiness when no candidate meets
  `minimum_positive_ticker_count`.
- LightGBM early stopping uses an inner-train chronological tail split and never
  the scored inner-eval fold.
- Frozen candidate schema.
- Baseline/control summary schema.
- `run_stage(config)` rejects Stage 01 holdout/test contact.
- `run_stage(config)` rejects Stage 01-approved families not enabled in Stage 02.
- Notebook static gate verifies safe defaults, package-backed bootstrap, and no
  direct official validation/test/holdout metric reads.

Additional tests to add if future code broadens the modeling surface:

- Candidate-versus-candidate row-contract comparability.
- Fold chronology and purge/embargo checks.
- Train-only preprocessing and early-stopping checks.
- Device provenance schema.
- No official validation/test/holdout read during HPO.
- Static gate that rejects unbudgeted families, losses, thresholds, or modeling
  scope axes.

## 18. Colab Checkpointing

Colab-managed runtimes are temporary. Stage 02 must therefore separate local
runtime execution from durable storage. Stage 02 uses two different durable
storage concepts:

- Drive result backup: copy the Stage 02 run artifacts to
  `My Drive/lst_models/results/02_model_hpo_train_inner/<stage02_run_id>/`.
  This is the canonical durable result location for downstream stages.
- Drive checkpoint archive: write compact zip archives under
  `My Drive/lst_models/checkpoints/02_model_hpo_train_inner/<stage01_run_id>/`.
  This is for recovery/audit support, not for downstream result lookup.

Rules:

- Execute from the local Colab VM path, not directly from a mounted Drive folder.
- Keep default committed checkpoint archive writes off unless the operator
  explicitly enables them.
- When `RUN_STAGE02_DRIVE_BACKUP=True` and Stage 02 runs, upload the completed
  Stage 02 result files immediately after `run_stage` returns.
- The Drive result backup must create/update `drive_backup_manifest.json` in
  the Stage 02 local run folder and upload it to the same Drive run folder. The
  manifest must record `stage_name`, `run_id`, local output dir, Drive path
  parts, Drive folder id, uploaded file names, uploaded relative paths, Drive
  file ids, uploaded byte sizes, and sync timestamp.
- When checkpointing is enabled, write a small local checkpoint directory first,
  then upload a compressed archive to Drive.
- Prefer a small number of archive uploads over many small Drive file writes.
- Do not move files between Drive folders through Colab as the primary checkpoint
  mechanism; if that operation is interrupted, data may be lost in transit.
- Checkpoint only Stage 02-safe data: Stage 02 config, protocol, search-space
  files, exact Stage 00 artifacts, exact Stage 01 handoff artifacts, and Stage
  02 formal run outputs. Do not checkpoint official validation, test, or holdout
  artifacts.
- Post-run Drive result backup saves the active formal result files:
  `run_manifest.json`, `artifact_inventory.csv`,
  `02_model_hpo_train_inner_summary.csv`, `02_hpo_plan_ledger.csv`,
  `02_hpo_trial_ledger.csv`, `02_hpo_summary.csv`,
  `02_baseline_control_summary.csv`, `02_frozen_candidate.json`,
  `02_frozen_candidate.md`, `02_best_params_by_family.json`,
  `02_stage03_handoff.json`, frozen param YAML files when produced, and
  `drive_backup_manifest.json`.
- Drive result backup must preserve `artifact_inventory.csv` relative paths.
  Files under `frozen_params/` must remain under `frozen_params/` in the Drive
  run folder; backup code must not flatten subdirectories by uploading every
  file directly under the run folder.
- Pre-run checkpoint may archive the Stage 02 sidecars and exact Stage 00/01
  input artifacts needed to reconstruct the HPO run.
- Post-run checkpoint may archive the Stage 02 run folder after `run_stage`
  returns.
- The runner writes incremental local checkpoints after bounded trial batches
  according to `checkpointing.checkpoint_every_trials`.
- A checkpoint archive does not make Stage 02 ready for Stage 03. Readiness still
  depends on `02_stage03_handoff.json`.

## 19. Scientific Risks And Protections

Risk: Protocol and executable contract diverge.
Protection: Keep config, code, notebook, protocol, and tests synchronized when
artifact names, gates, families, or search axes change.

Risk: HPO overfitting to train-inner folds.
Protection: Bound the family count, profile count, folds, seeds, and all crossed
axes before execution. Freeze candidates before Stage 03.

Risk: Budget arithmetic does not close.
Protection: Use the factorized planned-row formula and fail before execution
when the plan exceeds `max_hpo_plan_rows`.

Risk: Time-series leakage.
Protection: Use chronological rolling, expanding, or purged/embargoed folds and
fit preprocessing only on inner-train rows.

Risk: Validation-budget leakage.
Protection: Stage 02 cannot read official validation, test, or holdout metrics.
Stage 03 is the first official validation readout stage.

Risk: Unfair baselines.
Protection: Require same-row baseline contracts, controlled baseline seeds, and
explicit deltas.

Risk: Unfair cross-candidate ranking.
Protection: Require common eligible row contracts or rank within candidate-input
groups.

Risk: Per-ticker weakness hidden by pooling.
Protection: Preserve Stage 01's positive ticker robustness gate or explicitly
declare a replacement before fitting.

Risk: Model zoo inflation.
Protection: Keep the upstream-approved candidate count small, label controls
separately, and block rather than silently changing Stage 01's handoff.

Risk: Feature semantics drift.
Protection: Consume Stage 01 feature definitions as frozen inputs and block on
upstream contradictions.

Risk: Colab runtime loss.
Protection: Use local execution with optional compressed Drive checkpoint
archives for pre-run inputs and post-run outputs. Formal HPO requires
incremental runner-level checkpointing.

## 20. Evidence Basis

This protocol is aligned with:

- Stage 00 data/split/label/sample freeze requirements.
- Stage 01 feature/window and family-shortlist requirements.
- The current Stage 02 config, formal HPO runner, notebook, and tests.
- The project route guide's one-notebook, one-protocol, one-config contract.
- Time-series leakage controls for chronological train-inner evaluation.
- Ian-route guidance that weak-signal stock direction modeling should emphasize
  disciplined baselines, controlled comparisons, and defensible model claims
  rather than broad opportunistic model-zoo search.

Ian-route notes are design guidance, not performance evidence. Stage 02 claims
must be based only on Stage 02 train-inner artifacts and must remain separate
from Stage 03 official validation outcomes.

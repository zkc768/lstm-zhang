# 02 Model HPO Train-Inner Protocol

Status: draft protocol.

Scope: V2 `lst_models` route only. This document defines Stage 02 train-inner
HPO planning and execution boundaries. Stage 02 does not read official
validation, test, or holdout rows and does not make final validation claims.

## 1. Stage Boundary

Stage 02 answers:

- Which pre-approved Stage 01 candidate inputs can enter bounded train-inner
  HPO.
- Which hyperparameter profiles are scheduled for each approved model family.
- Whether train-inner HPO has enough completed evidence to freeze family-level
  parameters for Stage 03 official validation readout.

Stage 02 does not answer:

- Which model wins on official validation.
- Which model wins on holdout/test.
- Whether thesis performance claims are supported.
- Whether Stage 00 labels, split boundaries, or Stage 01 feature/window choices
  should be changed.

Direct route answer:

```text
Stage 02 is train-inner HPO only. It may freeze model-family hyperparameters
for Stage 03, but it does not read official validation and does not select a
final model.
```

## 2. Required Inputs

Stage 02 may start only after Stage 01 exports one exact run folder containing:

- `run_manifest.json`
- `artifact_inventory.csv`
- `01_candidate_inputs.json`
- `01_feature_window_search_summary.csv`
- `01_train_inner_probe_ledger.csv`
- `01_train_inner_fold_manifest.csv`

Stage 02 must consume `01_candidate_inputs.json` as the only source of approved
candidate inputs and approved HPO families. It must not infer candidates from
the latest run, screenshots, notebook output, old notebooks, or official
validation results.

If Stage 01 says `candidate_inputs=[]`, `approved_model_families_for_stage02=[]`,
or a `decision` beginning with `do_not_start`, Stage 02 must stop before any HPO
fit and write a blocked run manifest. It must not override Stage 01.

## 3. Allowed HPO Families

The Stage 02 core family set is:

```text
lightgbm
standard_dlinear
tcn
ms_dlinear_tcn
```

`simple_gru` and `shallow_lstm` remain optional fixed controls only. They are
not Stage 02 core HPO families unless a later protocol revision changes the
research question before execution.

## 4. Search Space Policy

HPO ranges must be predeclared in small YAML files under:

```text
configs/models/<model_family>/search_space.yaml
```

Stage 02 must not hide search ranges in notebook cells or model source files.
The stage config controls which model-family search-space files are active.

The HPO unit is:

```text
candidate_input x model_family x hpo_profile x train_inner_fold x seed
```

Recommended bounded budget:

```text
max_hpo_plan_rows: 240
```

If the planned grid exceeds the cap, Stage 02 must fail before fitting.

## 5. Train-Inner Only Rule

All HPO fitting and scoring is inside train-inner folds derived from the Stage
00 train interval and the Stage 01 candidate-input handoff. Stage 02 must not
use official validation as a tie-breaker, early-stop readout, feature/window
rescue path, or family-selection signal.

Required guards:

- chronological train-inner folds only;
- no shuffled validation;
- train-only preprocessing;
- same-row dummy baseline where model metrics are reported;
- `holdout_test_contact=false` in the manifest;
- no active read, transform, window, score, or summary of closed holdout/test.

## 6. Output Artifacts

Stage 02 writes one compact run folder:

```text
results/02_model_hpo_train_inner/<run_id>/
  run_manifest.json
  artifact_inventory.csv
  02_model_hpo_train_inner_summary.csv
  02_hpo_plan_ledger.csv
  02_best_params_by_family.json
  02_stage03_handoff.json
```

Minimum `02_hpo_plan_ledger.csv` columns:

```text
candidate_id
feature_set
window_size
model_family
hpo_profile_id
fold_id
seed
fit_status
macro_f1
balanced_accuracy
baseline_macro_f1
delta_macro_f1_vs_baseline
selected_for_stage03
error_message
```

Skipped and blocked rows must remain explicit. If no Stage 01 candidate is
approved, the ledger may be empty but must keep the schema.

## 7. Decision Rule

Stage 02 may hand off to Stage 03 only when:

- at least one candidate input is approved by Stage 01;
- at least one HPO row completes for each active core family;
- every completed comparison includes same-row dummy baseline metrics;
- the selected parameter set is frozen in `02_best_params_by_family.json`;
- `02_stage03_handoff.json` records no official validation or holdout/test
  contact.

Allowed wording:

```text
Frozen train-inner HPO parameters for Stage 03 validation readout.
Stage 02 train-inner HPO completed for approved families.
Stage 02 blocked because Stage 01 produced no candidate inputs.
```

Forbidden wording:

```text
final model
official validation winner
holdout winner
test winner
proved best model
```

## 8. Implementation Gate

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
- one user-facing notebook for Stage 02;
- one protocol doc and one config for Stage 02;
- one `run_stage(config)` entry point;
- small Python helpers, no framework expansion;
- validation-only scope unless explicitly authorized;
- no official-validation selection;
- no holdout/test read, transform, window, score, or summary;
- train-only preprocessing;
- same-row dummy baseline comparison where metrics are reported;
- run manifest with `holdout_test_contact=false`;
- notebook static-gate compatibility.

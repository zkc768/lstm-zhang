# Stage 03 Bundle (Batch B) Implementation Plan

> **For agentic workers:** Execute task-by-task with review checkpoints.
> Required reading before any code (AGENTS.md §2): `AGENTS.md`,
> `docs/lst_models_code_style_and_route_guide.md`,
> `docs/lst_models_v2_route_roadmap.md` (Phases 2-4, decisions D1-D4 frozen
> 2026-06-09), `docs/protocols/02_model_hpo_train_inner_protocol.md`, and the
> target files of each task. Steps use checkbox syntax for tracking.
> Git commits only when the user has authorized committing (AGENTS.md §13);
> each task lists its commit point for when that authorization exists.

**Goal:** Implement the complete Stage 03 sidecar bundle (protocol, config,
runner, notebook, tests) plus the Stage 04/06 pre-registration cores, so the
official-validation readout can execute exactly once under frozen rules.

**Architecture:** `run_stage(config)` in a new
`src/lst_models/stages/frozen_validation_readout.py` that (1) fail-closed
verifies the full Stage 00→01→02 artifact chain, (2) rebuilds train +
validation feature/window tensors with the same frozen builders Stage 02 used,
(3) refits the frozen primary candidate per seed with mechanism-frozen
chronological-tail early stopping (D1) on all eligible official-train rows
(D2), (4) scores all eligible official-validation rows exactly once per seed,
(5) writes aggregate readouts, a per-row prediction dump, same-row baselines,
and a decision record with a scoring-event ledger. Heavy reuse of already
audited Stage 01/02 helpers; no new framework.

**Tech stack:** existing project stack only — pandas/numpy/sklearn/lightgbm/
torch via the helpers in `src/lst_models/`. No new dependencies.

**Pending external input (BLOCKING for execution, not for implementation):**
the superseding Stage 02 run id from roadmap Phase 0.3 (the completed run
`20260609_100637_704705` is pre-fix and must not be pinned). The two
fill-points are marked `<NEW_STAGE02_RUN_ID>` in Task 4 and Task 5; the config
contract test asserts the value is NOT the superseded id.

> **Correction record (2026-06-10, post-Route-A migration `4672f4d`):** the
> import instructions in Tasks 6-8 below predate the Route A code migration
> and are superseded. Cross-stage imports (`from lst_models.stages import
> feature_window_search as stage01`, `stage02._lightgbm_params`, etc.) are now
> forbidden by `tests/contracts/test_module_structure.py`; Stage 03 consumes
> public domain modules instead (`data`, `features`, `splits`, `windows`,
> `fitting`, `metrics`, `artifacts`). The shared helpers were dedupe-moved on
> 2026-06-10: `lightgbm_hpo_params`, `lightgbm_inner_train_early_stopping_split`,
> `probe_trial_config`, `profile_params`, `torch_training_defaults`, and
> `PROBE_BY_FAMILY` live in `fitting.py`; `score_registry_baseline` lives in
> `metrics.py`. Upstream pins moved to the R3 clean chain (Stage 00
> `20260610_051705_347450`, Stage 01 `20260610_075002`); the superseded Stage
> 02 list is now `["20260609_100637_704705", "20260610_010019_507648"]`.
> Tasks 1-10 (protocol, config, contract test, runner entry gates, refit
> wrappers, scoring loop, artifacts) are implemented at HEAD; Task 11
> (notebook trio) and the runner resume entry are the remaining items.

```text
placement_decision:
  target_file_type: protocol|stage_config|python_module|test|notebook (per task below)
  target_path: see File Structure
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: refit/scoring/gate logic is reusable, safety-critical, and
    testable -> src/lst_models/stages/frozen_validation_readout.py per guide §5
  why_not_utils: every helper has a domain home (stage module, metrics.py,
    artifacts.py); no utils.py is created
  safety_tests: tests/contracts/test_stage03_config_contract.py,
    tests/stages/test_stage03_run_stage_smoke.py,
    tests/notebooks/test_stage03_notebook_static.py,
    tests/contracts/test_metrics.py (per_class_metrics)
```

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `docs/protocols/03_frozen_validation_readout_protocol.md` | Create | Pre-registered readout contract (T1) |
| `docs/protocols/04_diagnostics_ablation_protocol.md` | Create | D3 pre-registration core only (T2) |
| `docs/protocols/06_ian_final_progress_record_protocol.md` | Create | D4 pre-registration core only (T2) |
| `src/lst_models/metrics.py` | Modify | add `per_class_metrics` (T3) |
| `tests/contracts/test_metrics.py` | Modify | per-class metric test (T3) |
| `configs/stages/03_frozen_validation_readout.yaml` | Create | frozen execution parameters (T4) |
| `tests/contracts/test_stage03_config_contract.py` | Create | config contract gates (T5) |
| `src/lst_models/stages/frozen_validation_readout.py` | Create | `run_stage(config)` (T6-T10) |
| `tests/stages/test_stage03_run_stage_smoke.py` | Create | gate/behavior/schema tests (T6-T10) |
| `notebooks/03_frozen_validation_readout_colab.ipynb` | Create | user-facing execution surface (T11) |
| `scripts/notebooks/generate_03_frozen_validation_readout_colab.py` | Create | agent notebook generator (T11) |
| `tests/notebooks/test_stage03_notebook_static.py` | Create | static gate (T11) |
| `docs/lst_models_v2_route_roadmap.md` | Modify | check off Phase 3 items (T13) |

Module size targets (guide §10): stage module ≤ ~900 LOC by reusing Stage
01/02 helpers; orchestration `run_stage` ≤ 70 lines by delegation.

---

## Task 1: Protocol `03_frozen_validation_readout_protocol.md`

**Files:** Create `docs/protocols/03_frozen_validation_readout_protocol.md`

The protocol is the pre-registration instrument; it must be reviewable text
before any Stage 03 code lands. Sections and binding content (each maps to a
roadmap B-item):

- [ ] **Step 1.1 Write sections 1-3 (gate, role, wording).**
  - §1 Implementation Gate: standard AGENTS.md block (copy shape from
    `02_model_hpo_train_inner_protocol.md` §1) with this protocol's own
    placement decision.
  - §2 Stage Role: frozen official-validation readout; inputs = exactly one
    primary + exactly one fallback from the superseding Stage 02 run; does
    NOT do HPO, model/feature/window selection, threshold tuning, loss
    selection, calibrator fitting, or holdout/test contact. `scope:
    validation_only` retains the project meaning "no test/holdout contact";
    Stage 03 additionally records `official_validation_contact=true`,
    `official_validation_for_selection=false`.
  - §3 Wording Rules. Forbidden (superset of Stage 02 config list): `final
    model`, `official validation winner`, `holdout winner`, `test winner`,
    `proved best model`, `generalization proven`, `profitable`,
    `holdout-ready`, `selected by official validation`, `chosen threshold`.
    Allowed: `validation-only evidence`, `official validation readout`,
    `candidate met/did not meet predeclared validation-readout criteria`.
    Note: `no_final_model_selected=true` is retained in Stage 03 outputs —
    the readout characterizes a frozen candidate; it does not crown a model.
- [ ] **Step 1.2 Write §4 Entry Gates (roadmap B2, verbatim list).** Exact
  Stage 02 run folder by run id with `ready_for_stage03=true`, exactly one
  primary AND one fallback (Stage 02 requires both:
  `model_hpo_train_inner.py:1628-1635`); full Stage 02 artifact list present
  with inventory `bytes`/`sha256` verification via
  `artifacts.require_artifacts`; `02_hpo_plan_ledger.csv` sha256 must differ
  from `02_hpo_trial_ledger.csv` sha256 (post-`6182508` packaging proof);
  exact Stage 00 run folder (six artifacts + inventory) and exact Stage 01
  run folder (`run_manifest.json`, `artifact_inventory.csv`,
  `01_candidate_inputs.json`, `01_feature_window_search_summary.csv`); raw
  files by Drive file ID with sha256/bytes verification when present in the
  frozen Stage 00 raw manifest (legacy-tolerant, reason recorded); run-id
  chain consistency (config stage00/01/02 ids == handoff/frozen-candidate
  `source_*_run_id` fields); `stage01.feature_rebuild_code_sha256()` must
  equal the Stage 02 manifest's `stage02_feature_rebuild_code_sha256`;
  rebuilt train-row totals and per-ticker counts for the scored candidate
  must equal `01_feature_window_search_summary.csv` (same parity check Stage
  02 ran); `holdout_test_contact=false` and
  `official_validation_for_selection=false` on every upstream manifest and
  handoff. Legacy-provenance sentence (roadmap 0.4) is quoted here.
- [ ] **Step 1.3 Write §5 Refit Recipe (D1+D2, frozen).** Refit on ALL
  eligible official-train rows; per frozen seed in `[101, 202]`:
  LightGBM refits reuse `_lightgbm_inner_train_early_stopping_split`
  semantics (chronological tail from the refit rows,
  `early_stopping_validation_fraction=0.2`, minimums 128/128,
  `early_stopping_rounds=25`); torch refits reuse
  `inner_train_chronological_tail` early stopping (fraction 0.2, minimums
  128/128, patience 8, max epochs 64, best-epoch restoration); class weights
  recomputed on the refit fit-subset rows; tail-split fallback reasons
  recorded per refit. Stage 02 absolute metrics are declared non-comparable
  to Stage 03 absolute metrics (equal-allocation subsample vs natural
  distribution; Zadrozny 2004). Feasibility clause: the notebook pre-flight
  cell estimates materialized bytes BEFORE any scoring; if infeasible, abort
  with zero scoring events, amend config to the predeclared
  deterministic-even-stride raised-cap fallback, and start a fresh run —
  never tune the policy after a scoring event.
- [ ] **Step 1.4 Write §6 Validation Windowing + Same-Row Baselines (B4).**
  Validation rows are windowed for the first time under Stage 00 §9 rules
  (windows per ticker / per split / per trading day — no lookback across
  2013-09-16; day-start warmup rows ineligible); eligible-row contract is
  computed by the same frozen builder (`stage01._build_window_dataset`) and
  recorded as `n_scored_validation_samples` + `eval_sample_id_hash`.
  Same-row baselines on identical validation rows: the four Stage 00
  registry baselines, train-prior fit on the refit rows' labels, dummy seeded
  with the trial seed. Every candidate row reports BOTH deltas
  (`..._vs_stratified_dummy_train_prior`, `..._vs_majority_train_prior`).
- [ ] **Step 1.5 Write §7 Predeclared Readout Criteria (B5, frozen).**
  Judged on the seed-aggregate (mean over seeds; per-seed reported):
  `mean(delta_macro_f1_vs_stratified_dummy_train_prior) > 0` AND
  `mean(delta_macro_f1_vs_majority_train_prior) > 0` AND
  `positive_ticker_count >= 3` where per-ticker deltas are averaged across
  seeds before counting positives. Outcomes: met → Stage 04/05 proceed with
  validation-only claims; not met → record
  `did_not_meet_predeclared_validation_readout_criteria`, NO fallback
  activation, NO retuning; forward path is honest reporting + optional
  pre-registered V2.1. Stages 04/05 run either way.
- [ ] **Step 1.6 Write §8 Fallback Policy (B6, frozen).** Triggers allowed
  ONLY before the first scoring event of the primary:
  `missing_frozen_artifact`, `schema_or_hash_mismatch`,
  `refit_crash_before_any_scoring`, `candidate_not_reconstructable`.
  Forbidden triggers: weak metrics, below-dummy, per-ticker instability.
  After the first scoring event nothing activates the fallback; a mid-seed
  crash is recorded as an incomplete readout. Fallback activation, reason,
  and every scoring event enter `03_decision_record.json`.
- [ ] **Step 1.7 Write §9 Metrics + §10 Required Artifacts (B7+B8).** Metric
  list and the seven artifact schemas exactly as defined in Task 7/Task 9
  column constants (copy the column lists into the protocol so doc and code
  freeze together). CI/LCB: only the predeclared trading-day block bootstrap
  (`metrics.block_bootstrap_macro_f1_delta`, blocks = `ticker|trading_day`)
  reported as uncertainty context, never as a selection device.
- [ ] **Step 1.8 Write §11 Execution Discipline + §12 Tests + §13 Risks.**
  One scoring event per seed×candidate; scoring-event ledger; checkpoints to
  `My Drive/lst_models/checkpoints/03_frozen_validation_readout/<run_id>/`
  after each seed refit with `status=incomplete`/pending-units/resume
  instructions; durable result save to
  `My Drive/lst_models/results/03_frozen_validation_readout/<run_id>/`;
  minimum test list = the three test files of this plan; risk table mirrors
  roadmap §10 rows relevant to Stage 03.
- [ ] **Step 1.9 Self-check.** Every D1/D2 number (0.2, 128, 25, 8, 64,
  seeds [101,202], ticker floor 3) appears once in protocol text and will be
  asserted by the config contract test (Task 5). Commit point:
  `docs(stage03): pre-register frozen validation readout protocol`.

## Task 2: Stage 04/06 pre-registration cores

**Files:** Create `docs/protocols/04_diagnostics_ablation_protocol.md`,
`docs/protocols/06_ian_final_progress_record_protocol.md`

- [ ] **Step 2.1 `04_diagnostics_ablation_protocol.md` (D3 frozen core).**
  Status line: "pre-registration core; operational detail completed in Batch
  C without changing this section." Binding content: Stage 04 reads frozen
  Stage 03 artifacts only; new official-validation fit-predict events = 0;
  ablations (`dlinear_only`, `tcn_only`, `last_step_mlp`,
  `last_step_lightgbm_control`) are fit and scored on Stage 02 train-inner
  folds only, same fold/row/baseline contracts; calibration is measure-only
  (ECE/Brier/reliability on `03_validation_predictions.csv`; no calibrator
  fitting on official validation); selective/no-trade analysis reports full
  risk-coverage/AURC curves with no recommended operating point; Stage 04
  cannot change the Stage 03 outcome — findings become limitations or V2.1
  pre-registration items.
- [ ] **Step 2.2 `06_ian_final_progress_record_protocol.md` (D4 frozen
  core).** Stage 06 = progress record + reproducibility inventory; closed
  holdout/test (≥ 2017-01-25) stays closed; claims remain validation-only;
  honesty section records V1's historical contact with the post-2017 segment
  ("guarded, historically-contacted test" if ever opened); future-blind or
  external-ticker readouts are V2.1 pre-registration options, never silent
  upgrades. Ian-requirement mapping table stub with columns
  `requirement | stage | artifact | status`.
- [ ] **Step 2.3 Commit point:**
  `docs(stage04,stage06): freeze D3/D4 pre-registration cores`.

## Task 3: `metrics.per_class_metrics`

**Files:** Modify `src/lst_models/metrics.py`, modify
`tests/contracts/test_metrics.py`

- [ ] **Step 3.1 Failing test** in `tests/contracts/test_metrics.py`:

```python
def test_per_class_metrics_matches_sklearn_and_handles_missing_class() -> None:
    y_true = np.array([0, 0, 1, 1, 1])
    y_pred = np.array([0, 1, 1, 1, 0])
    result = metrics.per_class_metrics(y_true, y_pred)
    assert result["precision_down"] == pytest.approx(0.5)
    assert result["recall_down"] == pytest.approx(0.5)
    assert result["f1_down"] == pytest.approx(0.5)
    assert result["precision_up"] == pytest.approx(2.0 / 3.0)
    assert result["recall_up"] == pytest.approx(2.0 / 3.0)
    assert result["support_down"] == 2 and result["support_up"] == 3
    empty = metrics.per_class_metrics(np.array([1, 1]), np.array([1, 1]))
    assert empty["support_down"] == 0 and empty["f1_down"] == 0.0
```

- [ ] **Step 3.2 Run:** `E:/codex_workspace/_envs/py311_shared/python.exe -m
  pytest tests/contracts/test_metrics.py -q` → expected FAIL
  (`AttributeError: per_class_metrics`).
- [ ] **Step 3.3 Implement** in `src/lst_models/metrics.py` (after
  `score_classifier`):

```python
def per_class_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Per-class precision/recall/F1/support over fixed labels {0, 1}."""
    from sklearn.metrics import precision_recall_fscore_support

    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(BINARY_LABELS), zero_division=0
    )
    return {
        "precision_down": float(precision[0]),
        "recall_down": float(recall[0]),
        "f1_down": float(f1[0]),
        "support_down": int(support[0]),
        "precision_up": float(precision[1]),
        "recall_up": float(recall[1]),
        "f1_up": float(f1[1]),
        "support_up": int(support[1]),
    }
```

- [ ] **Step 3.4 Run again** → PASS. Also fix the `compute_metric_lcb`
  docstring (roadmap A6): replace "one-sided 95%" with "one-sided 97.5%
  (lower endpoint of the two-sided 95% Student-t interval)".
- [ ] **Step 3.5 Commit point:** `feat(metrics): per-class metrics + LCB docstring fix`.

## Task 4: Stage 03 config

**Files:** Create `configs/stages/03_frozen_validation_readout.yaml`

- [ ] **Step 4.1 Write the config** (complete; `<NEW_STAGE02_RUN_ID>` is the
  Phase 0.3 output and the ONLY permitted edit afterward):

```yaml
stage_name: 03_frozen_validation_readout
route: lst_models
scope: validation_only
holdout_test_contact: false
official_validation_contact: true
official_validation_for_selection: false

inputs:
  stage00_run_id: "20260609_015034_927813"
  stage00_runtime_run_dir: /content/lst_models_results/00_data_split_label_freeze/20260609_015034_927813
  stage00_drive_path_parts: [lst_models, results, 00_data_split_label_freeze, "20260609_015034_927813"]
  required_stage00_artifacts:
    - raw_data_manifest.json
    - split_freeze.json
    - label_policy.json
    - baseline_registry.json
    - sample_event_index.csv
    - run_manifest.json
    - artifact_inventory.csv
  stage01_run_id: "20260609_070204"
  stage01_runtime_run_dir: /content/lst_models_results/01_feature_window_search/20260609_070204
  stage01_drive_path_parts: [lst_models, results, 01_feature_window_search, "20260609_070204"]
  required_stage01_artifacts:
    - run_manifest.json
    - artifact_inventory.csv
    - 01_candidate_inputs.json
    - 01_feature_window_search_summary.csv
  stage02_run_id: "<NEW_STAGE02_RUN_ID>"
  stage02_runtime_run_dir: /content/lst_models_results/02_model_hpo_train_inner/<NEW_STAGE02_RUN_ID>
  stage02_drive_path_parts: [lst_models, results, 02_model_hpo_train_inner, "<NEW_STAGE02_RUN_ID>"]
  superseded_stage02_run_ids: ["20260609_100637_704705"]
  required_stage02_artifacts:
    - run_manifest.json
    - artifact_inventory.csv
    - 02_model_hpo_train_inner_summary.csv
    - 02_hpo_plan_ledger.csv
    - 02_hpo_trial_ledger.csv
    - 02_hpo_summary.csv
    - 02_baseline_control_summary.csv
    - 02_frozen_candidate.json
    - 02_frozen_candidate.md
    - 02_best_params_by_family.json
    - 02_stage03_handoff.json
  raw_data_manifest: configs/lst_models_data.yaml
  raw_data_dir: /content/lst_models_raw_stock_data
  notebook_path: notebooks/03_frozen_validation_readout_colab.ipynb

outputs:
  output_dir: /content/lst_models_results/03_frozen_validation_readout
  manifest: run_manifest.json
  artifact_inventory: artifact_inventory.csv
  validation_readout: 03_validation_readout.csv
  per_ticker_readout: 03_per_ticker_readout.csv
  seed_summary: 03_seed_summary.csv
  same_row_baselines: 03_same_row_baselines.csv
  validation_predictions: 03_validation_predictions.csv
  decision_record: 03_decision_record.json

readout:
  seeds: [101, 202]
  refit_rows: all_eligible_official_train_rows
  scoring_rows: all_eligible_official_validation_rows
  refit_recipe: frozen_mechanism_chronological_tail_early_stopping
  score_each_seed_candidate_exactly_once: true
  max_materialized_train_bytes: 2000000000

predeclared_criteria:
  aggregate: mean_over_seeds
  require_delta_macro_f1_vs_stratified_dummy_train_prior_positive: true
  require_delta_macro_f1_vs_majority_train_prior_positive: true
  minimum_positive_ticker_count: 3
  per_ticker_aggregation: mean_delta_across_seeds_then_count_positive

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

baseline_controls:
  mandatory:
    - stratified_dummy_train_prior
    - majority_train_prior
    - constant_up
    - constant_down

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
  checkpoint_after_each_seed: true
  checkpoint_dir: /content/lst_models_checkpoints/03_frozen_validation_readout

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

  The two training-defaults blocks are byte-equal copies of the Stage 02
  frozen values (`configs/stages/02_model_hpo_train_inner.yaml:102-126`);
  Task 5 asserts the equality so drift is impossible.
- [ ] **Step 4.2 Commit point:** `feat(stage03): frozen readout config`.

## Task 5: Config contract test

**Files:** Create `tests/contracts/test_stage03_config_contract.py`

- [ ] **Step 5.1 Write the tests** (complete assertions; follow the loading
  pattern of `tests/contracts/test_stage02_config_contract.py`):

```python
CONFIG = load_yaml(REPO_ROOT / "configs/stages/03_frozen_validation_readout.yaml")
STAGE02_CONFIG = load_yaml(REPO_ROOT / "configs/stages/02_model_hpo_train_inner.yaml")

def test_scope_and_contact_flags() -> None:
    assert CONFIG["scope"] == "validation_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["official_validation_contact"] is True
    assert CONFIG["official_validation_for_selection"] is False

def test_upstream_run_ids_chain() -> None:
    inputs = CONFIG["inputs"]
    assert inputs["stage00_run_id"] == "20260609_015034_927813"
    assert inputs["stage01_run_id"] == "20260609_070204"
    assert inputs["stage02_run_id"] not in inputs["superseded_stage02_run_ids"]
    assert inputs["stage02_run_id"] != "<NEW_STAGE02_RUN_ID>", (
        "fill inputs.stage02_run_id with the superseding Stage 02 run id "
        "(roadmap Phase 0.3) before executing Stage 03"
    )
    assert inputs["stage02_run_id"] in inputs["stage02_runtime_run_dir"]

def test_frozen_training_defaults_match_stage02() -> None:
    assert CONFIG["lightgbm_training_defaults"] == STAGE02_CONFIG["lightgbm_training_defaults"]
    assert CONFIG["probe_training_defaults"]["torch"] == (
        STAGE02_CONFIG["probe_training_defaults"]["torch"]
    )

def test_predeclared_criteria_frozen() -> None:
    criteria = CONFIG["predeclared_criteria"]
    assert criteria["aggregate"] == "mean_over_seeds"
    assert criteria["minimum_positive_ticker_count"] == 3
    assert CONFIG["readout"]["seeds"] == [101, 202]
    assert CONFIG["readout"]["score_each_seed_candidate_exactly_once"] is True

def test_fallback_policy_mechanical_only() -> None:
    policy = CONFIG["fallback_policy"]
    assert "weak_validation_metrics" in policy["forbidden_triggers"]
    assert policy["after_first_scoring_event"] == "never_activate"
    assert set(policy["allowed_triggers"]) == {
        "missing_frozen_artifact", "schema_or_hash_mismatch",
        "refit_crash_before_any_scoring", "candidate_not_reconstructable",
    }

def test_required_artifact_names_and_wording() -> None:
    outputs = CONFIG["outputs"]
    assert outputs["validation_predictions"] == "03_validation_predictions.csv"
    assert outputs["decision_record"] == "03_decision_record.json"
    for phrase in ["final model", "selected by official validation", "chosen threshold"]:
        assert phrase in CONFIG["forbidden"]["wording"]
    assert CONFIG["baseline_controls"]["mandatory"] == [
        "stratified_dummy_train_prior", "majority_train_prior",
        "constant_up", "constant_down",
    ]
```

  Until Phase 0.3 completes, `test_upstream_run_ids_chain` FAILS by design —
  it is the executable reminder that Stage 03 must not run against the
  superseded Stage 02 run. Mark it `@pytest.mark.xfail(strict=False,
  reason="pending roadmap Phase 0.3 stage02 re-run id")` at creation time and
  REMOVE the marker in the same commit that fills the run id.
- [ ] **Step 5.2 Run:** suite stays green (xfail pending). Commit point:
  `test(stage03): config contract`.

## Task 6: Runner — config validation, entry gates, data context

**Files:** Create `src/lst_models/stages/frozen_validation_readout.py`;
create `tests/stages/test_stage03_run_stage_smoke.py`

Reuse imports (all verified to exist):

```python
from lst_models import metrics
from lst_models.artifacts import require_artifacts, write_artifact_inventory, write_json
from lst_models.config import hash_file, hash_mapping, load_yaml
from lst_models.stages import feature_window_search as stage01
from lst_models.stages import model_hpo_train_inner as stage02
```

- [ ] **Step 6.1 Failing gate tests first** (fixture builds tmp fake
  stage00/01/02 run folders; adapt the builder pattern from
  `tests/stages/test_stage02_run_stage_smoke.py`, extending it with a fake
  Stage 02 folder containing handoff/frozen-candidate/ledgers/inventory with
  real sha256 values):

```python
def test_blocks_when_handoff_not_ready(stage_dirs) -> None:
    stage_dirs.write_stage02_handoff(ready_for_stage03=False)
    result = run_stage(stage_dirs.config())
    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["decision"].startswith("do_not_start")
    assert record["official_validation_scoring_events"] == 0

def test_blocks_on_run_id_chain_mismatch(stage_dirs) -> None:
    stage_dirs.write_stage02_handoff(source_stage01_run_id="wrong_id")
    with pytest.raises(ValueError, match="run id"):
        run_stage(stage_dirs.config())

def test_blocks_when_plan_ledger_is_trial_ledger_copy(stage_dirs) -> None:
    stage_dirs.copy_trial_ledger_over_plan_ledger()
    with pytest.raises(ValueError, match="plan ledger"):
        run_stage(stage_dirs.config())

def test_blocks_on_superseded_stage02_run_id(stage_dirs) -> None:
    config = stage_dirs.config()
    config["inputs"]["stage02_run_id"] = config["inputs"]["superseded_stage02_run_ids"][0]
    with pytest.raises(ValueError, match="superseded"):
        run_stage(config)
```

- [ ] **Step 6.2 Implement** `_validate_config` (mirror
  `stage02._validate_config` shape: stage_name, scope, contact flags, seeds
  == frozen candidate seed policy is checked later against the artifact,
  criteria/fallback blocks present), `_verify_entry_gates(config)` returning
  a loaded `Stage03Inputs` dataclass (stage00/01/02 paths + parsed handoff,
  frozen candidate, manifests), implementing every §4 protocol check with
  exact-path/exact-field `ValueError` messages, and
  `_load_readout_data_context(config, inputs)`:

```python
def _load_train_validation_bars(raw_manifest, split_freeze, inputs):
    # mirrors stage01._load_train_bars (feature_window_search.py:390-416)
    # but keeps split.isin(["train", "validation"]) rows; reuses
    # stage01._verify_raw_file_integrity per ticker before resampling.

def _valid_events_for_split(sample_events, split_name):
    # generalizes stage01._train_valid_events (:375-381): filter
    # split == split_name AND valid_label; label -> int; sort by
    # (target_timestamp, ticker, sample_id); raise if empty.
```

  Data context: bars → `stage01._build_feature_frame` (day-local features,
  proven identical for train rows) → train events + validation events.
  Record `stage03_readout_code_sha256` = sha256 over `inspect.getsource` of
  the two new functions above plus `stage01.feature_rebuild_code_sha256()`
  (chain composition documented in the manifest).
- [ ] **Step 6.3 Parity checks:** rebuild the primary candidate's window
  dataset for train events via `stage01._build_window_dataset`; assert total
  and per-ticker counts equal `01_feature_window_search_summary.csv` (reuse
  `stage02._validate_rebuilt_candidate_counts`). Run the gate tests → PASS.
- [ ] **Step 6.4 Commit point:** `feat(stage03): entry gates + data context`.

## Task 7: Runner — refit wrappers (D1 mechanism)

**Files:** Modify `src/lst_models/stages/frozen_validation_readout.py`; add
tests in `tests/stages/test_stage03_run_stage_smoke.py`

- [ ] **Step 7.1 Failing test:** with the tiny fixture and a real LightGBM
  refit (`pytest.importorskip("lightgbm")`), assert the early-stopping tail
  is a chronological subset of refit rows and was passed to `fit`:

```python
def test_lightgbm_refit_uses_train_tail_eval_set(monkeypatch, stage_dirs) -> None:
    captured = {}
    real_fit = LGBMClassifier.fit
    def spy_fit(self, X, y, **kwargs):
        captured["eval_set"] = kwargs.get("eval_set")
        return real_fit(self, X, y, **kwargs)
    monkeypatch.setattr(LGBMClassifier, "fit", spy_fit)
    outcome = _refit_lightgbm_and_predict(profile_params, x_train, train_meta,
                                          x_eval, config, seed=101)
    tail_rows = captured["eval_set"][0][0]
    assert len(tail_rows) < len(x_train)
    assert outcome["early_stopping_source"] == "inner_train_chronological_tail"
    assert len(outcome["predictions"]) == len(x_eval)
```

- [ ] **Step 7.2 Implement `_refit_lightgbm_and_predict`:** build params via
  `stage02._lightgbm_params({"profile_id": ..., **profile_params})`, tail
  split via `stage02._lightgbm_inner_train_early_stopping_split` (pass the
  full refit `train_meta`), fit with the same callbacks pattern as
  `model_hpo_train_inner.py:1134-1148`, then `predict`/`predict_proba` on
  `x_eval`; return predictions, scores, `best_iteration_`, early-stopping
  fields, and `requested_device/resolved_device/device_fallback_reason`
  ("cpu"/"not_gpu_capable_trial").
- [ ] **Step 7.3 Implement `_refit_torch_and_predict`:** probe id via
  `stage02.PROBE_BY_FAMILY[family]`; trial config via
  `stage02._trial_probe_config(config, probe_id, {"profile_id": ...,
  **profile_params})`; call `stage01._fit_torch_sequence_probe(probe_id,
  x_train, y_train, x_eval, trial_config, seed, window_size, n_features,
  train_meta=train_meta)`; map the returned `ProbeFitResult` fields
  (predictions, scores, best_iteration, early-stopping hashes, device
  fields) into the same outcome dict shape. One dispatch function
  `_refit_and_predict(family, ...)` routes lightgbm vs torch families.
- [ ] **Step 7.4 Run tests → PASS.** Commit point:
  `feat(stage03): mechanism-frozen refit wrappers`.

## Task 8: Runner — scoring, aggregation, criteria

**Files:** Modify runner + smoke tests

- [ ] **Step 8.1 Failing tests:** monkeypatch `_refit_and_predict` with a
  deterministic stub (predictions = labels for seed 101, inverted for a
  weak-candidate variant) and assert:

```python
def test_scores_each_seed_exactly_once_and_aggregates(stage_dirs, stub_refit) -> None:
    result = run_stage(stage_dirs.config())
    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["official_validation_scoring_events"] == 2  # one per seed
    seeds = [event["seed"] for event in record["scoring_event_ledger"]]
    assert seeds == [101, 202]
    readout = pd.read_csv(stage_dirs.read_path("03_validation_readout.csv"))
    assert set(readout["seed"].astype(str)) >= {"101", "202", "aggregate_mean"}

def test_weak_primary_never_activates_fallback(stage_dirs, stub_weak_refit) -> None:
    run_stage(stage_dirs.config())
    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["decision"] == "did_not_meet_predeclared_validation_readout_criteria"
    assert record["fallback_activated"] is False
    assert record["criteria"]["delta_vs_stratified_dummy_met"] is False
```

- [ ] **Step 8.2 Implement the per-seed loop:** for each seed in frozen
  order: score the four baselines via `stage02._score_stage02_baseline`
  (y_train = refit labels, y_eval = validation labels, seed) → baseline
  rows; refit + predict; `metrics.score_classifier` +
  `metrics.per_class_metrics` + `stage01._ticker_delta_macro_f1` (vs the
  seed's stratified-dummy predictions) + majority delta; append per-row
  prediction-dump records; append the scoring event
  `{candidate_role, candidate_id, seed, n_rows, timestamp_utc}`; write a
  per-seed checkpoint when `checkpointing.enabled`.
- [ ] **Step 8.3 Implement `_aggregate_and_judge(seed_rows, criteria)`:**
  mean over seeds for both deltas; per-ticker mean-across-seeds then count
  positive; emit per-criterion booleans + overall decision string from
  {`met_predeclared_validation_readout_criteria`,
  `did_not_meet_predeclared_validation_readout_criteria`}.
- [ ] **Step 8.4 Fallback wiring:** wrap candidate reconstruction + refit of
  the PRIMARY in try/except limited to the allowed mechanical trigger
  classes; on trigger BEFORE any scoring event, log
  `fallback_activated=true` + reason and run the identical procedure for the
  fallback candidate; if scoring has started, re-raise and let the decision
  record show an incomplete readout. Tests: corrupt the frozen-params file →
  fallback activates; stub a crash after seed 101's scoring → no fallback,
  `readout_complete=false`.
- [ ] **Step 8.5 Commit point:** `feat(stage03): one-shot scoring + predeclared criteria`.

## Task 9: Runner — artifacts, manifest, decision record

**Files:** Modify runner + smoke tests

- [ ] **Step 9.1 Column constants (also copied verbatim into protocol §10):**

```python
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
PER_TICKER_READOUT_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "ticker", "n_rows",
    "support_up", "support_down", "macro_f1", "balanced_accuracy",
    "accuracy", "f1_up", "f1_down",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "scope",
]
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
SAME_ROW_BASELINE_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "baseline_id", "fit_status",
    "n_train_samples", "n_eval_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "sample_id_hash", "macro_f1",
    "balanced_accuracy", "accuracy", "roc_auc", "mcc", "error_message",
    "scope",
]
VALIDATION_PREDICTION_COLUMNS = [
    "candidate_role", "candidate_id", "model_family", "hpo_profile_id",
    "seed", "sample_id", "ticker", "target_timestamp", "trading_day",
    "y_true", "p_up", "y_pred", "scope",
]
```

- [ ] **Step 9.2 Decision record + manifest.** `03_decision_record.json`
  fields: route, stage_name, source_stage00/01/02_run_id,
  superseded_stage02_run_ids, primary/fallback identity blocks (from the
  frozen candidate), `predeclared_criteria` echo, per-seed outcome rows,
  aggregate values, per-criterion booleans, `decision`,
  `fallback_activated` + `fallback_reason`, `readout_complete`,
  `official_validation_scoring_events`, `scoring_event_ledger` (list),
  `refit_records` (role, seed, best_iteration, early-stopping fields),
  `holdout_test_contact=false`, `official_validation_for_selection=false`,
  `no_final_model_selected=true`. Manifest mirrors the Stage 02 shape plus:
  `official_validation_contact=true`, `official_validation_scoring_events`,
  `stage03_readout_code_sha256`,
  `source_stage02_feature_rebuild_code_sha256` + match flag, device fields
  via the post-`4d2aeeb` runtime-resolution pattern, git-commit fields via
  `stage02._git_commit_fields()`.
- [ ] **Step 9.3 Schema tests:** every output exists with exactly the
  declared columns; prediction-dump row count == n_scored_validation_samples
  × seeds scored; `scope == "validation_only"` on every row; inventory
  includes sha256 for all outputs. Run → PASS.
- [ ] **Step 9.4 Commit point:** `feat(stage03): readout artifacts + decision record`.

## Task 10: Full smoke pass + codegraph

- [ ] **Step 10.1 Run the full fast suite:**
  `E:/codex_workspace/_envs/py311_shared/python.exe -m pytest tests/data
  tests/stages tests/notebooks tests/contracts -q -rs` → expected: green
  except the single intentional Task 5 xfail (pending run id) and the
  env-gated torch skip.
- [ ] **Step 10.2 Codegraph audit (mandatory: new stage entry point, ≥3
  modules touched):** `find_cycles` (expect none; stage03 imports stage01 &
  stage02 one-way), `semantic_search` for duplicate helper names before
  finalizing, `context` on `stage01._build_window_dataset` and
  `stage02._lightgbm_inner_train_early_stopping_split` callers. Record
  result in the task report; if codegraph unavailable, fall back to `rg` +
  `py_compile` and say so.

## Task 11: Notebook + static gate

**Files:** Create `notebooks/03_frozen_validation_readout_colab.ipynb`,
`scripts/notebooks/generate_03_frozen_validation_readout_colab.py`,
`tests/notebooks/test_stage03_notebook_static.py`

- [ ] **Step 11.1 Generate the notebook** with the generator script
  (pattern: `scripts/notebooks/generate_02_model_hpo_train_inner_colab.py`).
  Cell map:
  1. markdown — title, research question, frozen protocol summary, scope.
  2. bootstrap/config cell — `PROJECT_BOOTSTRAP_MODE="github_commit"`,
     `PROJECT_REPO_COMMIT=<full-bundle commit>`, exact-commit clone +
     `sys.path` insert + commit assert (copy nb02 cell).
  3. control cell — `RUN_STAGE03 = False`, `RUN_UPSTREAM_DRIVE_SYNC = False`,
     `RUN_STAGE03_DRIVE_BACKUP = True`, exact upstream run ids printed.
  4. config-load + TRUE runtime injection cell — load YAML, inject
     `raw_data_dir`, `stage00/01/02_runtime_run_dir`, `output_dir`,
     `checkpoint_dir` from notebook constants BEFORE asserts (post-`0ff50c0`
     injection pattern), then config-contract asserts.
  5. upstream sync cell — fetch the three exact run folders from Drive by
     `*_drive_path_parts` (duplicate match = hard error; reuse nb02 helper).
  6. pre-flight feasibility cell — row counts from `sample_event_index.csv`,
     estimated materialized bytes vs
     `readout.max_materialized_train_bytes`; abort BEFORE any scoring if
     exceeded (protocol §5 clause).
  7. run cell — `result = run_stage(stage03_config)` under `RUN_STAGE03`.
  8. durable save cell — immediately after; validate the seven required
     outputs, refuse upload unless
     `manifest.official_validation_for_selection is False` and
     `holdout_test_contact is False`, Drive API upload +
     `drive_backup_manifest.json` (copy nb02 cell 13 contract).
  9. readout display cell — compact tables from
     `03_seed_summary.csv`/`03_decision_record.json`; wording-safe headings.
  10. markdown — honest interpretation template with allowed-wording
      reminders and the legacy-provenance sentence.
- [ ] **Step 11.2 Static gate** (pattern:
  `tests/notebooks/test_stage02_notebook_static.py`): parses; code cells
  AST-parse; outputs empty; `RUN_STAGE03 = False` enforced; pinned commit
  matches expected constant; exact upstream run-id strings present; durable
  save cell present with manifest-flag refusals; injection lines present;
  forbidden patterns absent — active holdout/test reads,
  `closed_holdout_test` data access, `2017-01-25` outside the frozen
  boundary echo, and selection-on-validation strings
  (`select`/`rank`/`tune` adjacent to `official_validation` — implement as
  the same regex style the stage02 gate uses for its forbidden list).
- [ ] **Step 11.3 Commit point:** `feat(stage03): colab notebook + static gate`.

## Task 12: Pin sequence (publish)

- [ ] **Step 12.1** After user authorizes commits/push: create the
  full-bundle commit (protocol+config+src+tests+notebook+generator), then
  the final notebook commit pinning `PROJECT_REPO_COMMIT` to that
  full-bundle commit (AGENTS.md §5 two-step pin). Verify with
  `git ls-tree -r <pin> --name-only` that the pinned tree contains
  `docs/protocols/03_*`, `configs/stages/03_*`, `src/lst_models/stages/frozen_validation_readout.py`,
  `notebooks/03_*`, and the three test files.
- [ ] **Step 12.2** Update `tests/notebooks/test_stage03_notebook_static.py`
  expected-pin constant in the same commit.

## Task 13: Roadmap bookkeeping

- [ ] **Step 13.1** Check off roadmap Phase 3 items B1-B10 with the commit
  hashes; record the fill-in of `<NEW_STAGE02_RUN_ID>` (and xfail removal)
  when Phase 0.3 delivers the superseding run id.
- [ ] **Step 13.2** Confirm Phase 4 pre-flight list is satisfied before the
  user runs nb03 once.

---

## Self-Review Notes

- Spec coverage: roadmap B1-B10 → T1 (B1-B7 protocol text), T4/T5 (frozen
  parameters + executable reminders), T6 (B2 gates), T7 (B3/D1), T8 (B5/B6
  criteria+fallback), T9 (B7/B8 artifacts incl. the load-bearing
  `03_validation_predictions.csv`), T11 (B9/B10 notebook discipline), T2
  (D3/D4 pre-registration). Pending-input handling: `<NEW_STAGE02_RUN_ID>`
  is a declared external input with an xfail tripwire, not a placeholder.
- Reused symbols verified against current source during the 2026-06-09
  audit: `stage01._load_sample_event_index/_train_valid_events/_load_train_bars/
  _build_feature_frame/_build_window_dataset/_materialize_window_matrix/
  _sample_id_hash/_verify_raw_file_integrity/_ticker_delta_macro_f1/
  _block_delta_macro_f1/_fit_torch_sequence_probe/feature_rebuild_code_sha256`;
  `stage02._score_stage02_baseline/_lightgbm_params/
  _lightgbm_inner_train_early_stopping_split/_trial_probe_config/
  _validate_rebuilt_candidate_counts/_git_commit_fields/PROBE_BY_FAMILY`;
  `metrics.score_classifier/block_bootstrap_macro_f1_delta`;
  `artifacts.require_artifacts/write_json/write_artifact_inventory`.
  Re-verify each against HEAD at execution time (parallel sessions are
  active in this repo).
- Type consistency: outcome dict keys produced by T7 wrappers match the
  T9 column constants; criteria field names match T4 config keys and the T5
  assertions.

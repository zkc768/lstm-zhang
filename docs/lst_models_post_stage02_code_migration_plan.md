# Post-Stage02 Code Migration Plan

> For agentic workers: this is a technical migration plan, not execution
> authorization. Do not edit code from this document unless the user explicitly
> approves implementation in the current thread.

This document is the execution detail for Phases R1 and R2 of
`docs/lst_models_route_a_clean_chain_plan.md` (the Route A master plan). The
user has chosen Route A: rules first, then this refactor, then a full
`00 -> 01 -> 02` chain rerun with the refactored code, then Stage 03 official
validation readout against the new chain only.

Goal: remove stage-to-stage private coupling from the Stage 01/02/03 Python
surface and relocate all provenance-hashed mechanism code into domain modules,
with gated behavior equivalence, before the clean-chain rerun.

Architecture: keep the public notebook API stable:
`lst_models.stages.<stage>.run_stage(config)`. Move reusable domain logic into
small domain modules. The provenance code hash will change as a designed
consequence; it is resolved by the Route A chain rerun, never by a legacy-hash
acceptance bypass.

Tech stack: Python package under `src/lst_models/`, Colab notebooks generated
under `notebooks/`, YAML stage configs, pytest static/contract/smoke tests,
optional codegraph structural audit when `.codegraph/graph.db` is available.

---

## 1. Non-Negotiable Boundary

The legacy chain (Stage 00 `20260609_015034_927813`, Stage 01
`20260609_070204`, Stage 02 `20260610_010019_507648`) has already produced
formal artifacts. Therefore:

- Do not delete, rewrite, or regenerate completed run artifacts, local or
  Drive, results or checkpoints. The legacy chain is superseded, not erased.
- Do not change the meaning of existing `02_stage03_handoff.json`,
  `02_frozen_candidate.json`, `02_hpo_trial_ledger.csv`,
  `02_hpo_plan_ledger.csv`, `run_manifest.json`, or `artifact_inventory.csv`.
- The refactor changes code placement only. Selection rules, search spaces,
  fold design, seeds, configs, thresholds, and decision logic are frozen.
  Behavior equivalence is enforced by golden tests (section 5), not assumed.
- `feature_rebuild_code_sha256` WILL change when the hashed functions move.
  This is expected. The new value becomes authoritative when the chain rerun
  records it in the new Stage 01/02 manifests. Do not implement any
  "accept legacy hash" bypass in Stage 03; Route A forbids it.
- No Stage 03 official validation scoring happens before the new chain is
  complete and frozen. Keep `holdout_test_contact=false`,
  `official_validation_for_selection=false`, and
  `no_final_model_selected=true` semantics intact throughout.

## 2. Execution Order

Phases run strictly in this order. Each phase ends with the fast test suite
green.

```text
Phase G  golden equivalence tests captured from current code   (section 5)
Phase 1  extract domain modules behind transitional wrappers   (section 6)
Phase 2  migrate Stage 01/02/03 callers to public imports      (section 7)
Phase 3  extract model classes                                 (section 8)
Phase 4  remove wrappers, land the static structure gate       (section 9)
Phase 5  equivalence freeze and handoff to the chain rerun     (section 10)
```

Prerequisite: Route A Phase R0 (AGENTS.md structural gates and route guide
rows for `fitting.py`, provenance-hash placement, and inner-fold placement)
must be merged first, because Phase 1 creates `fitting.py` and the guide must
already name it.

## 3. Target Module Map

Verified against the current tree. Two of the six provenance-hashed functions
(`read_raw_txt_file`, `resample_1min_to_5min`) already live in `data.py`; the
migration moves the remaining mechanism code to match.

```text
src/lst_models/features.py        (new)
  build_feature_frame             <- stage01._build_feature_frame
  require_feature_columns         <- stage01._require_feature_columns

src/lst_models/windows.py         (new)
  CandidateDataset                <- stage01.CandidateDataset
  build_window_dataset            <- stage01._build_window_dataset
  materialize_window_matrix       <- stage01._materialize_window_matrix
  fold_indices                    <- stage01._fold_indices
  cap_indices                     <- stage01._cap_indices
  sample_id_hash                  <- stage01._sample_id_hash
  validate_rebuilt_candidate_counts
                                  <- stage02._validate_rebuilt_candidate_counts
                                     (also called by stage03)

src/lst_models/fitting.py         (new; created in Phase 3 together with the
                                   model modules: the fit wrappers construct
                                   the model classes, and a domain module must
                                   never import a stage module to reach them)
  fit_probe                       <- stage01._fit_probe
  fit_logreg_probe                <- stage01._fit_logreg_probe
  fit_lightgbm_probe              <- stage01._fit_lightgbm_probe
  fit_torch_sequence_probe        <- stage01._fit_torch_sequence_probe
  torch_inner_train_early_stopping_split
                                  <- stage01._torch_inner_train_early_stopping_split

src/lst_models/models/standard_dlinear.py   (new)
  StandardDLinearTiny             <- stage01._StandardDLinearTiny
  odd_kernel_within_window        <- stage01._odd_kernel_within_window
  moving_average_same             <- stage01._moving_average_same

src/lst_models/models/tcn.py      (new)
  TCNTiny                         <- stage01._TCNTiny

src/lst_models/models/ms_dlinear_tcn.py     (new)
  MSDLinearTCNTiny                <- stage01._MSDLinearTCNTiny
  (imports moving_average_same from standard_dlinear; models-internal
  imports are allowed)

src/lst_models/data.py            (extend)
  load_train_bars                 <- stage01._load_train_bars
  load_sample_event_index         <- stage01._load_sample_event_index
  load_train_validation_bars      <- stage03._load_train_validation_bars
  load_stage01_summary            <- stage02._load_stage01_summary
                                     (also called by stage03)
  verify_raw_file_integrity       <- stage01._verify_raw_file_integrity
                                     (also called by stage03)
  raw_manifest_integrity_summary  <- stage01._raw_manifest_integrity_summary
                                     (also wrapped by stage02)

src/lst_models/splits.py          (extend)
  FOLD_COLUMNS                    <- stage01.FOLD_COLUMNS
  train_valid_events              <- stage01._train_valid_events
  build_train_inner_folds         <- stage01._build_train_inner_folds
  valid_events_for_split          <- stage03._valid_events_for_split

src/lst_models/metrics.py         (extend; run codegraph semantic_search to
                                   dedupe against existing score_classifier,
                                   block_bootstrap_macro_f1_delta,
                                   compute_metric_lcb before adding)
  classification_metrics          <- stage01._classification_metrics
  score_train_prior_baseline      <- stage01._score_train_prior_baseline
  ticker_delta_macro_f1           <- stage01._ticker_delta_macro_f1
  block_delta_macro_f1            <- stage01._block_delta_macro_f1
  block_bootstrap_lcb             <- stage01._block_bootstrap_lcb

src/lst_models/device.py          (extend)
  detect_torch_runtime            <- stage01._detect_torch_runtime (takes a
                                     forced_import_error parameter so stage01
                                     keeps its monkeypatchable
                                     _TORCH_IMPORT_ERROR flag)
  torch_gpu_name_or_null          <- stage01._torch_gpu_name_or_null
  non_gpu_device_info             <- stage01._non_gpu_device_info
  torch_runtime_device_fields     <- stage02._torch_runtime_device_fields
  note: stage01._device_manifest_fields and stage02._device_manifest_fields
  are NOT merged. They aggregate different ledgers (probe vs trial) with
  different fallback semantics; each stays in its own stage module as
  stage-specific manifest assembly.

src/lst_models/artifacts.py       (extend)
  read_json_object                <- stage01/02/03 _load_json (3 copies)
  hash_file                       re-exported from config.py; the canonical
                                   implementation stays in config.py because
                                   artifacts -> data -> config would cycle if
                                   config had to import artifacts
  git_commit_fields               <- stage02._git_commit_fields
                                     (also called by stage03)
  feature_rebuild_code_sha256     <- stage01.feature_rebuild_code_sha256;
                                     payload imports from data/features/windows
  stage03_readout_code_sha256     <- stage03.stage03_readout_code_sha256;
                                     payload imports from data/splits and
                                     composes feature_rebuild_code_sha256

src/lst_models/config.py          (extend)
  require_mapping                 <- stage01/02/03 _as_mapping (3 copies)
  parse_bool_flag                 <- stage01._is_true (placed here, not in
                                     data.py: splits.py needs it and data.py
                                     imports splits.py, so config.py is the
                                     cycle-free home)
  resolve_repo_path, repo_root    <- stage01/02/03 copies (3 each)
```

Provenance-hash placement after migration (this is the structural payoff):

```text
feature_rebuild_code_sha256 payload =
  data.read_raw_txt_file, data.resample_1min_to_5min, data.load_train_bars,
  features.build_feature_frame, features.require_feature_columns,
  windows.build_window_dataset

stage03_readout_code_sha256 payload =
  data.load_train_validation_bars, splits.valid_events_for_split,
  composed feature_rebuild_code_sha256
```

All payload functions live in domain modules; both builders live in
`artifacts.py`. Future stage-module refactors can no longer move the
scientific hash.

Stays in stage modules (orchestration-owned, not migrated): config
validation, entry gates, ledger row builders, summary/selection logic, frozen
candidate/handoff payload writers, checkpoint writing, `run_stage(config)`.
Stage-02-specific fit wrappers (`_fit_stage02_model`,
`_fit_lightgbm_hpo_trial`) stay in Stage 02 but call `fitting.py` functions;
`_lightgbm_inner_train_early_stopping_split` is a dedupe candidate against
`fitting.torch_inner_train_early_stopping_split` (codegraph check, merge only
if genuinely shared logic).

A `models/registry.py` is NOT created in this migration. Family lookup stays
where it is; the route guide's "What Not To Build" list controls.

## 4. Callers And Tests To Update

```text
src/lst_models/stages/feature_window_search.py
  keep run_stage(config), Stage 01 gates, probe ledger/summary/selection
  replace moved internals with imports from domain modules
  delete the local feature_rebuild_code_sha256 after callers migrate

src/lst_models/stages/model_hpo_train_inner.py
  remove `from lst_models.stages import feature_window_search as stage01`
  import features/windows/fitting/metrics/device/artifacts/config publics
  keep run_stage(config), HPO ledgers, selection, frozen payload writers

src/lst_models/stages/frozen_validation_readout.py
  remove stage01/stage02 imports
  import domain publics; entry gates compare against
  artifacts.feature_rebuild_code_sha256()
  keep run_stage(config), entry gates, blocked-result writers

tests/stages/test_stage02_run_stage_smoke.py
  currently imports stage01.CandidateDataset, stage01._sample_id_hash,
  stage01._torch_inner_train_early_stopping_split
  -> import from windows.py / fitting.py instead

tests/stages/test_stage03_run_stage_smoke.py
  currently imports stage01._load_sample_event_index,
  stage01._build_feature_frame, stage01._build_window_dataset,
  stage01.feature_rebuild_code_sha256
  -> import from data.py / features.py / windows.py / artifacts.py

tests/stages/test_stage01_metrics_and_torch.py
  move private-helper assertions to public module tests under
  tests/data/ (features, windows) and tests/contracts/ or tests/stages/
  (fitting, models, metrics additions)

tests/contracts/test_module_structure.py   (new, Phase 4)
tests/contracts/test_refactor_equivalence_golden.py   (new, Phase G)
```

Notebook user-facing imports stay stable and need no workflow change:

```python
from lst_models.stages.feature_window_search import run_stage
from lst_models.stages.model_hpo_train_inner import run_stage
from lst_models.stages.frozen_validation_readout import run_stage
```

Notebook repinning happens at handoff (section 10), not per phase.

## 5. Phase G: Golden Equivalence Tests First

Before moving any code, add
`tests/contracts/test_refactor_equivalence_golden.py` that runs the CURRENT
code on small deterministic fixtures and pins outputs as committed constants:

- sha256 of the canonical CSV serialization of `_build_feature_frame` output
  on a fixture bar frame (reuse the smoke-test synthetic fixtures).
- sha256 of the window matrix bytes and metadata CSV from
  `_build_window_dataset` + `_materialize_window_matrix` on that frame.
- `_sample_id_hash` known-value cases.
- `_fold_indices` / `_cap_indices` exact outputs for a fixture fold table.
- `read_raw_txt_file` + `resample_1min_to_5min` fixture output hash (guards
  accidental edits to the two already-migrated payload functions).

Rules:

- Constants are captured from current behavior and committed before Phase 1.
- Every later phase must keep these tests green through the new import paths.
- Never edit a golden constant to make a phase pass. A genuine mechanism
  change is out of scope for this migration and requires explicit user
  approval plus protocol updates.
- These tests stay after the migration as regression guards on the provenance
  payload functions.

## 6. Phase 1: Compatibility Extraction

Create the new domain modules and move behavior with tests, keeping
transitional wrappers in the stage modules so existing callers and tests stay
green between phases:

```python
from lst_models.windows import build_window_dataset

def _build_window_dataset(...):
    return build_window_dataset(...)
```

- Order: features/windows/data/splits first, then metrics/device/artifacts/
  config consolidation. `fitting.py` is deliberately deferred to Phase 3: the
  fit wrappers construct the model classes, and creating `fitting.py` before
  the models move would force a domain module to import a stage module.
- Wrappers are intra-migration scaffolding only. They must all be gone by the
  end of Phase 4; none may survive into the chain-rerun commit.
- While both paths exist, golden tests additionally assert old-vs-new equality
  through the wrapper and the public function.
- `artifacts.feature_rebuild_code_sha256` is created in this phase with the
  domain-module payload, and `stage01.feature_rebuild_code_sha256` becomes a
  direct re-export of it: once the payload functions are wrappers, a "legacy
  payload" no longer exists to preserve. The legacy and new hash values are
  both recorded in the migration notes (section 10).

## 7. Phase 2: Caller Migration

- Stage 02: delete the `stage01` import; switch all ~29 references to domain
  publics. Stage 03: delete `stage01`/`stage02` imports; switch all ~15
  references; entry gate calls `artifacts.feature_rebuild_code_sha256()`.
- Keep `run_stage(config)` import paths, artifact names, and config schemas
  unchanged.
- Move test assertions from stage privates to public modules in the same
  commits as the callers they cover.
- Run codegraph `find_cycles` after each module's caller migration.

## 8. Phase 3: Model Module Extraction

- Move `_StandardDLinearTiny`, `_TCNTiny`, `_MSDLinearTCNTiny` to
  `src/lst_models/models/` as public classes; `fitting.py` imports them.
- Models receive tensors and config values only: no file reads, no YAML, no
  Drive paths, no result writing (route guide rule).
- Do not build a trainer abstraction or callback system around them.

## 9. Phase 4: Remove Wrappers, Land The Structure Gate

Remove all transitional wrappers, then add
`tests/contracts/test_module_structure.py` that statically rejects:

- `from lst_models.stages import <any_stage>` in `src/` production code
  outside the stage's own module
- attribute calls through a stage alias to a private name
  (`<stage_alias>._name`) anywhere in `src/`
- tests importing private helpers from a different stage's module
- `class` definitions for models inside `src/lst_models/stages/*.py`
- `inspect.getsource` provenance payloads referencing functions defined in
  `src/lst_models/stages/*.py`

The gate must pass in the same commit that removes the last wrapper.

## 10. Phase 5: Equivalence Freeze And Handoff

Exit criteria for the migration (gates for Route A Phase R3, the chain rerun):

- Golden equivalence tests green on the final tree.
- Full fast suite green: `tests/data tests/stages tests/notebooks
  tests/contracts`.
- `py_compile` green on all touched modules.
- Structure gate green; `rg "from lst_models.stages import"` over `src/`
  returns only each stage's own-module imports (none cross-stage).
- Codegraph `find_cycles` clean, or `codegraph: unavailable` recorded with
  fallback evidence.
- Migration notes record: legacy hash
  `f8bf1f102925a05960ae39279db203156f5e5802403be76ed7292fc5de74eea0`, the new
  `feature_rebuild_code_sha256`, and the new `stage03_readout_code_sha256`.
- Two-step notebook repin completed: a full-bundle commit (refactored `src/`,
  tests, configs, protocols, notebooks), then `PROJECT_REPO_COMMIT` pinned to
  it and verified with `git ls-tree` to contain required sidecars.

Only after all of the above does the Route A chain rerun start, following
master-plan section 6 (Stage 00 data-identity gate, Stage 01
provenance/data gates, Stage 02 completion gates, supersede records).

Recorded migration notes:

- 2026-06-09 Phase G complete: golden constants captured from pre-migration
  code; 9 tests, deterministic across runs.
- 2026-06-09 Phase 1 complete: domain extraction with alias wrappers in
  stage01/02/03; golden tests and full fast suite green (105 passed);
  codegraph unavailable in this environment, fallback validation used
  (rg + py_compile + targeted pytest).
- 2026-06-09 Phase 2 complete: Stage 02/03 callers and tests switched to
  public domain functions; `_load_stage01_summary` and
  `_validate_rebuilt_candidate_counts` moved to data.py/windows.py (two
  cross-stage edges the original map had missed); stage03 now has zero
  cross-stage imports; stage02 retains exactly one stage01 reference
  (`_fit_probe`) pending Phase 3; golden constants unchanged through the
  public import switch; full fast suite green (105 passed).
- 2026-06-09 Phase 3 complete: model factories moved to
  `models/standard_dlinear.py`, `models/tcn.py`, `models/ms_dlinear_tcn.py`
  (torch imported lazily inside the factories); fit wrappers, `probe_defaults`,
  `ProbeFitResult`, and the early-stopping split moved to `fitting.py`; the
  torch import-failure flag is now `fitting.TORCH_IMPORT_ERROR` and the
  stage01 smoke fixture patches it there; stage02's last stage01 reference
  (`_fit_probe`) switched to `fitting.fit_probe` and the cross-stage import
  removed. `src/` now has ZERO stage-to-stage imports. Stage01 is down to
  1146 lines (from 2082). Golden constants unchanged; full fast suite green
  (105 passed).
- 2026-06-09 Phase 4 complete: all stage01 wrapper aliases removed and
  stage01 internals switched to public names; transitional alias-identity
  test deleted; `tests/contracts/test_module_structure.py` landed (no stage
  imports in src/, no nn.Module / inspect.getsource in stage modules,
  cross-stage private access in tests forbidden by filename mapping, line
  ratchet baselines 133/1004/2084/495); TEMPORARY markers added to the five
  same-stage private tests in stage01/stage02 smoke files. Also finished the
  Phase 2 leftover: the triplicated `_as_mapping`/`_load_json`/
  `_resolve_repo_path`/`_repo_root` local copies in all three stages were
  deleted and callers switched to `config.require_mapping`/
  `artifacts.read_json_object`/`config.resolve_repo_path`. Fixed a latent
  Phase 3 issue masked by the CI skip: the torch behavior test patched
  `fws._moving_average_same`, which no longer affects the relocated model;
  it now patches `models.ms_dlinear_tcn.moving_average_same` and calls
  `fitting.fit_torch_sequence_probe` directly. Hashes unchanged
  (`0bf0752c...`, `9ef91880...`); full fast suite green (108 passed).
  Stage line counts: stage01 2082 -> 1004, stage02 2146 -> 2084,
  stage03 560 -> 495.
- legacy feature_rebuild_code_sha256 (superseded chain):
  `f8bf1f102925a05960ae39279db203156f5e5802403be76ed7292fc5de74eea0`
- post-refactor feature_rebuild_code_sha256:
  `0bf0752ceacee98963f6deb9452e65fd81ca6ab51ae722f7405156a18e69e3ea`
- post-refactor stage03_readout_code_sha256:
  `9ef9188000292a4500460f8db61cb1c86992bc17e7f71368b1e10fef53c62545`
- Both new values must be re-verified at the Phase 5 freeze; they change only
  if payload function sources change after this note.
- 2026-06-09 Phase 5 freeze: hashes re-verified unchanged; extra assurance
  pass ran before freeze: 12/12 moved model/fit units verified verbatim
  against pre-migration git HEAD (modulo declared renames plus one documented
  local-variable rename), and the torch behavior checks (A1 moving-average
  effect, D3 score range) executed live in plain Python on the relocated
  code (the pytest-process torch DLL failure on this machine is recorded by
  the test's own skip reason). A `.gitignore` `models/` rule that silently
  excluded `src/lst_models/models/` was caught by the ls-tree bundle check
  and narrowed to `/models/`. Full-bundle commit:
  `4672f4d27e3e8a009ce95bc5344cadc0aac398e1` (verified to contain src incl.
  models/fitting, configs, protocols, notebooks, tests). Stage 00/01/02
  notebooks, generators, and notebook static gates all pin to it. Superseded
  run `20260610_010019_507648` recorded in stage02/03 configs. Migration
  complete; handoff to Route A Phase R3 (chain rerun).

## 11. Validation Commands

Use the project Python executable:

```powershell
E:\codex_workspace\_envs\py311_shared\python.exe -m py_compile `
  src\lst_models\artifacts.py `
  src\lst_models\config.py `
  src\lst_models\data.py `
  src\lst_models\device.py `
  src\lst_models\features.py `
  src\lst_models\windows.py `
  src\lst_models\fitting.py `
  src\lst_models\metrics.py `
  src\lst_models\splits.py `
  src\lst_models\models\standard_dlinear.py `
  src\lst_models\models\tcn.py `
  src\lst_models\models\ms_dlinear_tcn.py `
  src\lst_models\stages\feature_window_search.py `
  src\lst_models\stages\model_hpo_train_inner.py `
  src\lst_models\stages\frozen_validation_readout.py
```

Targeted tests:

```powershell
E:\codex_workspace\_envs\py311_shared\python.exe -m pytest `
  tests\data `
  tests\contracts `
  tests\stages\test_stage01_run_stage_smoke.py `
  tests\stages\test_stage02_run_stage_smoke.py `
  tests\stages\test_stage03_run_stage_smoke.py `
  tests\notebooks `
  -q -rs
```

Codegraph, when available:

```text
mcp__codegraph.find_cycles
mcp__codegraph.semantic_search (before adding moved helpers, dedupe check)
mcp__codegraph.structure(directory="src/lst_models", depth=4, full=true)
mcp__codegraph.context(name="run_stage", file="model_hpo_train_inner.py")
```

If codegraph reports a missing database, record `codegraph: unavailable` and
use `rg`, direct file reads, `py_compile`, and targeted pytest as fallback.

## 12. Do Not Delete

- Any raw data, run folders, Drive backups, checkpoint archives, or artifact
  inventories, legacy or new.
- Golden equivalence tests (they remain as payload regression guards).
- Stage 02 artifact schema constants, frozen handoff writers, Stage 03
  entry-gate code, notebook generators for Stage 00/01/02.
- Transitional wrappers may be deleted only in Phase 4 with the structure
  gate landing in the same commit.

## 13. Acceptance Criteria

The migration is acceptable only when:

- No `src/` production code imports another stage module; no test imports a
  different stage's private helpers; the structure gate enforces both.
- All provenance-hash payload functions live in domain modules; both hash
  builders live in `artifacts.py`.
- Golden equivalence tests passed at every phase without constant edits.
- Notebook user imports, artifact names, config schemas, and stage protocols
  are unchanged.
- No validation/test/holdout boundary is weakened; selection rules and seeds
  untouched.
- New public modules have focused tests in the locations the route guide
  names.
- Legacy run artifacts remain intact and interpretable; the legacy hash and
  both new hash values are recorded in the migration notes.
- `git status --short` and `git diff --stat` are reported at start and end of
  each phase.

## 14. Implementation Gate

Before writing or changing code for this migration, the implementer MUST read:

- docs/lst_models_code_style_and_route_guide.md
- docs/lst_models_route_a_clean_chain_plan.md
- this migration plan
- the target stage module or test

Before writing code, the implementer MUST record a placement decision:

- target_file_type
- target_path
- guide_sections used
- why_not_notebook, when creating Python helper code
- why_not_utils, when creating Python helper code
- safety_tests

The implementation MUST preserve:

- Colab-first execution and one user-facing notebook per stage
- one run_stage(config) per executable stage
- canonical Python package path: src/lst_models/
- small Python helpers, no framework expansion
- validation-only scope; no holdout/test read, transform, window, score, or
  summary
- train-only preprocessing and dummy-baseline comparison contracts
- run manifest with holdout_test_contact=false
- notebook static-gate compatibility
- the Phase G golden constants without edits

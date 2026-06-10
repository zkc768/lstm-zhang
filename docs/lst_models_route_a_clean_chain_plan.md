# Route A Clean Chain Technical Plan

> For agentic workers: this is the master technical plan for Route A. It is a
> design and sequencing document, not execution authorization. Do not edit code
> from this document unless the user explicitly approves the specific phase in
> the current thread.

Goal: produce the authoritative thesis-grade evidence chain by executing, in
this exact order: harden agent rules, refactor the stage code surface, rerun
the `00 -> 01 -> 02` chain with the refactored code, then run Stage 03 official
validation readout against the new chain only.

Companion execution doc for the refactor phases:
`docs/lst_models_post_stage02_code_migration_plan.md`.

---

## 0. Decision Record

- Decision date: 2026-06-09, decided by the user.
- Project goal tier: formal thesis / paper / clean archive.
- Chosen route: **A** `rules -> refactor -> rerun 00->01->02 -> stage 03`.
- Rejected route B (`stage 03 first on legacy chain, refactor later`):
  rejected because any later provenance rerun would happen after official
  validation results were seen, creating a post-validation selection-bias
  concern that cannot be argued away in a thesis.
- Rejected route C (`refactor + Stage 03 accepts exact legacy hash, no rerun`):
  rejected because it keeps the upstream provenance gaps and adds a
  code-changed-between-selection-and-validation note to the chain. Worst
  explanatory burden for the lowest savings.
- The legacy chain stays on disk and on Drive, marked superseded. It is never
  deleted and never silently reinterpreted.

Legacy chain being superseded:

```text
stage 00: 20260609_015034_927813   (raw manifest lacks per-file bytes/sha256)
stage 01: 20260609_070204          (manifest lacks feature_rebuild_code_sha256
                                    and raw_file_integrity)
stage 02: 20260610_010019_507648   (complete and valid; 192/192 HPO rows,
                                    ready_for_stage03=True)
legacy feature_rebuild_code_sha256:
f8bf1f102925a05960ae39279db203156f5e5802403be76ed7292fc5de74eea0
```

## 1. Binding Facts That Force This Order

These are verified code facts, not preferences:

1. `feature_window_search.feature_rebuild_code_sha256()` is a sha256 over
   `inspect.getsource` of exactly six functions: `read_raw_txt_file` and
   `resample_1min_to_5min` (already in `src/lst_models/data.py`), plus
   `_load_train_bars`, `_build_feature_frame`, `_require_feature_columns`,
   `_build_window_dataset` (defined inside the 2082-line Stage 01 module).
   Any move or reformat of those four functions changes the hash by design.
2. `frozen_validation_readout.stage03_readout_code_sha256()` composes the
   Stage 01 hash into its own payload, so the Stage 03 gate inherits the same
   sensitivity.
3. Stage 02 (`model_hpo_train_inner.py`, 2146 lines) makes ~29 references to
   `stage01.*` private helpers. Stage 03 (`frozen_validation_readout.py`,
   560 lines) makes ~15 references to `stage01.*` / `stage02.*` helpers.
   `tests/stages/test_stage02_run_stage_smoke.py` and
   `tests/stages/test_stage03_run_stage_smoke.py` also import Stage 01 private
   helpers directly.
4. The completed Stage 00/01 runs use the legacy manifest format without raw
   file `bytes`/`sha256` and without `feature_rebuild_code_sha256`. Current
   Stage 00/01 code already writes those fields, so a rerun upgrades provenance
   automatically.

Consequences:

- Refactoring without rerunning would break the Stage 03 hash gate against the
  legacy Stage 02 manifest (route C's problem).
- Rerunning without refactoring would freeze the spaghetti surface into the
  authoritative chain, and the next refactor would break the hash gate again
  (route B's problem, deferred and worse).
- Refactor first, then rerun: the new Stage 02 manifest records the
  post-refactor hash, Stage 03 validates against it, and the hash payload moves
  into domain modules so future stage-level refactors never touch the
  scientific provenance hash again. One rerun buys clean code, clean
  provenance, and a permanently stable hash payload.

## 2. Non-Negotiables For The Whole Route

- All `AGENTS.md` section 6 research safety rules stay in force unchanged.
- Raw data is never modified, moved, or deleted.
- Legacy run folders (local, Drive results, Drive checkpoints) are never
  deleted. They are recorded as superseded in the new chain's manifests and
  configs.
- The refactor changes code placement only. Selection rules, search spaces,
  fold design, seeds, configs, thresholds, and stage decision logic are frozen
  and must not change. Behavior equivalence is gated, not assumed (Phase R2).
- Stage 03 official validation scoring runs only against the new chain. No
  Stage 03 scoring, preview, or partial readout against the legacy chain at any
  point. This window is what makes the rerun bias-free; do not waste it.
- The new chain's frozen candidates are authoritative even if they differ from
  the legacy chain's. No old-vs-new comparison may be used to pick, tune, or
  veto a selection. Comparison is allowed only as a recorded reproducibility
  observation after the new chain is frozen.

## 3. Phase R0: Rules First

Update agent rules before any code movement so the refactor itself is governed
by the new gates. Files to change: `AGENTS.md`,
`docs/lst_models_code_style_and_route_guide.md`.

### 3.1 AGENTS.md: add an `Anti-Spaghetti Structural Gates` section

Draft rule text (final wording may be edited during R0 implementation, intent
must not weaken):

```text
## Anti-Spaghetti Structural Gates

These gates are mandatory for all Python changes.

- Stage modules under `src/lst_models/stages/` are orchestration files. They
  own `run_stage(config)`, stage-specific gates, ledgers, selection logic, and
  artifact payload writers. They are not reusable libraries.
- Production code must not import one stage module from another. Forbidden in
  any `src/` file: `from lst_models.stages import <other_stage>`. Downstream
  stages consume upstream run artifacts (manifests, CSVs, JSON) and public
  domain modules, never upstream stage code.
- Any function whose source participates in a provenance code hash (for
  example the `feature_rebuild_code_sha256` payload) must live in a domain
  module such as `data.py`, `features.py`, `windows.py`, or `splits.py`,
  never in a stage module. Provenance hash builders themselves live in
  `artifacts.py`. Rationale: the scientific mechanism hash must be independent
  of stage orchestration refactors.
- A helper needed by two stages moves to the domain module named by the route
  guide before the second stage uses it.
- Long-term tests assert on public domain functions or `run_stage(config)`.
  No test may import a private helper from a different stage's module. A
  same-stage private-helper test is allowed only with an explicit temporary
  marker and a removal target.
- Size ratchet: a new stage module stays under 700 lines and a new
  `run_stage(config)` body under 90 lines. Existing stage modules must not
  grow beyond their recorded post-migration baselines; approved stage-scoped
  features may add lines only with a recorded reason in the task report.
- `tests/contracts/test_module_structure.py` is the enforcing static gate.
  A structural violation is `non_compliant_pending_fix`, not a style note.
```

### 3.2 Route guide updates

- `Where Code Goes` table: add a row for `src/lst_models/fitting.py` -
  shared probe/trial model-fit wrappers (logreg, LightGBM, torch sequence fit
  and early-stopping split) as plain functions. Explicitly exclude trainer
  frameworks, callback systems, and registries.
- `Code File Types And Common Function Placement` table: add rows for fit
  wrappers (`fitting.py`), provenance code-hash builders (`artifacts.py`),
  and inner-fold construction (`splits.py`).
- `Anti-placement examples`: add `stage module imported as a helper library by
  another stage` and `provenance-hashed function defined inside a stage
  module`.
- `Minimum Tests For GitHub` table: add the static module-structure gate.

### 3.3 R0 acceptance

- Both docs updated and internally consistent with this plan and the migration
  plan.
- No code changed in R0.

## 4. Phase R1: Refactor

Execution detail lives in `docs/lst_models_post_stage02_code_migration_plan.md`
(sections 3 to 10). Summary of the target shape:

```text
src/lst_models/features.py      build_feature_frame, require_feature_columns
src/lst_models/windows.py       CandidateDataset, build_window_dataset,
                                materialize_window_matrix, fold_indices,
                                cap_indices, sample_id_hash
src/lst_models/fitting.py       fit_probe, fit_logreg_probe,
                                fit_lightgbm_probe, fit_torch_sequence_probe,
                                torch_inner_train_early_stopping_split
src/lst_models/models/          standard_dlinear.py, tcn.py, ms_dlinear_tcn.py
src/lst_models/data.py          + load_train_bars, load_sample_event_index,
                                load_train_validation_bars, parse_bool_flag
src/lst_models/splits.py        + train_valid_events, build_train_inner_folds,
                                valid_events_for_split
src/lst_models/metrics.py       + ticker/block delta helpers, train-prior
                                baseline, bootstrap LCB (dedupe with existing)
src/lst_models/device.py        + torch runtime detection, gpu name, manifest
                                field consolidation (dedupe with existing)
src/lst_models/artifacts.py     + read_json_object, canonical hash_file,
                                feature_rebuild_code_sha256,
                                stage03_readout_code_sha256
src/lst_models/config.py        + require_mapping, resolve_repo_path
```

Stage modules keep: config validation, entry gates, ledger/summary/selection
logic, frozen payload writers, checkpointing, and `run_stage(config)`.

Placement decision for the refactor (per `AGENTS.md` section 2):

```text
placement_decision:
  target_file_type: python_module
  target_path: src/lst_models/{features,windows,fitting}.py,
               src/lst_models/models/{standard_dlinear,tcn,ms_dlinear_tcn}.py,
               extensions to data.py, splits.py, metrics.py, device.py,
               artifacts.py, config.py
  guide_sections: ["Where Code Goes",
                   "Code File Types And Common Function Placement"]
  why_not_notebook: reusable, safety-critical, provenance-hashed logic shared
                    by three stages; must be testable package code
  why_not_utils: every moved function has a named domain module; no catch-all
                 module is created
  safety_tests: tests/data/, tests/contracts/, tests/stages/,
                tests/contracts/test_module_structure.py,
                tests/contracts/test_refactor_equivalence_golden.py
```

Codegraph is mandatory for R1 (three or more modules, moved helpers, changed
stage entry internals): run `find_cycles` before and after, `semantic_search`
before adding moved helpers to detect duplicates, `context` on touched
functions with callers. If the codegraph database is unavailable, record that
and fall back to `rg`, `py_compile`, and targeted pytest.

## 5. Phase R2: Equivalence Gate (local, before any rerun)

The refactor is acceptable only with verified behavior equivalence:

1. Golden fixture tests are written and committed **before** any code
   movement, capturing current-code outputs as constants: feature-frame
   content hash, window matrix and metadata hashes, `sample_id_hash` known
   values, fold/cap index outputs on fixture data.
2. After each migration phase, the same golden constants must hold via the new
   import paths. While transitional wrappers exist, old-vs-new dual-import
   equality is also asserted.
3. Full fast suite green:
   `tests/data tests/stages tests/notebooks tests/contracts`.
4. `py_compile` passes on every touched module.
5. Structure gate green: no `from lst_models.stages import <other_stage>` in
   `src/` production code; no cross-stage private-helper imports in tests.
6. Record in the migration notes: legacy hash
   `f8bf1f10...74eea0`, the new `feature_rebuild_code_sha256`, and the new
   `stage03_readout_code_sha256`.

Stop condition: any golden mismatch halts the route. Fix the code; never edit
the golden constant to match. If a deliberate behavior fix is ever required,
that is a research-mechanism change and needs explicit user approval plus a
protocol update, not a constant edit.

## 6. Phase R3: Chain Rerun 00 -> 01 -> 02

Preconditions: R0 to R2 complete; notebooks repinned with the two-step
exact-commit flow (full-bundle commit containing refactored `src/`, tests,
configs, protocols, notebooks; then pin `PROJECT_REPO_COMMIT` to it and verify
with `git ls-tree`).

Run order and per-stage gates:

### Stage 00 rerun

- New run id; artifacts to the canonical Drive results path; raw data read
  from the authoritative Drive file IDs only.
- Gate A (provenance upgrade): `raw_data_manifest.json` now records `bytes`
  and `sha256` for every raw file.
- Gate B (data identity): `sample_event_index.csv` sha256 equals the value
  recorded in the legacy run `20260609_015034_927813` artifact inventory, and
  split boundaries are identical. Raw data and label/split code are unchanged,
  so any mismatch means raw-data drift or a code regression: **halt the chain
  and investigate before Stage 01.**

### Stage 01 rerun

- Inputs pinned to the new Stage 00 run id.
- Gate A (provenance upgrade): `run_manifest.json` records
  `feature_rebuild_code_sha256` (new value) and a verified
  `raw_file_integrity` status.
- Gate B (data identity): per-candidate sample counts equal the legacy run
  `20260609_070204`; sample-id hashes equal wherever the legacy ledgers
  recorded them. Probe **metrics** may drift within training nondeterminism
  (torch on GPU); that is recorded, not a failure.
- Gate C (selection honesty): the frozen Stage 01 selection rule runs as-is.
  If the selected candidates differ from the legacy run, record the fact and
  proceed. Do not re-tune or re-seed to chase the legacy selection.

### Stage 02 rerun

- Inputs pinned to the new Stage 01 run id. `superseded_stage02_run_ids`
  includes `20260610_010019_507648`.
- Gates: `completed_hpo_rows == planned_hpo_rows`, `failed_hpo_rows == 0`,
  baselines complete, `ready_for_stage03=True`, manifest
  `stage02_feature_rebuild_code_sha256` equals the new post-refactor hash,
  device provenance fields present.
- The new frozen primary/fallback are authoritative even if they differ from
  the legacy freeze (the legacy candidates were statistically close; a flip is
  a legitimate outcome, not an error).

## 7. Phase R4: Stage 03 Official Validation Readout

- Stage 03 config and protocol point to the new Stage 00/01/02 run ids, with
  the legacy ids listed as superseded.
- Entry gates compare against the new hash values. A legacy-hash acceptance
  path must **not** be implemented; route A makes it unnecessary, and adding
  one would silently reopen route C.
- Only after the new chain is frozen and gates pass does official validation
  scoring run. From that point the standard Stage 03 protocol owns wording and
  stop conditions.

## 8. Risks And Expectation Management

- The new chain may freeze a different primary/fallback than the legacy chain.
  Pre-registered selection rules make this acceptable; the decision record
  above is the commitment device.
- Torch GPU nondeterminism means metric-level drift between legacy and new
  runs is expected. Data-level identity (Gate B at Stages 00/01) is the
  refactor-regression detector; metric drift is not.
- Cost: one full Stage 01 probe sweep plus one full Stage 02 HPO sweep of
  Colab GPU time, same order as the legacy runs, plus the refactor effort.
- Failure isolation: fixture-level golden tests (R2) isolate refactor
  regressions before any GPU money is spent; Stage 00 Gate B isolates
  raw-data drift from code regressions.

## 9. Route Acceptance Criteria

Route A is complete only when all of these hold:

- AGENTS.md and the route guide contain the structural gates and new file
  rows; the static structure test exists and passes.
- No production stage module imports another stage module; no test imports a
  different stage's private helpers.
- Provenance hash payload functions live in domain modules; hash builders live
  in `artifacts.py`; golden equivalence tests passed throughout.
- New `00 -> 01 -> 02` chain is complete with full provenance fields, gates
  green, legacy run ids recorded as superseded, legacy folders intact.
- Stage 03 ran only against the new chain, with no legacy-hash acceptance code
  in the tree.
- All notebook `PROJECT_REPO_COMMIT` pins point to full-bundle commits.

## 10. Implementation Gate

Before writing or changing code for any phase of this plan, the implementer
MUST read:

- docs/lst_models_code_style_and_route_guide.md
- this plan and docs/lst_models_post_stage02_code_migration_plan.md
- the target stage protocol doc, notebook, module, or test

Before writing code, the implementer MUST record a placement decision:

- target_file_type
- target_path
- guide_sections used
- why_not_notebook, when creating Python helper code
- why_not_utils, when creating Python helper code
- safety_tests

The implementation MUST preserve:

- Colab-first execution and one user-facing notebook per stage
- sidecar docs/configs/tests updated in the same task when required
- one run_stage(config) per executable stage
- canonical Python package path: src/lst_models/
- small Python helpers, no framework expansion
- validation-only scope unless explicitly authorized
- no holdout/test read, transform, window, score, or summary
- train-only preprocessing
- dummy baseline comparison where model metrics are reported
- run manifest with holdout_test_contact=false
- durable Drive result-save cell immediately after successful run_stage(config)
- final artifacts saved to My Drive/lst_models/results/<stage_name>/<run_id>/
- drive_backup_manifest.json written and uploaded with final artifacts
- checkpoint plan for long-running stages under
  My Drive/lst_models/checkpoints/<stage_name>/<run_id>/
- runtime paths computed by a notebook injected into the stage config before
  run_stage(config) and before config contract assertions
- GPU/CUDA device provenance recorded when Torch/LightGBM GPU paths are used
  or resolved
- exact-commit Colab bootstrap verified against a commit that contains
  required sidecars, not only the notebook
- notebook static-gate compatibility

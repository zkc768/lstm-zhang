# lst_models V2 Route Roadmap (Stages 03-06 + Integrity Preconditions)

> **For agentic workers:** This is the route-level roadmap, not a code-level
> implementation plan. Each implementation batch (B1-B5 below) MUST get its own
> detailed plan and pass the AGENTS.md Implementation Gate (placement decision,
> required reading, sidecar bundle) before code is written. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** Take the V2 route from the frozen Stage 00/01/02 state through a
defensible one-shot official-validation readout (03), no-reselection
diagnostics (04), thesis synthesis (05), and the Ian final progress record
(06), without ever contacting closed holdout/test and without reusing official
validation for selection.

**Architecture:** One notebook + one protocol + one config + one
`run_stage(config)` per stage (AGENTS.md §3). Official validation is scored
exactly once per frozen seed/candidate in Stage 03; Stage 04 and later only
read frozen Stage 03 artifacts. All decision rules are frozen in protocol text
BEFORE the readout executes.

**Status date:** 2026-06-09 (post-`0ff50c0`; Stage 02 Drive provenance check
completed; this roadmap records the follow-up route after `836f2c6`/`4d2aeeb`/
`0ff50c0` absorbed the prior dirty working tree and the first Batch A fixes).

```text
placement_decision:
  target_file_type: protocol  # route-level planning document
  target_path: docs/lst_models_v2_route_roadmap.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; planning document, no executable logic
  why_not_utils: not applicable; planning document
  safety_tests: not applicable for the roadmap itself; per-batch safety tests
    are defined inside each batch below
```

---

## 0. Current State Snapshot (evidence basis for this roadmap)

Frozen pipeline instances:

| Stage | Run id | Produced at pin | Known state |
|---|---|---|---|
| 00 | `20260609_015034_927813` | `55c8cac` | Valid. Manifest lacks raw-file `bytes`/`sha256` (fields introduced later in `63b646c`); downstream raw-hash gates therefore self-disable ("legacy provenance"). |
| 01 | `20260609_070204` | `2e675cc` | Valid. Manifest lacks `feature_rebuild_code_sha256`; Stage 02's rebuild-hash gate no-ops. Feature functions verified unchanged between pin and HEAD by code diff; Stage 02 row-count parity passed. |
| 02 | `20260609_100637_704705` (supersede before Stage 03) | `63b646c` | Affected. The Drive manifest predates `6182508`, so this run used the defective pre-fix plan-ledger packaging path and must not be frozen as the Stage 03 input. Re-run Stage 02 once at the current pin; do not re-run 00/01. |

Audit verdicts already established (2026-06-09 session):

- No leakage/evaluation-corrupting bug found in the Stage 00-02 code paths.
  The remaining Stage 02 issue is artifact-packaging provenance: the complete
  Drive run predates `6182508` and must be superseded before Stage 03.
- Fast test suite green after Batch A fix-forward: 82 passed / 1 skipped
  (env-gated torch module).
- Known open compliance gaps (fix-forward, no 00/01 rerun): Stage 02 rerun at
  the current pin; remaining Batch A test/doc hardening in A4.1/A4.5/A6; and
  Stage 02 checkpoint durability still needs runner-level Drive mirroring plus
  exact Stage 02 run-id checkpoint path/resume verification. Previously open
  GPU provenance, nb00/nb01 durable-save, and nb01/nb02 runtime-injection gaps
  were fixed in `4d2aeeb`/`0ff50c0`.
- Design facts that Stage 03+ documents must state explicitly: label policy
  `h=9` (45 min), no-trade band `±3.0 bps`; `_cap_indices` equal-allocation
  per `(ticker, label)` subsampling (50k train / 20k eval per fold); Stage 01
  deep probes were 8-epoch no-early-stopping screeners; deep "HPO" is a
  4-profile bounded predeclared grid per family; modeling scope is de facto
  `pooled_five_ticker`.

Route contract (unchanged, AGENTS.md §3):

```text
00_data_split_label_freeze -> 01_feature_window_search ->
02_model_hpo_train_inner -> 03_frozen_validation_readout ->
04_diagnostics_ablation -> 05_thesis_synthesis ->
06_ian_final_progress_record
```

---

## 1. Phase Map

```text
Phase 0  Run-provenance check + housekeeping          (user + agent, hours)
Phase 1  Batch A: compliance & test hardening          (agent, no retraining)
Phase 2  Decision freeze D1-D4                         (user sign-off, no code)
Phase 3  Batch B: Stage 03 bundle + pre-registration   (agent)
Phase 4  Stage 03 one-shot execution                   (user runs Colab once)
Phase 5  Batch C: Stage 04 bundle + execution          (agent + user)
Phase 6  Batch D: Stage 05 thesis synthesis            (agent + user)
Phase 7  Batch E: Stage 06 final progress record       (agent + user)
```

Hard ordering rules:

1. Phase 2 (decision freeze) MUST complete before Phase 4 (readout execution).
   Freezing D3/D4 after seeing Stage 03 numbers is adaptive analysis.
2. Phase 1 test hardening MUST land before Phase 4, because Stage 03 reuses
   the helpers those tests guard (early-stopping tail, same-row hashes).
3. Stage 04 may not begin until `03_decision_record.json` is frozen.
4. No stage ever reads rows at or after `2017-01-25`.

---

## 2. Phase 0 — Run-Provenance Check + Housekeeping

- [x] **0.1 Verify Stage 02 run commit (user, Drive).** DONE 2026-06-09:
  `My Drive/lst_models/results/02_model_hpo_train_inner/20260609_100637_704705/run_manifest.json`
  records
  `git_commit=63b646c0f4a8913f182aa5f8e68eabb27359f67f`, which is an ancestor
  of `61825083d6b3b88103473e19f8f8dc340217f97b`. Verdict: this complete Stage
  02 run is affected by the pre-fix plan-ledger packaging bug and must be
  superseded before Stage 03.
- [x] **0.2 Clean the working tree.** DONE 2026-06-09: commits `836f2c6`
  (AGENTS.md codegraph rules), `4d2aeeb` (stage02 provenance/drive
  contracts), `0ff50c0` (notebook re-pins) absorbed the prior dirty state.
  This roadmap is tracked as a separate follow-up documentation commit.
- [ ] **0.3 Required Stage 02 re-run.** Phase 0.1 failed. Re-run
  `02_model_hpo_train_inner_colab.ipynb` once at the current pin. The new run
  supersedes `20260609_100637_704705` (legitimate: official validation
  untouched). Then update the Stage 02 run id wherever Stage 03 config will
  point, and the hardcoded ids in
  `tests/contracts/test_stage02_config_contract.py:10-11` and
  `tests/notebooks/test_stage02_notebook_static.py:11-12` if upstream ids
  changed. Record the superseded run id in the new run's notes.
- [x] **0.4 Do NOT re-run Stages 00/01.** CONFIRMED. Re-running re-rolls Stage 01
  candidate selection (GPU nondeterminism) — a gratuitous re-selection event.
  The missing provenance fields are handled as documented legacy state
  (Stage 02 manifest already records
  `feature_rebuild_code_match_reason="stage01_manifest_field_missing_legacy_run"`).
  Stage 03/05 documents must carry one sentence: "Stage 00/01 runs predate
  hash-provenance fields; consistency was established by code-diff audit and
  Stage 02 row-count parity."

**Exit gate:** New Stage 02 run id confirmed clean at `6182508` or later;
`git status --short` clean after the roadmap commit.

---

## 3. Phase 1 — Batch A: Compliance & Test Hardening (no retraining)

One implementation task batch. Fix-forward only; the frozen runs keep their
manifests.

**Status note (2026-06-09, post-`0ff50c0`):** Batch A is partly complete at
HEAD. Confirmed landed: A1 GPU-name provenance, A2 durable-save cells/static
gates for nb00/nb01, A3 runtime-path injection for package-backed nb01/nb02,
A4.2 per-key candidate-vs-baseline hash assertions, A4.3 LightGBM
`eval_set` interception, and notebook forbidden-pattern gates. A5 is partial:
the runner writes local incremental checkpoints with resume metadata and the
notebook can upload compact checkpoint archives, but runner-level Drive
mirroring and exact Stage 02 run-id checkpoint organization still need
follow-up.
**Next Batch A task: implement only the remaining gaps below.**

- [x] **A1 `gpu_name_or_null` fix.** DONE in `4d2aeeb`
  (`src/lst_models/stages/model_hpo_train_inner.py` `_device_manifest_fields`
  now resolves the runtime GPU name; CPU-safe test added).
- [x] **A2 Durable-save cells for nb00/nb01.** DONE in `4d2aeeb`/`0ff50c0`.
  Static gates verify immediate post-`run_stage` backup cells,
  `drive_backup_manifest.json`, artifact validation, and duplicate-folder hard
  errors.
- [x] **A3 True runtime-path injection.** DONE for package-backed nb01/nb02 in
  `4d2aeeb`/`0ff50c0`: runtime `RAW_DATA_DIR`,
  `STAGE00_OUTPUT_DIR`/`STAGE01_OUTPUT_DIR`, `OUTPUT_DIR`, and
  `CHECKPOINT_ROOT` are injected into config before contract assertions and
  `run_stage(config)`; static gates pin those lines.
- [ ] **A4 Test hardening (remaining items).**
  1. OPEN — independent fold-overlap test: compute overlap from
     `horizon_end_timestamp` (not the builder's own `event_overlap_count`)
     on a fixture whose label horizon crosses a fold boundary; assert the
     builder rejects or zero-overlaps it. New test in `tests/data/`.
  2. DONE in `4d2aeeb` — per-key candidate-vs-baseline hash assertions
     (verify the old tautological assertion was replaced, not duplicated).
  3. DONE in `4d2aeeb` — eval_set fit-kwargs interception test.
  4. DONE in `4d2aeeb`/`0ff50c0` — notebook static gates include active
     holdout/test/official-validation forbidden-pattern checks for Stage
     00/01/02 notebooks.
  5. OPEN — sampler tests for `_cap_indices`: determinism, per-group
     allocation shape, and the cap < n_groups whole-group-drop edge
     (document intended behavior or fix to proportional floor-1 allocation).
- [ ] **A5 Stage 02 checkpoint durability.** Partially landed in `4d2aeeb`.
  Done: local incremental checkpoint manifest has `status=incomplete`,
  completed/pending units, and resume instructions; notebook-level compact
  checkpoint archives can be uploaded to Drive. Still open: runner-level Drive
  mirror after natural units, checkpoint Drive folders keyed by the Stage 02
  run id (current notebook archive path is still Stage 01-run-id based), and
  exact-run-id resume entry in the runner per AGENTS.md §5. Same contract is
  reused by Stage 03 refits.
- [ ] **A6 LCB docstring nit.** `src/lst_models/metrics.py:140-155`
  `compute_metric_lcb` says "one-sided 95%" but uses the 97.5% quantile.
  Align the docstring (keep the conservative behavior).

**Exit gate:** fast suite green; `codegraph: run` reported for the Python
changes (A1, A4, A5 touch ≥3 modules); no behavior change to frozen-run
evidence.

---

## 4. Phase 2 — Decision Freeze (D1-D4, user sign-off, no code)

These four decisions are written into protocol text in Batch B and MUST be
frozen before the Stage 03 readout executes. Recommended defaults are listed;
"approve defaults" is a sufficient sign-off.

- [ ] **D1 Stage 03 refit recipe — mechanism-frozen (RECOMMENDED).**
  `02_frozen_candidate.json` carries profile params but not per-trial
  `best_iteration`/best-epoch. Recommended: freeze the *mechanism*, not the
  number — refit on the official training partition with the same
  chronological-tail early stopping used in Stage 02
  (`inner_train_chronological_tail`, same fraction/minimum rules, tail carved
  from the full train partition), and record per-refit
  `best_iteration`/`best_epoch` + tail hashes in the readout artifacts.
  Alternative (rejected unless user overrides): fixed epochs/n_estimators
  copied from Stage 02 trials — brittle, because Stage 03's training-row
  regime differs from the 50k-row trial regime.
- [ ] **D2 Stage 03 sample policy — full rows (RECOMMENDED).**
  Refit on ALL eligible official-train rows (no 50k cap); score ALL eligible
  official-validation rows (no 20k cap, natural distribution). Document
  explicitly that Stage 02 absolute metrics (stylized equal-allocation
  subsample; cf. Zadrozny 2004 sample-selection bias) are not comparable to
  Stage 03 absolute metrics; only Stage 03 same-row deltas support claims.
  Fallback if full-train refit is infeasible on Colab (memory/time measured,
  not guessed): the SAME deterministic even-stride policy with a raised cap,
  predeclared in config before execution, never tuned afterward.
- [ ] **D3 Stage 04 ablation scoring path — train-inner only (RECOMMENDED).**
  Architectural controls (`dlinear_only`, `tcn_only`, `last_step_mlp`,
  `last_step_lightgbm_control`) are new fits. Recommended: score them on
  Stage 02's train-inner folds only (consistent with Stage 02 protocol §7
  "tracked architectural controls"), zero new official-validation contact.
  Alternative (requires explicit pre-registration in Batch B, before the
  readout): a bounded one-shot validation-scored ablation budget, every
  fit-predict event counted in the validation ledger. Do not choose this
  after seeing Stage 03 results.
- [ ] **D4 Stage 06 evidence standard — progress record, no test contact
  (RECOMMENDED).** Freeze now, before any validation number is seen:
  - (a) RECOMMENDED: 06 = progress record + reproducibility inventory;
    closed holdout/test (≥ 2017-01-25) stays closed; final claims remain
    validation-only. The honesty section must state that the V1 route
    historically contacted the post-2017 segment, so even a future opening
    yields a "guarded, historically-contacted test", not a clean test.
  - (b) future-blind readout on newly collected post-V2 data — only if such
    data can actually be obtained for the same tickers/bars.
  - (c) external-ticker readout — new tickers, same period, pre-registered.
  Choosing (b)/(c) later as a V2.1 extension is allowed; silently upgrading
  (a) into a test claim is not.

**Exit gate:** user reply recording D1-D4 choices (defaults acceptable).

---

## 5. Phase 3 — Batch B: Stage 03 Bundle + Pre-Registration

One implementation task producing the full sidecar bundle (route guide §7).
Files:

```text
docs/protocols/03_frozen_validation_readout_protocol.md
configs/stages/03_frozen_validation_readout.yaml
src/lst_models/stages/frozen_validation_readout.py     (run_stage)
notebooks/03_frozen_validation_readout_colab.ipynb
tests/contracts/test_stage03_config_contract.py
tests/stages/test_stage03_run_stage_smoke.py
tests/notebooks/test_stage03_notebook_static.py
docs/protocols/04_diagnostics_ablation_protocol.md     (pre-registration core)
docs/protocols/06_ian_final_progress_record_protocol.md (pre-registration core)
```

The 04/06 protocols are written here at least to the depth needed to freeze
D3/D4 — their full operational detail can be completed in Batches C/E, but
the decision sections must be committed before Phase 4.

Protocol content requirements (each is a named section; all were identified
as gaps in the 2026-06-09 plan review):

- [ ] **B1 Stage boundary + wording rules.** Inherit the Stage 02 canonical
  forbidden list (`final model`, `official validation winner`,
  `holdout winner`, `test winner`, `proved best model`) and extend with
  `generalization proven`, `profitable`, `holdout-ready`,
  `selected by official validation`, `chosen threshold`. Allowed:
  `validation-only evidence`, `official validation readout`,
  `candidate met/did not meet predeclared validation-readout criteria`.
- [ ] **B2 Entry gates (full chain).**
  - Exact Stage 02 run folder by run id; `02_stage03_handoff.json` with
    `ready_for_stage03=true`; exactly one primary AND exactly one fallback
    (Stage 02 source requires both: `model_hpo_train_inner.py:1628-1635`).
  - All Stage 02 active outputs present
    (`02_model_hpo_train_inner_summary.csv`, `02_hpo_plan_ledger.csv`,
    `02_hpo_trial_ledger.csv`, `02_hpo_summary.csv`,
    `02_baseline_control_summary.csv`, `02_frozen_candidate.json`,
    `02_frozen_candidate.md`, `02_best_params_by_family.json`,
    `02_stage03_handoff.json`, `frozen_params/*.yaml`, `run_manifest.json`,
    `artifact_inventory.csv`); plan ledger must NOT be byte-identical to the
    trial ledger; inventory `bytes`/`sha256` verified via
    `require_artifacts` (already implemented in `artifacts.py`).
  - Exact Stage 00 run folder (`split_freeze.json`, `label_policy.json`,
    `baseline_registry.json`, `sample_event_index.csv`,
    `raw_data_manifest.json`, `run_manifest.json`) + raw files by file ID
    with hash verification when hashes exist (legacy-tolerant, recorded).
  - Run-id chain consistency: config stage00/01/02 ids ==
    `source_stage00_run_id`/`source_stage01_run_id` inside the Stage 02
    handoff and frozen candidate.
  - `feature_rebuild_code_sha256` match against the current rebuild code
    (legacy-tolerant for the frozen Stage 01 run, reason recorded).
  - Rebuilt train row counts == Stage 02 row contract (same parity check
    Stage 02 ran against Stage 01).
  - `holdout_test_contact=false` and `official_validation_for_selection=false`
    on every upstream manifest/handoff.
- [ ] **B3 Refit recipe (per D1) + sample policy (per D2).** Including: class
  weights recomputed on the refit rows; tail-split fallback reasons recorded;
  per-seed refits use the frozen seed policy `[101, 202]`.
- [ ] **B4 Validation windowing contract.** First-ever windowing of official
  validation rows: cite Stage 00 §9 verbatim (windows per ticker / per split
  / per trading day — no lookback across the 2013-09-16 boundary, day-start
  warmup rows ineligible); eligible-row contract computed by the same frozen
  builder; `sample_id_hash` recorded for the validation row set; same-row
  baselines (`stratified_dummy_train_prior` with fixed seed list,
  `majority_train_prior`, `constant_up`, `constant_down`) fit on
  official-train labels only and scored on identical rows.
- [ ] **B5 Predeclared readout criteria.** Mirror Stage 02 freeze gates on
  the pooled validation readout, judged on the seed-aggregate (mean over
  seeds; per-seed reported):
  `delta_macro_f1_vs_stratified_dummy_train_prior > 0`,
  `delta_macro_f1_vs_majority_train_prior > 0`,
  `positive_ticker_count >= 3`.
  Outcome semantics: met → proceed to 04/05 with validation-only claims;
  not met → record `did_not_meet_predeclared_criteria`, do NOT activate
  fallback, do NOT retune; the only forward path is honest reporting plus an
  optional pre-registered V2.1 revision upstream.
- [ ] **B6 Fallback rule.** Fallback activates ONLY on predeclared mechanical
  failure BEFORE any official-validation scoring of the primary (artifact
  missing, fit/refit crash, schema/hash mismatch, candidate not
  reconstructable). Weak primary metrics never activate it. Fallback
  activation and scoring events are logged in the decision record.
- [ ] **B7 Metrics.** `macro_f1`, `balanced_accuracy`, `accuracy` (aux),
  `mcc`, `roc_auc` (when defined), per-class precision/recall/F1, support by
  class and ticker, both baseline deltas (`..._vs_stratified_dummy_train_prior`,
  `..._vs_majority_train_prior` — keep Stage 02 column naming), per-ticker
  metrics, seed summary. CI/LCB only if predeclared with its resampling unit
  (trading-day block bootstrap via `metrics.block_bootstrap_macro_f1_delta`).
- [ ] **B8 Required artifacts.**
  ```text
  03_validation_readout.csv          (pooled per candidate × seed + aggregate)
  03_per_ticker_readout.csv
  03_seed_summary.csv
  03_same_row_baselines.csv
  03_validation_predictions.csv      (REQUIRED per-row dump: sample_id, ticker,
                                      target_timestamp, trading_day, y_true,
                                      p_up, y_pred, candidate_id, seed)
  03_decision_record.json            (criteria, outcomes, scoring-event count,
                                      fallback status, refit best_iterations)
  run_manifest.json                  (adds official_validation_contact=true,
                                      official_validation_scoring_events=<n>,
                                      official_validation_for_selection=false,
                                      holdout_test_contact=false, device
                                      provenance, config/notebook sha256,
                                      exact upstream run ids)
  artifact_inventory.csv
  drive_backup_manifest.json
  optional: 03_failure_rows.csv      (subset view of the prediction dump)
  ```
  The prediction dump is the load-bearing interface to Stage 04 — without it,
  Stage 04 calibration/selective/failure analysis would require re-scoring
  validation (forbidden). It stays out of git (route guide §11), lives in the
  run folder + Drive with sha256 in the inventory.
- [ ] **B9 Execution discipline.** Each frozen seed×candidate scores official
  validation exactly once; no early stopping, threshold selection, loss
  selection, or ranking against official validation; scoring-event ledger in
  the decision record; per-seed/per-candidate checkpoints under
  `My Drive/lst_models/checkpoints/03_frozen_validation_readout/<run_id>/`
  with resume-by-exact-run-id (reuse A5 contract).
- [ ] **B10 Notebook + tests.** nb03 follows nb02's compliant pattern
  (exact-commit two-step pin, true runtime injection per A3, durable save
  cell, heavy cells off, duplicate-Drive hard errors). Static gate forbids
  active holdout/test reads AND any selection-on-validation strings; config
  contract test pins exact upstream run ids; smoke test runs `run_stage`
  against a tiny chronology-safe fixture with a fake frozen candidate and
  asserts: refit tail hashes ∈ train rows only, validation scored once per
  seed, decision record schema, prediction-dump schema, manifest fields.

**Exit gate:** Batch B merged; fast suite green; D1-D4 decisions visible in
committed protocol text; pinned full-bundle commit verified by `git ls-tree`.

---

## 6. Phase 4 — Stage 03 One-Shot Execution

- [ ] **4.1 Pre-flight.** Confirm Phase 0 exit gate (clean Stage 02 run id in
  config), Phase 1/3 merged, suite green at the pinned commit.
- [ ] **4.2 Execute nb03 once** on Colab GPU. Entry gates fail closed on any
  mismatch. Durable save + decision record verified before the session ends.
- [ ] **4.3 Freeze.** Record the Stage 03 run id; update Stage 04 config
  pointers; no second scoring run regardless of outcome. If outcome is
  `did_not_meet_predeclared_criteria`, Stages 04-05 still run (diagnosis and
  honest synthesis are not conditional on success).

**Exit gate:** `03_decision_record.json` frozen; scoring-event count equals
the predeclared plan (seeds × candidates actually scored).

---

## 7. Phase 5 — Batch C: Stage 04 Diagnostics & Ablation (no reselection)

Files: `docs/protocols/04_diagnostics_ablation_protocol.md` (complete it),
`configs/stages/04_diagnostics_ablation.yaml`,
`src/lst_models/stages/diagnostics_ablation.py`,
`notebooks/04_diagnostics_ablation_colab.ipynb`, tests triad.

Scope (route guide §2: "diagnostics, ablations, ECE/AURC, SHAP/permutation,
and robustness checks without reselection"):

- [ ] **C1 Calibration — measure-only.** Reliability bins, Brier score, ECE
  on `03_validation_predictions.csv` (Guo et al. 2017 as the method anchor).
  NO calibrator fitting on official validation; if a calibrated model is ever
  wanted, the calibration set must be carved from the train tail under a new
  pre-registered protocol revision.
- [ ] **C2 Selective / no-trade diagnostics.** Full risk-coverage and AURC
  curves from the frozen prediction dump (Geifman & El-Yaniv 2017; AURC per
  Geifman et al. 2019). Report whole curves; never mark a recommended
  operating point (`chosen threshold` is a forbidden string).
- [ ] **C3 Robustness slices.** Per-ticker, per-seed, per-year/per-regime
  concentration of the pooled delta; flag if the pooled result is carried by
  a single ticker/seed/period.
- [ ] **C4 Ablations per D3.** Train-inner-only fits of `dlinear_only`,
  `tcn_only`, `last_step_mlp`, `last_step_lightgbm_control` against the
  frozen primary's family, same fold/row contracts as Stage 02, same-row
  baselines. Reference implementations available locally:
  `hf_stock_ml_references2/repos/Time-Series-Library` (DLinear
  classification adaptation, `exp/exp_classification.py`),
  `repos/FEDformer/layers/Autoformer_EncDec.py` (`series_decomp_multi`),
  `repos/LTSF-Linear/models/DLinear.py`. Mind the KB warning: odd moving-avg
  kernels only (`_odd_kernel_within_window` already enforces this).
- [ ] **C5 Failure analysis.** Error concentration by ticker, time-of-day,
  trading day, volatility state — from the prediction dump only.
- [ ] **C6 Hard boundary.** Stage 04 cannot change the Stage 03 winner; any
  finding becomes limitation text or a pre-registered V2.1 item. Stage 04
  manifest: `official_validation_contact=read_frozen_artifacts_only`,
  new fit-predict events on validation = 0 (or = the pre-registered D3(b)
  budget if that path was frozen).

**Exit gate:** diagnostics artifacts frozen; zero (or exactly-budgeted)
validation scoring events; suite green.

---

## 8. Phase 6 — Batch D: Stage 05 Thesis Synthesis

Files: `docs/protocols/05_thesis_synthesis_protocol.md`,
`configs/stages/05_thesis_synthesis.yaml`,
`src/lst_models/stages/thesis_synthesis.py` (table/figure packaging only),
`notebooks/05_thesis_synthesis_colab.ipynb`, tests triad.

- [ ] **S5.1 Validation budget ledger (required artifact).** Aggregate every
  official-validation scoring event across the route (Stage 03 events + any
  D3(b) ablation events) into one auditable table. Method anchors: Dwork et
  al. 2015 (reusable holdout / adaptive analysis), Cawley & Talbot 2010
  (already in Stage 00 protocol §16).
- [ ] **S5.2 Claim boundary register.** Validation-only wording; the
  limitation list assembled from known design facts: ±3bps band rationale
  (with `01_train_label_band_diagnostic.csv` as evidence), stylized
  equal-allocation subsampling in screening/HPO (Zadrozny 2004), 8-epoch
  screening probes, bounded 4-profile grids, pooled-only scope, legacy
  provenance fields, V1 historical contact with post-2017 data. See KB
  guardrails in S5.5.
- [ ] **S5.3 Expectation calibration.** Frame absolute performance against
  published direction-classification context (~52-56% accuracy is the
  typical reported ceiling for daily/intraday direction work; see roadmap
  references) — supports honest "weak signal, disciplined comparison"
  positioning rather than performance claims.
- [ ] **S5.4 Tables/figures.** Use `figure-generation` skill; thesis tables
  from frozen artifacts only; no new search, no new scoring.
- [ ] **S5.5 KB wording guardrails.** From the reference index: do not call
  DLinear-classification a "published standard"; do not present drop-neutral
  binary results as full-market deployment performance; do not compare V1
  labels with V2 no-trade labels as the same task.

**Exit gate:** synthesis package complete; every numeric claim traceable to a
frozen artifact path + sha256.

---

## 9. Phase 7 — Batch E: Stage 06 Ian Final Progress Record

Files: complete `docs/protocols/06_ian_final_progress_record_protocol.md`,
`configs/stages/06_ian_final_progress_record.yaml`,
`notebooks/06_ian_final_progress_record_colab.ipynb`, tests triad
(`src/lst_models/stages/ian_final_progress_record.py` only if executable
logic is actually needed).

- [ ] **E1 Per D4 frozen standard.** Default: progress record +
  reproducibility inventory (exact run ids, commits, artifact hashes, Drive
  folder ids for stages 00-05); closed holdout stays closed.
- [ ] **E2 Honesty section.** V1 post-2017 contact history; what a future
  "guarded test" opening would and would not prove; what a clean future-blind
  evaluation would require (new data beyond 2026 collection or external
  tickers, pre-registered as V2.1).
- [ ] **E3 Ian-requirement mapping.** One table: each Ian/Lan requirement →
  where the route answers it (stage, artifact, protocol section) → status.

**Exit gate:** record delivered; route closed or V2.1 pre-registration opened
explicitly.

---

## 10. Risk Register

| Risk | Phase | Protection |
|---|---|---|
| Stage 02 run predates packaging fix | 0 | confirmed for `20260609_100637_704705`; required Stage 02 re-run before any Stage 03 pointer freezes |
| Decision standards chosen after seeing readout | 2/4 | D1-D4 frozen in committed protocol text before nb03 executes |
| Validation budget creep | 4-7 | scoring-event ledger in `03_decision_record.json`, aggregated in Stage 05; Stage 04 default zero new events |
| Refit regime ≠ tuning regime surprises | 3/4 | D2 full-row policy predeclared; Stage 02 vs 03 absolute metrics declared non-comparable |
| Stage 04 needing validation re-scoring | 3 | `03_validation_predictions.csv` is a required Stage 03 artifact |
| Weak tests letting a regression into Stage 03 helpers | 1 | Batch A items A4.1-A4.5 land before Batch B executes |
| Colab loss mid-refit | 3/4 | A5 checkpoint contract reused by Stage 03 after remaining Drive mirror / exact-run resume gap is closed |
| Wording drift in thesis | 6 | stage forbidden-string gates + KB DO-NOT list in S5.5 |
| Stale hardcoded run ids after any re-run | 0/4 | known list (`test_stage01_config_contract.py`, `test_stage02_config_contract.py`, notebook static gates); update in the same task as the config repoint |

## 11. Stage-Skill Routing (from docs/agent_capabilities_and_skill_routing.md §5)

| Phase | Recommended skills |
|---|---|
| Batch A/B implementation | `writing-plans`, `python-expert-best-practices-code-review`, `pytest-testing`, `verification-before-completion`, codegraph audit |
| Stage 03 readout review | `statistical-analysis`, `notebook-code-reviewer`, `ara-rigor-reviewer` |
| Stage 04 diagnostics | `statistical-analysis`, `figure-generation`, `ara-rigor-reviewer` |
| Stage 05 synthesis | `ml-paper-writing`, `academic-paper`, `figure-generation`, `nature-citation` |
| Stage 06 record | `academic-paper-reviewer`, `ara-research-manager`, `verification-before-completion` |

## 12. External Evidence Basis

Local knowledge base (`E:/codex_workspace/projects/hf_stock_ml_references2/`):
curated citation index (`papers/README.md`, with BibTeX) and local repos —
`Time-Series-Library`, `Autoformer`, `FEDformer`, `LTSF-Linear`, `mlfinlab`.
Key anchors used by this roadmap:

- DLinear: Zeng et al. 2023 (AAAI), `repos/LTSF-Linear/models/DLinear.py`;
  TSLib classification adaptation `repos/Time-Series-Library`.
- Multi-scale decomposition: Wu et al. 2021 (Autoformer), Zhou et al. 2022
  (FEDformer `series_decomp_multi`).
- TCN: Bai et al. 2018 (arXiv:1803.01271).
- Purge/embargo + financial CV: López de Prado 2018, ch.7; mlfinlab docs.
- Selective classification / risk-coverage: Geifman & El-Yaniv 2017
  (arXiv:1705.08500); AURC: Geifman et al. 2019 (arXiv:1805.08206).
- Calibration: Guo et al. 2017, "On Calibration of Modern Neural Networks",
  ICML (arXiv:1706.04599).
- Validation reuse discipline: Dwork et al. 2015, "The reusable holdout:
  Preserving validity in adaptive data analysis", Science 349(6248)
  (arXiv:1506.02629); Cawley & Talbot 2010 (JMLR v11).
- Sample-selection bias (subsampling caveat): Zadrozny 2004 (ICML).
- Label band precedents: Xu & Cohen 2018; Ntakaris et al. 2018; triple-barrier
  (López de Prado 2018) — context for defending/limiting the ±3bps band.
- Direction-accuracy expectation context (2025-2026 web survey): published
  daily/intraday direction studies typically report low-to-mid 50s percent
  accuracy against a ~50% naive floor; treat anything materially above that
  as a red flag for leakage rather than a triumph.

## 13. Out of Scope for This Roadmap

- Re-running Stage 00/01 (rejected; see Phase 0.4).
- Changing label policy, band, split boundaries, ticker universe, feature
  universe, or window universe (Stage 00/01 frozen; any change = V2.1
  pre-registration, a new roadmap).
- Stock-aware / per-ticker modeling axis (recorded as deferred; candidate
  V2.1 item).
- Any holdout/test contact (forbidden until D4(b)/(c) pre-registration, if
  ever).

# V2 Seed Addendum Preregistration — Disclosed Post-Hoc Official-Validation Seed Addendum

Date frozen: 2026-07-01 (before any addendum scoring event; zero addendum
results exist as of this freeze).
Status: preregistered, NOT executed; SIGNED OFF 2026-07-01 (author
authorization via working session: run order "M4 -> M1 -> E5 -> E3 -> E4",
Colab GPU execution by the author; the n=2 compute rationale is recorded in
paper/rebuttal_prep.md R2). This document contains no result numbers
and must never acquire any except through the section 13 deviation log and the
run artifacts it points to.

Stage sidecars covered by this preregistration:

```text
docs/protocols/v2_seed_addendum_preregistration_20260701.md   (this document)
configs/stages/v2_seed_addendum_readout.yaml
src/lst_models/stages/v2_seed_addendum_readout.py
notebooks/v2_seed_addendum_readout_colab.ipynb
tests/contracts/test_v2_seed_addendum_config_contract.py
tests/notebooks/test_v2_seed_addendum_notebook_static.py
```

Sections 2 through 9 are frozen: changing any of them after the first addendum
scoring event is forbidden. A change would require a new dated preregistration
revision and a fresh run, recorded as such in section 13.

## 1. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `AGENTS.md` (research safety, route contract, notebook rules)
- `docs/lst_models_code_style_and_route_guide.md`
- `docs/protocols/03_frozen_validation_readout_protocol.md` (the mechanism this
  addendum reuses)
- this preregistration
- the target notebook, config, module, or test

Recorded placement decision for this bundle:

```text
placement_decision:
  target_file_type: protocol + stage_config + python_module + notebook + test
  target_path: the six sidecar paths listed above
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: the per-seed refit/score loop contacts the official
    validation split and must be budget-capped, chronology-guarded, and
    testable; notebooks call a stage, stages call tested domain helpers.
  why_not_utils: every mechanism function already lives in a domain module
    (data/features/windows/splits/fitting/metrics/artifacts/device) and is
    imported, not duplicated; the stage module is orchestration + gates +
    payload writers only.
  safety_tests: tests/contracts/test_v2_seed_addendum_config_contract.py,
    tests/notebooks/test_v2_seed_addendum_notebook_static.py
```

Structure-gate note: `tests/contracts/test_module_structure.py` carries a dated
stage-scoped line budget (1200) for `v2_seed_addendum_readout.py` with the
recorded reason (one-shot official-validation scoring stages carry the
Stage-03-grade gate/ledger/checkpoint surface; the Stage 03 protocol section 10
freezes the output-schema constants with the runner, so the addendum keeps
verbatim copies pinned by an equality test instead of hoisting them).

## 2. Motivation And Provenance

External review of the paper concluded that every venue reviewer will ask
"seeds are cheap, why only 2?". The prepared answer is
`paper/rebuttal_prep.md` entry R2, whose verifiable facts are:

- the seed pair [101, 202] is predeclared in every stage config before any
  scoring (config anchors listed in R2);
- the claims ledger mandates honest n=2 reporting
  (`paper/outline_and_claims.md:195`, ledger §1: "官方验证种子 | n=2 (101, 202) —
  论文必须如实写 n=2");
- the paper already registers the consequence as a limitation
  (`paper/sections/09_limitations_conclusion.tex:24-27`).

Historical reason (author-provided 2026-07-01, recorded in R2): n=2 was fixed
at preregistration, when the train-inner hyperparameter search was designed, to
conserve compute budget. The choice predates any validation readout; the
constraint was compute, not design intent.

R2's registered concession option is therefore the natural cure, and this
preregistration executes it: "Additional seeds could be run as a disclosed
post-hoc addendum: each new scoring contact logged in the validation-budget
ledger ..., reported in a separate addendum domain, and never merged into the
predeclared n=2 readout. This preserves the predeclaration boundary instead of
silently repairing it." The author authorized the disclosed post-hoc seed
addendum on 2026-07-01.

Method anchor: the one-scoring-pass-per-seed rule, the contact ledger, and the
never-merge rule follow the reusable-holdout budget discipline (Dwork et al.
2015) already used by Stage 03 and Stage 05.

## 3. What Stays Canonical (The Untouchables)

1. The predeclared n=2 readout (seeds 101, 202; Stage 03 run
   `20260610_133305_716174`) remains the paper's canonical official-validation
   number under EVERY addendum outcome. Nothing in this addendum reruns,
   rescores, edits, reweights, or averages it.
2. `paper/outline_and_claims.md` canonical rows are not edited by this work.
   Section 12.3 PROPOSES an addendum row for the user to add after the run.
3. `paper/` prose is not edited by this work. Section 12 maps which sentences
   COULD change under which outcomes, for a later revision cycle under
   `docs/protocols/lst_models_paper_revision_workflow.md`.
4. The closed holdout (rows at or after 2017-01-25) is untouched. The runner
   asserts the frozen `split_freeze.json` boundaries and asserts every events /
   bars / feature / window frame stays strictly before
   `closed_holdout_test_start` (post-2017 rows are never read, windowed, or
   scored).
5. The evidence-domain discipline holds: addendum sentences must name their
   domain ("disclosed post-hoc seed addendum") and are never fused with the
   predeclared official-validation, train-inner, or guarded walk-forward
   domains in one claim.

## 4. Deterministic Seed Rule (Declared, Not Ad Hoc)

```text
seed_k = 101 * k
predeclared readout:  k in {1, 2}  -> [101, 202]   (never rerun here)
this addendum:        k in {3..8}  -> [303, 404, 505, 606, 707, 808]
```

The rule is the continuation of the existing 101/202 pattern to the next six
consecutive multipliers. It is declared here before any run; the runner
(`_validate_config`) recomputes `[101 * k for k in range(3, 9)]` and fails
closed if the config list, this rule, or the disjointness from [101, 202] is
violated. Exactly six seeds; no seed may be added, dropped, or swapped after
the first scoring event (a mechanical failure of a seed is reported as a failed
row, not replaced).

## 5. Frozen Spec Identity (What Is Trained And Scored)

The addendum trains and scores ONLY the frozen Stage 02 primary candidate — the
same spec the predeclared Stage 03 readout scored:

| Field | Frozen value | Binding artifact (read at run time) |
|---|---|---|
| candidate_id | `price_volume_time_w20` | `02_stage03_handoff.json` `primary_candidate` (Stage 02 run `20260610_082130_797479`) |
| feature_set | `price_volume_time` | same |
| window_size | `20` | same |
| model_family / probe | `tcn` / `tcn_tiny` | same + `fitting.PROBE_BY_FAMILY` |
| hpo_profile_id | `tcn_p01` | same; `hpo_profile_params` are read from the artifact, never retyped |
| profile reference copy | channels [16,16], kernel 2, dropout 0.0, lr 0.001, wd 0.0001 | `configs/models/tcn/search_space.yaml` (tcn_p01) — reference only; the runtime binding is the handoff artifact |
| feature columns | 10 day-local columns | `01_candidate_inputs.json` entry for `price_volume_time_w20` (Stage 01 run `20260610_075002`) |
| predeclared seeds guard | `[101, 202]` | `02_frozen_candidate.json` `seed_policy.train_inner_seeds` (asserted equal, asserted disjoint from addendum seeds) |

Identity is enforced fail-closed: `_require_frozen_identity` compares the
config's `frozen_primary_identity` block field-for-field against the frozen
`primary_candidate` in `02_stage03_handoff.json` and refuses to run on any
mismatch. Ledger anchor for the primary identity: `paper/outline_and_claims.md`
C2.4 (TCN tcn_tiny, price_volume_time, w20).

## 6. Pipeline Specification (Per Seed; Identical Stage 03 Mechanism)

Upstream chain (identical pins as `configs/stages/03_frozen_validation_readout.yaml`;
byte-equality of the pins is asserted by the config contract test):

```text
stage00_run_id: 20260610_051705_347450   (split freeze, label policy, event index)
stage01_run_id: 20260610_075002          (candidate inputs, row-count parity summary)
stage02_run_id: 20260610_082130_797479   (frozen primary/fallback handoff)
superseded_stage02_run_ids rejected: 20260609_100637_704705, 20260610_010019_507648
```

Entry gates (all fail-closed, reusing `lst_models.artifacts` helpers exactly as
Stage 03 does): artifact presence + sha256 via `require_artifacts`; plan-ledger
vs trial-ledger distinct-hash gate; run-id chain equality; upstream safety
flags (`holdout_test_contact=false` everywhere,
`official_validation_for_selection=false` on the Stage 02 surfaces);
`ready_for_stage03=true` in the handoff; feature-rebuild code-hash gate
(`feature_rebuild_gate_fields` against
`stage02_feature_rebuild_code_sha256`); frozen date-bound equality against
`split_freeze.json` (train 1998-01-02 -> 2013-09-16; validation 2013-09-16 ->
2017-01-25; closed holdout from 2017-01-25).

Per-seed procedure, for each seed in [303, 404, 505, 606, 707, 808], in order:

1. Data rebuild (once, reused across seeds — same domain functions Stage 03
   calls, so a divergent reimplementation cannot occur):
   `load_sample_event_index` -> `valid_events_for_split("train"/"validation")`
   -> `load_train_validation_bars` (raw .txt by Drive file ID, canonical
   1min->5min recipe, integrity check) -> `build_feature_frame` ->
   `build_window_dataset` per split -> `validate_rebuilt_candidate_counts`
   (Stage 01 row-count parity gate) -> `materialize_window_matrix`. Refit rows =
   ALL eligible official-train rows; scoring rows = ALL eligible
   official-validation rows (Stage 03 D2 full-row policy; natural label
   distribution; no caps). Date-bound gates assert every frame stays strictly
   before 2017-01-25.
2. Same-row registry baselines, scored on the identical validation rows with
   per-seed draws (Stage 03 section 6 convention):
   `metrics.score_registry_baseline(baseline_id, y_train, y_eval, seed)` for
   `stratified_dummy_train_prior` (seeded with the trial seed),
   `majority_train_prior`, `constant_up`, `constant_down`. Train-prior
   baselines fit on the refit rows' labels only.
3. Mechanism-frozen refit: `fitting.fit_stage_control(tcn_tiny, profile, ...)`
   — the shared tested wrapper (also used by Stage 04 controls and the
   synthetic positive control) that routes through
   `fitting.probe_trial_config` + `fitting.fit_torch_sequence_probe`. Early
   stopping source is the frozen `inner_train_chronological_tail` (fraction
   0.2, min 128/128 rows, patience 8, max 64 epochs, best-epoch restoration);
   the `probe_training_defaults.torch` block is a byte-equal copy of the Stage
   03 block (itself byte-equal to Stage 02), asserted by the config contract
   test AND at notebook runtime against
   `configs/stages/03_frozen_validation_readout.yaml`. Scored validation rows
   are never used for epoch selection; normalization and class weights are fit
   on the refit fit-subset only (inside the shared fit wrapper). The only
   varying input across seeds is the seed itself.
4. ONE scoring pass on the official-validation rows
   (`score_each_seed_candidate_exactly_once=true`): the scoring event is
   appended to the ledger before any metric arithmetic; metrics via
   `metrics.score_classifier` / `per_class_metrics` /
   `ticker_delta_macro_f1` (deltas vs stratified dummy AND vs majority on the
   same rows; per-ticker deltas; positive-ticker count).
5. Per-seed recovery checkpoint (partial CSVs + ledger state + manifest) to
   `/content/lst_models_checkpoints/v2_seed_addendum_readout/<run_id>/`,
   mirrored to `My Drive/lst_models/checkpoints/v2_seed_addendum_readout/<run_id>/`.

Budget enforcement: hard cap of 6 new official-validation scoring events
(`budget.max_new_official_validation_scoring_events=6`); the runner raises on
any attempt beyond the cap. A crashed run is completed ONLY through the
exact-run-id resume path (exact checkpoint folder, no parent scans, recorded
scoring events never repeated). A failed seed is retried only by resume after
its failed rows are purged; it is never silently rescored within a run.

Failure semantics (predeclared): a seed whose refit fails mechanically is
recorded with its `fit_status` and error and REPORTED as a failed seed; the
remaining seeds still run. There is no fallback candidate in this addendum and
weak metrics are never a failure.

## 7. Predeclared Reporting And Interpretation Rules (Frozen Before Any Run)

1. ALL six seeds are reported regardless of outcome. No seed may be dropped,
   screened, re-run for a "better draw", or excluded from the summary. Failed
   seeds are reported as failed.
2. The predeclared summary is descriptive dispersion only:
   - min / median / max of `delta_macro_f1_vs_stratified_dummy_train_prior`
     across completed addendum seeds (mean/std as context columns);
   - the count of addendum seeds with a positive delta vs the stratified dummy
     (and vs majority as context);
   - per-ticker cross-seed mean deltas (context).
3. There is NO pass/fail criterion, NO gate, NO selection, and NO ranking. The
   addendum characterizes dispersion of the frozen spec; it cannot promote,
   demote, or select anything.
4. Interpretation is limited to descriptive dispersion evidence about
   seed-to-seed variability of the frozen primary on the frozen validation
   split. Explicit honest-outcome commitment: a wide spread, or a spread that
   touches or crosses zero, is reported exactly as observed. That outcome would
   STRENGTHEN the paper's stated n=2 limitation
   (`paper/sections/09_limitations_conclusion.tex:24-27`) and would be written
   into the limitation, not suppressed, minimized, or reframed.
5. The predeclared n=2 readout remains the paper's canonical
   official-validation number under every outcome. The addendum is reported in
   a separate, clearly labelled addendum domain ("disclosed post-hoc seed
   addendum") and is never merged, pooled, or averaged with the n=2 numbers.
6. Red lines apply in full: no "significant / best / superior / outperforms /
   profitable / well-calibrated / clean test / out-of-sample proof / final
   model"; no claim that the addendum "confirms" or "replaces" the predeclared
   readout; descriptive statistics are not significance tests.
7. Wording templates (the only claim shapes the addendum supports):
   - "Under six additional seeds (deterministic rule 101*k, k=3..8), trained
     and scored once each under the frozen Stage 03 mechanism, the delta vs the
     same-row stratified dummy ranges from [min] to [max] pp (median [median]);
     [k] of 6 seeds are positive."
   - "This is a disclosed post-hoc addendum, reported separately from the
     predeclared n=2 readout, which remains the canonical validation number."

## 8. Validation-Budget Accounting (Contact Template)

Every addendum scoring contact is logged twice:

1. In-run: `v2sa_decision_record.json` `scoring_event_ledger` — one entry per
   seed with `candidate_role`, `candidate_id`, `seed`, `n_rows`,
   `contact_type=official_validation_seed_addendum`, `for_selection=false`,
   `timestamp_utc`; `official_validation_scoring_events` must equal the ledger
   length (expected 6; the true count is used and any shortfall disclosed).
2. Route-level: the runner emits `v2sa_budget_ledger_row.csv` — the exact
   appendable row in the `05_validation_budget_ledger.csv` schema
   (`artifacts/05_thesis_synthesis/20260619_090454_562658/`), with the event
   count resolved from the recorded scoring events, never hand-typed:

```csv
stage_name,run_id,evidence_domain,data_segment,contact_type,scoring_events,for_selection,notes
v2_seed_addendum_readout,<RUN_ID>,official_validation,validation_2013_2017,official_validation_seed_addendum,<N_EVENTS(expected 6)>,False,"disclosed post-hoc seed addendum on the frozen primary; scored once per addendum seed; reported separately and never merged into the predeclared n=2 readout (Dwork 2015 reusable-holdout budget)"
```

After the run, the route budget total becomes 2 (predeclared official
validation) + 0 (diagnostics) + 56 (guarded) + 6 (this addendum) = 64 counted
scoring events. Proposed Stage 05 wiring for the NEXT synthesis run (a separate
authorized task; NOT applied now — `configs/stages/05_thesis_synthesis.yaml`
`budget_ledger.stages` gains one entry):

```yaml
    - stage_name: v2_seed_addendum_readout
      run_id_key: v2sa
      evidence_domain: official_validation
      data_segment: validation_2013_2017
      contact_type: official_validation_seed_addendum
      events_source_key: v2sa
      events_field: official_validation_scoring_events
      for_selection: false
      notes: "disclosed post-hoc seed addendum; scored once per addendum seed; reported separately; never merged into the predeclared n=2 readout"
```

## 9. Outputs And Schemas

Written to `/content/lst_models_results/v2_seed_addendum_readout/<run_id>/`,
then backed up (durable-save cell, Drive API, duplicate-refusal) to
`My Drive/lst_models/results/v2_seed_addendum_readout/<run_id>/`:

```text
v2sa_validation_readout.csv       per-seed rows; VERBATIM Stage 03 VALIDATION_READOUT_COLUMNS
v2sa_per_ticker_readout.csv       per-ticker x seed; VERBATIM Stage 03 PER_TICKER_READOUT_COLUMNS
v2sa_same_row_baselines.csv       4 registry baselines x seed; VERBATIM Stage 03 SAME_ROW_BASELINE_COLUMNS
v2sa_validation_predictions.csv   per-row dump; VERBATIM Stage 03 VALIDATION_PREDICTION_COLUMNS
v2sa_seed_dispersion_summary.csv  predeclared min/median/max + positive-seed counts (section 7)
v2sa_budget_ledger_row.csv        section 8 appendable row
v2sa_decision_record.json         seed rule, per-seed outcomes, scoring-event ledger,
                                  merged_into_predeclared_readout=false,
                                  canonical_readout_unchanged=true, no_final_model_selected=true
run_manifest.json                 config/notebook sha256, upstream run ids, seed rule, device
                                  provenance (requested/resolved/cuda/gpu_name/fallback),
                                  python + package versions, run_timestamp_utc, date bounds,
                                  max_scored_target_timestamp, scoring-event count,
                                  official_validation_for_selection=false, holdout_test_contact=false
artifact_inventory.csv            bytes + sha256 per artifact
drive_backup_manifest.json        written and uploaded last by the durable-save cell
```

Schema parity with the Stage 03 originals is pinned by
`tests/contracts/test_v2_seed_addendum_config_contract.py`
(`test_output_schema_constants_pinned_to_stage03`,
`test_budget_ledger_row_schema_matches_stage05_ledger`). Every result row
carries `scope="validation_only"`. The prediction dump exists so later
measure-only analyses (e.g., an activity-tercile re-slice of the addendum
seeds) need zero new scoring contacts.

## 10. Execution Plan (Colab)

- Runtime: Colab GPU (`Runtime > Change runtime type > GPU`). The frozen
  mechanism keeps `device: auto, require_gpu: false` (byte-equality with Stage
  02/03), so a CPU fallback is recorded rather than forbidden — but six
  full-row tcn_tiny refits on CPU are impractical; the notebook prints a loud
  warning when no GPU is visible.
- Wall-clock expectation (qualitative, no measured numbers exist for this
  stage): each addendum seed repeats the SAME work as one executed Stage 03
  primary refit-and-score (same ~737k eligible train rows, same ~151k
  validation rows, same tcn_tiny profile, same early stopping). Six seeds are
  three times the predeclared readout's two-seed refit compute plus a one-time
  data rebuild. On a T4-class GPU expect an afternoon-scale session
  (order of one to a few hours end to end including data download); on an
  A100-class GPU expect substantially less. If a session risks disconnection,
  the per-seed checkpoints plus exact-run resume complete the run without
  repeating any scoring event.
- Checkpoints: per-seed, mirrored to
  `My Drive/lst_models/checkpoints/v2_seed_addendum_readout/<run_id>/` by the
  notebook's background mirror thread (recovery state only, never evidence).
- Lost-runtime disclosure: if a runtime is lost before any checkpoint or
  result file reached Drive, the lost partial run (date, seeds started) must be
  disclosed in section 13 and carried into the budget accounting. Unrecorded
  official-validation contact is a protocol breach to report, not a license to
  silently restart.

## 11. Run Instructions (User)

One-time preparation (agent-side, already done in this bundle; user verifies):

1. Commit and push the full sidecar bundle (the six files in the header plus
   the `tests/contracts/test_module_structure.py` budget entry) to
   `https://github.com/zkc768/lstm-zhang.git`.
2. Set `PROJECT_REPO_COMMIT` in
   `notebooks/v2_seed_addendum_readout_colab.ipynb` to that exact full-bundle
   commit hash (two-step exact-commit pin, route guide section 7), push the
   pin commit, and verify with `git ls-tree` that the pinned commit contains
   all six sidecars. This is the ONLY permitted notebook edit.

Run steps (Colab):

1. Open `notebooks/v2_seed_addendum_readout_colab.ipynb` in Colab
   (github.com -> Open in Colab, or upload the .ipynb).
2. `Runtime > Change runtime type > GPU` (T4 or better; A100 if available).
3. Run the bootstrap cell (cell 1). It clones the repo at the pinned commit,
   verifies the resolved commit, checks all required sidecars, and adds
   `/content/lst_models/src` to `sys.path`. Verify the printed
   `PROJECT_COMMIT`, run ids, and `ADDENDUM_SEEDS: [303, 404, 505, 606, 707, 808]`.
4. Run the config cell. It injects runtime paths into the stage config and
   asserts the full frozen contract (seed rule, identity, byte-equal torch
   defaults vs the Stage 03 config, date bounds, budget cap, output names).
5. Set `RUN_V2SA = True` in the bootstrap cell, then `Runtime > Run all`.
   The upstream cell authenticates Drive once and downloads: the five raw
   `.txt` files by Drive file ID, and the exact Stage 00/01/02 run folders by
   exact path parts. The pre-flight cell checks GPU visibility and the
   materialized-bytes budget BEFORE any scoring.
6. The run cell executes the six seeds in order, printing one progress line
   per seed via checkpoints; the mirror thread copies checkpoints to Drive
   during the run. Do not interrupt between the run cell and the durable-save
   cell.
7. The durable-save cell validates the nine required outputs and the manifest
   safety flags, uploads everything to
   `My Drive/lst_models/results/v2_seed_addendum_readout/<run_id>/`, and
   writes/uploads `drive_backup_manifest.json` last. Record the printed
   `stage_run_id`, `drive_path`, and `drive_folder_id`.
8. Optionally set `RUN_ARTIFACT_DISPLAY = True` and run the display cell to
   view the dispersion summary, per-seed readout, baselines, and the budget
   row.
9. If the session dies mid-run: reopen the notebook, set
   `RESUME_V2SA_RUN_ID = "<the run id from the checkpoint folder>"`, keep
   `RUN_V2SA = True`, and run all. The resume path restores the exact
   checkpoint folder (from Drive if the runtime is fresh), skips every
   recorded scoring event, and completes only the missing seeds.
10. After the run: append the emitted `v2sa_budget_ledger_row.csv` row to the
    route budget accounting, and (separate task, user-authorized) add the
    section 12.3 ledger row and wire section 8's Stage 05 entry before the next
    synthesis run. Log any deviation in section 13.

## 12. Paper-Integration Map (Quotes Verified 2026-07-01; NO Edits Now)

Rule: nothing below is edited by this task. Any post-run edit goes through
`docs/protocols/lst_models_paper_revision_workflow.md` plus the standard gates
(ledger binding, red lines, grep gates). `.tex` line numbers drift — re-verify
against the working tree before use (`paper/rebuttal_prep.md` rule 1).

### 12.1 Sentences that could change, by outcome

- `paper/main.tex:25` — `\newcommand{\numseeds}{2}   % official validation
  seeds (ledger §1)`. UNCHANGED under every outcome: the canonical readout
  stays n=2. The addendum never edits this macro.
- `paper/sections/06_results.tex:7-10` — "... Every number in this section
  comes from that split over $n=\numseeds{}$ seeds, unless a sentence names a
  different evidence domain. Two seeds yield a descriptive spread rather than
  a variance estimate." UNCHANGED as a statement about the canonical readout.
  Possible post-run addition (any outcome): one sentence after line 10 naming
  the separate addendum domain and pointing to the addendum table, e.g. "A
  disclosed post-hoc seed addendum (six further seeds under a declared rule)
  is reported separately in Appendix X and never enters these numbers."
- `paper/sections/06_results.tex:14-17` — "The predeclared TCN primary reaches
  \macrofone{} of $0.5170 \pm 0.0009$ across \numseeds{} seeds ... It exceeds
  the same-row stratified dummy by 1.69\pp{} in the seed mean, with the
  smallest per-seed margin at 1.63\pp{} ...". UNCHANGED under every outcome
  (addendum numbers are never merged into these).
- `paper/sections/06_results.tex:71-72` (Table 2 caption) — "Frozen validation
  split: predeclared TCN primary, seed means over $n=\numseeds{}$ seeds (mean
  $\pm$ std where shown)." UNCHANGED; a possible new addendum table would be a
  separate float with its own "disclosed post-hoc addendum" caption.
- `paper/sections/09_limitations_conclusion.tex:24-27` — "The official
  validation readout rests on \numseeds{} seeds, too few for seed-to-seed
  variance \cite{bouthillier2021accounting,picard2021torch}, and the
  Student-$t$ lower bound shipped with the decision record is provenance, not
  a decision criterion." This is the sentence the addendum speaks to:
  - Outcome A (all six deltas positive; spread comparable to the n=2 spread):
    the sentence stays and may gain a subordinate clause reporting the
    addendum as descriptive dispersion context, e.g. "; a disclosed post-hoc
    six-seed addendum, reported separately, shows a delta range of [min, max]
    pp under the same frozen mechanism". The limitation is NOT deleted — the
    predeclared readout still rests on n=2.
  - Outcome B (wide or zero-touching/negative-touching spread): the sentence
    is strengthened and must carry the finding, e.g. "; a disclosed post-hoc
    six-seed addendum confirms the concern: the delta ranges from [min] to
    [max] pp, including [k] non-positive seeds". Honest reporting of B is a
    predeclared commitment (section 7.4).
  - Outcome C (some seeds fail mechanically): the completed seeds are reported
    with the failure count disclosed; wording follows A or B on the completed
    subset and names the failures.
- `paper/main.tex:54` (abstract) — "... The margin is positive in all five
  tickers; \numseeds{} seeds ...". UNCHANGED under every outcome: the abstract
  reports the predeclared readout only. (If a future revision decides the
  abstract must mention the addendum, that is a new gated decision, not part
  of this map.)
- `paper/rebuttal_prep.md` R2 "Concession option" — after the run, R2's
  hypothetical converts to an executed, artifact-backed answer: cite this
  preregistration, the run folder
  `My Drive/lst_models/results/v2_seed_addendum_readout/<run_id>/`, and the
  budget row. Rebuttal text obeys the same red lines (no "confirms the edge",
  no significance claims).

### 12.2 Sentences that must NOT change because of this addendum

Every canonical number in `paper/sections/06_results.tex` (0.5170 +/- 0.0009,
+1.69pp, +1.63pp min seed, +18.8pp, per-ticker values, 5/5), every guarded
readout number, and every train-inner control number. The addendum has no
authority over any of them.

### 12.3 PROPOSED claims-ledger addendum row (user adds AFTER the run; not now)

To `paper/outline_and_claims.md`, as a NEW clearly-separated section (e.g.
"C2-A. 种子附录 (disclosed post-hoc seed addendum)"), never inside C2:

```text
| ID | 主张 | 数字 (from v2sa_seed_dispersion_summary.csv) | 证据 |
| C2A.1 | [证据域: official_validation_seed_addendum (disclosed post-hoc);
  预登记 docs/protocols/v2_seed_addendum_preregistration_20260701.md] 在声明的
  确定性种子规则 (101*k, k=3..8) 下, 冻结主候选六个附加种子各评分一次;
  delta vs same-row stratified dummy 的 min/median/max = [__/__/__]pp;
  正 delta 种子数 = [_]/6。描述性离散度证据; 不与预登记 n=2 读出合并,
  n=2 读出保持 canonical。 | min/median/max + positive count 待运行后填入 |
  results/v2_seed_addendum_readout/<run_id>/v2sa_seed_dispersion_summary.csv +
  v2sa_decision_record.json |
```

Constraints on the row: numbers come only from the run artifacts; the row must
name the addendum domain; it may not contain comparative or significance
vocabulary; C2.1 and ledger §1 ("n=2 (101, 202) — 论文必须如实写 n=2") are not
modified.

## 13. Deviation Log (Placeholder)

No deviations recorded as of the 2026-07-01 freeze. Any deviation — a config
change after the first scoring event, a lost runtime, a failed seed, a resume,
an aborted run, a schema change — is appended here with a date, the exact
artifact paths, and the reason, BEFORE any addendum result is used anywhere.

```text
| date | deviation | artifacts | reason / disposition |
| 2026-07-01 | Entry-gate repair BEFORE any scoring event: the runner required official_validation_for_selection=false on 01_candidate_inputs.json (labelled[2:] slice), but that Stage 01 train-inner artifact has never carried the flag; the gate failed closed in Colab at _verify_entry_gates with zero scoring events and zero budget consumption. | src/lst_models/stages/v2_seed_addendum_readout.py (check narrowed to the three Stage 02 payloads); tests/contracts/test_v2_seed_addendum_config_contract.py (regression test pinning the frozen-artifact flag layout) | Implementation repair, not a design change: sections 2-9 untouched; the frozen artifacts are the reference. Aborted run consumed no addendum scoring events; rerun proceeds under the repaired gate at the re-pinned commit. |
```

## 14. Sign-Off

- Preregistration frozen: 2026-07-01, before any addendum scoring event.
- Authorization: author-approved disclosed post-hoc seed addendum
  (2026-07-01; recorded in `paper/rebuttal_prep.md` R2).
- Execution: pending (user-run on Colab GPU per section 11).
- This document contains zero result numbers and must stay that way outside
  the section 13 log and the artifact pointers.

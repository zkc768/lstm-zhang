# V2 Embargo Robustness Control Pre-Registration (Train-Domain, One-Day Embargo)

Status: pre-registration SIGNED OFF 2026-07-01 (author authorization via working session: run order "M4 -> M1 -> E5 -> E3 -> E4", Colab GPU execution by the author), dated 2026-07-01. This
document MUST be committed BEFORE any fold is fitted. Once the first fit cell
of `notebooks/v2_embargo_robustness_colab.ipynb` runs, sections 3-7 are
frozen; changing any of them afterwards requires a new dated entry in the
section 10 deviation log (Stage 03 / V2.1 / synthetic-positive-control
precedent). This document contains NO result numbers; every quantity it names
is either a design parameter fixed here or a pointer to a frozen artifact read
at run time.

## 1. Designation & Scope

Fixed designation (mandatory, verbatim, in every artifact header, notebook
title cell, and summary built on this analysis):

```text
train-domain one-day-embargo robustness control (train-inner domain evidence
only; no model selected)
```

What this experiment IS: a preregistered probe of the protocol's no-embargo
fold design. The route substitutes within-day locality for purge and embargo:
labels and windows never cross a trading day, so no target window straddles a
fold cut — but the eval rows of each train-inner fold begin on the trading day
immediately after the train rows end, and cross-day serial dependence across
that boundary stays intact. This experiment runs the SAME train-inner fold
machinery at the frozen label policy (3.0 bps, 9 bars) and reads the same-row
macro-F1 margin over the stratified dummy under two predeclared variants
within one run: the exact Stage 02 fold rows, and a one-trading-day eval-side
embargo. If the margin is materially smaller under the embargo, cross-day
dependence was inflating the no-embargo readout; if roughly unchanged, the
limitation is bounded at the one-day scale — bounded, never removed.

What this experiment is NOT: NOT a purge/embargo redesign of the route, NOT a
new fold policy, NOT market evidence about any model, NOT a selection event,
NOT a validation or holdout readout, and NOT a test of the actual
train/validation boundary (that boundary cannot be probed without touching the
official validation split; this experiment probes the SAME mechanism — day-
block adjacency without embargo — at the three train-inner fold boundaries,
which is the in-domain instrument for the paper's stated limitation). The V2
frozen selection is unchanged regardless of outcome. Its numbers are
train-inner-domain evidence ONLY and are never fused with the official
validation, train-inner control, or guarded walk-forward domains.

**DOMAIN INVARIANT (enforced in code): the entire experiment runs on the
frozen TRAIN segment only, 1998-01-02 (inclusive) through 2013-09-16
(exclusive). ZERO contact with the official validation split (2013-09-16
onward). ZERO contact with post-2017 rows. The code raises `ValueError` on any
timestamp at or after 2013-09-16** (`src/lst_models/synthetic_control.py`:
`assert_train_domain_only`, applied by `stages/embargo_robustness.py` and
`robustness.load_robustness_inputs` to the frozen event index, the raw train
bars, the feature frame, the window metadata, and the fold boundaries;
`require_frozen_train_boundaries` cross-checks the frozen Stage 00
`split_freeze.json` against these literals before any row is touched).

Forbidden strings in every output and summary of this analysis (verbatim):
`solved problem`, `leakage-free proof`, `purge complete`, `final model`,
`clean test`, `profitable`, `statistically significant`. Student-t lower
bounds are DESCRIPTIVE context, never significance tests. No outcome may be
worded as removing the paper's limitation.

## 2. Motivation: The Paper's Own Limitation Sentences

The paper concedes the gap this experiment addresses (quoted verbatim; these
are the exact sentences the section 9 outcome map could change AFTER the
run):

- `paper/sections/03_protocol.tex:52-56`: "Because every window and horizon
  stays inside one trading day, the last train target window and the first
  validation target window cannot straddle the cut or share a row. Within-day
  locality substitutes for purge and embargo here; we apply neither. Cross-day
  serial dependence therefore stays intact, which is a limitation, not a
  solved problem."
- Supporting protocol facts (frozen, not changed by this experiment): the
  train-inner fold policy is `chronological_expanding_day_block_no_overlap`
  (`src/lst_models/splits.py:118`, recorded per fold in every fold manifest);
  `docs/protocols/02_model_hpo_train_inner_protocol.md` section 9 admits
  "rolling, expanding-window, or purged/embargoed time-series folds" — the
  executed choice was the no-purge/no-embargo expanding day block, and no
  embargoed variant has ever been run.

The within-day-locality argument rules out target-window overlap across the
cut; it does not rule out serial dependence between the last train days and
the first eval days (volatility and regime persistence outlive a day). This
experiment measures, inside the train segment already consumed by Stage 01/02
selection, how much of the train-inner margin survives when the eval rows
nearest the boundary are excluded. Zero validation budget is spent.

## 3. Design: Two Variants, One Run, Shared Fits (frozen)

Machinery, identical to the executed Stage 02 path by the same functions:
frozen Stage 00 artifacts (labels at the frozen policy `h09_bps3p0`; nothing
is relabeled) -> `data.load_train_bars` -> `features.build_feature_frame` ->
`splits.train_valid_events` -> `splits.build_train_inner_folds` (3
chronological expanding day-block folds, zero event overlap required) ->
`windows.build_window_dataset` (candidate `price_volume_time_w20`, w=20) ->
the Stage 02 fold-row caps (50000/20000, deterministic even-stride by ticker x
label) -> `fitting.fit_stage_control` with probe `tcn_tiny`, frozen profile
`tcn_p01`, torch defaults identical to
`configs/stages/02_model_hpo_train_inner.yaml` -> frozen seeds [101, 202].

Like-for-like anchor gates (fail-closed): the rebuilt windowed counts must
match the frozen Stage 01 summary
(`windows.validate_rebuilt_candidate_counts`), and the capped fold-row hashes
of the no-embargo variant must equal the recorded hashes in the frozen
executed Stage 02 plan ledger `02_hpo_plan_ledger.csv` of run
`20260610_082130_797479` (`windows.require_recorded_fold_hash_parity`). The
no-embargo variant therefore scores EXACTLY the executed Stage 02 row
contract.

Variants (both inside the same run):

- `no_embargo` — baseline: fold boundaries and capped rows exactly as
  Stage 02 executed them.
- `embargo_1day` — **EXACT PREREGISTERED RULE: drop every capped eval row
  whose `trading_day` equals the fold's first eval trading day, where the
  first eval trading day is the calendar day of the fold's `eval_start`
  (`eval_start` is the earliest eval target timestamp by construction of
  `splits.build_train_inner_folds`). Train rows and fold boundaries are
  untouched. Equivalently: a one-trading-day gap is inserted between each
  fold's `train_end_exclusive` and its first scored eval row.** Implemented as
  the row filter `robustness.embargo_keep_mask` over the already-capped eval
  rows, chosen because it composes with `splits.py` without modifying the
  frozen fold builder and keeps the embargoed rows a strict subset of the
  baseline rows.

Shared fits (the design decision that makes the contrast exact): because the
embargo removes eval rows only, the two variants have IDENTICAL train rows per
(fold, seed). The runner therefore fits tcn_tiny ONCE per (fold, seed) and
scores both variants from the same fitted model's predictions (the embargoed
variant scores the prediction subset on the retained rows). A refit-per-
variant alternative was considered and rejected: with identical training
inputs it could only add GPU fit-level nondeterminism to the variant contrast,
confounding exactly the difference this experiment measures. The trial ledger
records a shared `fit_group_id` on both variant rows, and the manifest records
`fits_shared_across_variants=true`. Budget: 3 folds x 2 seeds = 6 fits
(config cap 8), read out twice each = 12 readout rows (cap 16); in
fit-unit terms, 2 variants x 2 seeds = 4 readout units over the 3 folds.

Which rows drop is documented exactly, not approximately:
`emb_dropped_rows.csv` lists every dropped row (fold_id, first eval trading
day, sample_id, ticker, trading day, target timestamp — drops are
seed-independent because capping is deterministic), and
`emb_fold_manifest.csv` records per fold the capped counts, retained/dropped
counts, and the sample-id hashes of the baseline eval set, the embargoed eval
set, and the shared train set. If the embargo would remove EVERY capped eval
row of a fold (single-day eval fold), the run fails closed rather than
reading an empty variant. If the deterministic cap left no first-day rows in
some fold's capped eval set, that fold's variants coincide and the recorded
`n_embargo_dropped_rows=0` says so honestly.

## 4. Readout And Per-Variant Dummy Handling (frozen)

Per (variant x fold x seed) row: macro-F1, balanced accuracy, MCC, ROC-AUC,
same-row `delta_macro_f1_vs_baseline`, per-ticker deltas and positivity count,
per-(ticker, trading_day) block deltas.

The same-row stratified dummy (`stratified_dummy_train_prior`) is RE-DRAWN per
variant, per fold, per seed: it is fitted on the shared capped inner-train
labels (identical prior across variants) and predicts on THAT variant's eval
rows — the draw length differs between variants, so the draws differ even at
the same seed. All four registry baselines are recomputed per variant on the
identical rows (`emb_baseline_control_summary.csv`); the stratified dummy is
the predeclared primary comparator. "Identical-as-possible eval rows" holds by
construction: the embargoed rows are a strict, documented subset of the
baseline rows.

## 5. Predeclared Reading Rules (frozen BEFORE any run)

Definitions (`robustness.embargo_reading`, emitted mechanically to
`emb_reading_readout.json` so any human deviation would be visible):

- per seed s and variant v, the MARGIN m(v, s) is the mean over the 3 folds of
  the completed same-row `delta_macro_f1_vs_baseline`;
- APPLICABILITY: the shrinkage rule applies to seed s only when
  m(no_embargo, s) > 0. If the no-embargo margin is not positive for a seed,
  the inflation question degenerates for that seed (there is no positive
  train-inner margin to inflate) and the readout is reported descriptively
  with no verdict for that seed;
- MATERIALLY SMALLER (the predeclared descriptive threshold): seed s flags
  when m(embargo_1day, s) < 0.5 x m(no_embargo, s) — more than half the
  baseline margin disappears under the one-day embargo
  (`reading_rules.shrinkage_fraction: 0.5`, frozen here). The retained-margin
  fraction m(embargo)/m(no_embargo) is reported per seed as descriptive
  context;
- SEED AGREEMENT: the rule is evaluated PER SEED and both seeds must agree.

Outcomes (`overall_outcome`):

- `materially_smaller_cross_day_dependence_inflation_reported` — both seeds
  applicable AND both flag: cross-day serial dependence between the last
  train day and the first eval day was inflating the no-embargo train-inner
  readout. Reported honestly as STRENGTHENING the paper's stated limitation;
  the fold design is not changed, and no re-run with other embargo lengths is
  authorized by this document.
- `roughly_unchanged_limitation_bounded_not_removed` — both seeds applicable
  AND neither flags: the train-inner margin is not driven by the first
  post-boundary eval day. The limitation is BOUNDED at the one-day scale, not
  removed: within-day locality remains the main argument, dependence at lags
  beyond one trading day remains untested, and the actual train/validation
  boundary remains unprobed.
- `baseline_margin_not_positive_rule_inapplicable` — any seed's no-embargo
  margin is not strictly positive: reported descriptively with the per-seed
  values; no shrinkage verdict.
- `mixed_across_seeds_inconclusive` — the seeds disagree: reported as
  inconclusive with both seeds' values; no verdict, no re-run to break the
  tie.
- `incomplete_run_fix_and_rerun` — any variant row failed or is missing: no
  scientific reading; fix the engineering fault and rerun under the section
  10 deviation log.

No outcome uses significance language, selects a model, or removes the
limitation (`limitation_removed=false` is written into the readout and the
manifest in every outcome).

## 6. Outputs

```text
/content/lst_models_results/v2_embargo_robustness/<run_id>/
  run_manifest.json                  # train_domain_only=true, holdout_test_contact=false,
                                     # official_validation_contact=false, embargo rule text,
                                     # fits_shared_across_variants=true, limitation_removed=false,
                                     # feature-rebuild hash gate vs Stage 01, raw integrity,
                                     # device provenance, train-domain bounds, reading outcome
  artifact_inventory.csv
  emb_trial_ledger.csv               # 2 variants x 3 folds x 2 seeds = 12 rows, shared fit_group_id
  emb_variant_summary.csv            # per variant x seed margins + seed_mean rows (descriptive)
  emb_fold_manifest.csv              # fold boundaries, first eval day, retained/dropped counts, hashes
  emb_dropped_rows.csv               # EXACTLY which rows drop under the embargo, row by row
  emb_baseline_control_summary.csv   # four registry baselines per variant/fold/seed
  emb_reading_readout.json           # section 5 rules applied mechanically + overall_outcome
```

Durable backup: `My Drive/lst_models/results/v2_embargo_robustness/<run_id>/`
(drive_backup_manifest.json written and uploaded last). Checkpoints per
completed fold under
`My Drive/lst_models/checkpoints/v2_embargo_robustness/<run_id>/`
(local-first; recovery policy is rerun-from-scratch under a fresh run id, with
the checkpoint as audit state).

## 7. Compute Scope

`tcn_tiny` profile `tcn_p01` ONLY — the predeclared primary configuration.
Cost: 6 tiny-TCN fits on capped fold rows (3 folds x 2 seeds, each fit scored
under both variants), 48 trivial baseline scorings, one raw-data rebuild, one
feature-frame build, one window-dataset build. This is a quarter of the
synthetic positive control's fit count and far inside a single Colab GPU
session; the label/feature/window rebuild dominates wall-clock, not the fits.

## 8. Start Gate

The runner fails closed unless all of these hold (enforced in
`stages/embargo_robustness.py` + `robustness.load_robustness_inputs`):

- exact-run-id Stage 00 / Stage 01 / Stage 02 artifacts resolve, with
  `holdout_test_contact=false` in every upstream manifest and the run-id chain
  verified against the config pins;
- `split_freeze.json` matches the preregistered boundaries verbatim
  (1998-01-02 / 2013-09-16 / 2017-01-25), and `label_policy.json` matches the
  frozen policy verbatim (`endpoint_cumulative_return`, 9, 3.0);
- the Stage 01 handoff contains exactly one `price_volume_time_w20` candidate;
- the Stage 01 manifest's `feature_rebuild_code_sha256` matches the current
  rebuild code (same gate as Stage 02/03/04);
- the rebuilt windowed counts match the Stage 01 summary, and every fold's
  capped row hashes match the frozen Stage 02 plan ledger;
- the embargo config declares exactly the section 3 rule (rule id, one
  trading day, shared fits, the two named variants);
- the planned fit and readout counts are within the declared budgets;
- every timestamp guard in section 1 passes.

## 9. Outcome -> Paper Integration Map (NO edits now)

No paper file, and no row of `paper/outline_and_claims.md`, is edited as part
of this preparation. After the run completes and the user signs off, outcomes
map to edits as follows, all numbers quoted only from
`emb_variant_summary.csv` / `emb_reading_readout.json` and entered through the
claims-ledger process first (proposed new ledger rows live in the train-inner
domain, never fused with the other domains).

On `roughly_unchanged_limitation_bounded_not_removed`:

- `paper/sections/03_protocol.tex:52-56` — "Within-day locality substitutes
  for purge and embargo here; we apply neither. Cross-day serial dependence
  therefore stays intact, which is a limitation, not a solved problem." ->
  the sentence STAYS and may gain one bounded clause: a preregistered
  train-inner control that drops each fold's first post-boundary eval day
  left the same-row margin's order of magnitude in place (numbers from the
  run), with the scope caveat in the same sentence (train-inner folds only,
  one-day embargo only, longer-lag dependence and the actual
  train/validation boundary untested). "We apply neither" and "a limitation,
  not a solved problem" are never softened into "solved".

On `materially_smaller_cross_day_dependence_inflation_reported`:

- the same 03 sentences STAY and gain a strictly more damaging clause: the
  train-inner one-day-embargo control shows the no-embargo readout overstates
  the margin (numbers from the run), so cross-day dependence is not merely a
  theoretical residual. If the paper's train-inner control comparisons are
  cited anywhere as supporting stability, those citations must carry the same
  clause. The fold design itself is not retroactively changed.

On `baseline_margin_not_positive_rule_inapplicable` or
`mixed_across_seeds_inconclusive`: the 03 sentences stay unchanged; at most a
neutral clause reports that the control ran and was inconclusive, with the
per-seed values. On `incomplete_run_fix_and_rerun`: no paper change; deviation
log + rerun decision first.

In every outcome the proposed ledger addition is a new train-inner-domain row
(experiment id, run id, per-variant per-seed margins, retained-margin
fractions, outcome string); no existing ledger row is rewritten by this
experiment.

## 10. Deviation Log

(Empty at pre-registration. Every post-freeze change — config edit, embargo
rule change, variant change, rerun, seed change, criteria reinterpretation —
must be recorded here with date, reason, and effect BEFORE results are
interpreted.)

| date | deviation | reason | effect on section 5 rules |
|---|---|---|---|
| — | — | — | — |

## 11. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this pre-registration document
- the target notebook, config, module, or test

Placement decision recorded for this implementation:

```text
placement_decision:
  target_file_type: protocol + stage_config + python_module + test + notebook
  target_path:
    - docs/protocols/v2_embargo_robustness_preregistration_20260701.md
    - configs/stages/v2_embargo_robustness.yaml
    - src/lst_models/robustness.py
    - src/lst_models/stages/embargo_robustness.py
    - notebooks/v2_embargo_robustness_colab.ipynb
    - tests/stages/test_embargo_robustness.py
    - tests/contracts/test_v2_train_domain_robustness_config_contract.py
    - tests/notebooks/test_v2_embargo_robustness_notebook_static.py
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: the embargo row filter, the shared-fit variant readout,
    the train-domain date-bound wiring, and the shrinkage reading rules are
    safety-critical and shared by the stage entry point and the tests; they
    must be provably identical between the test suite and Colab.
  why_not_utils: purpose-specific domain module (robustness.py) mirroring the
    synthetic_control.py precedent; fold construction stays in splits.py
    (unchanged), fits in fitting.py, and the hard date-bound guards in
    synthetic_control.py. The embargo filter is a preregistered experiment
    treatment, not a route-level fold policy, so it lives in the experiment
    domain module rather than splits.py.
  safety_tests: the three test files above
```

The implementation MUST preserve: Colab-first execution; one user-facing
notebook; one `run_stage(config)`; canonical package path `src/lst_models/`;
no stage-to-stage imports; train-domain-only scope; the per-variant same-row
dummy contract of section 4; the shared-fit contract of section 3;
`holdout_test_contact=false` plus `train_domain_only=true` in the manifest;
the durable Drive result-save cell immediately after `run_stage` succeeds;
checkpoint writing per completed fold; runtime paths injected into the config
before `run_stage` and before the config contract assertions; notebook
static-gate compatibility.

---

Provenance: motivation quotes verified against
`paper/sections/03_protocol.tex` on 2026-07-01; fold policy string from
`src/lst_models/splits.py:118`; Stage 02 fold-design admission from
`docs/protocols/02_model_hpo_train_inner_protocol.md` section 9. Upstream
pins: Stage 00 `20260610_051705_347450`, Stage 01 `20260610_075002`, executed
Stage 02 `20260610_082130_797479` (the Stage 03-pinned frozen run). Embargo
concept context: purge/embargo per Lopez de Prado (2018), adapted here as a
forward-chaining one-trading-day eval-side gap. Structural precedents:
`docs/protocols/v2_1_conditional_predictability_preregistration.md` and
`docs/protocols/v2_positive_control_preregistration_20260701.md`. Governance:
`AGENTS.md` (research safety, no fabrication) > claims ledger
`paper/outline_and_claims.md` > red lines (`.claude/CLAUDE.md` §3) > anti-AI
style gates. This document adds no number to the ledger; ledger rows may be
PROPOSED only after the run completes.

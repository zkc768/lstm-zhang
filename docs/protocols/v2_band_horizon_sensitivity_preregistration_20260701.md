# V2 Band/Horizon Sensitivity Scan Pre-Registration (Train-Domain, No Cell Selected)

Status: pre-registration SIGNED OFF 2026-07-01 (author authorization via working session: run order "M4 -> M1 -> E5 -> E3 -> E4", Colab GPU execution by the author), dated 2026-07-01. This
document MUST be committed BEFORE any cell is fitted. Once the first fit cell
of `notebooks/v2_band_horizon_sensitivity_colab.ipynb` runs, sections 3-8 are
frozen; changing any of them afterwards requires a new dated entry in the
section 11 deviation log (Stage 03 / V2.1 / synthetic-positive-control
precedent). This document contains NO result numbers; every quantity it names
is either a design parameter fixed here or a pointer to a frozen artifact read
at run time.

## 1. Designation & Scope

Fixed designation (mandatory, verbatim, in every artifact header, notebook
title cell, and summary built on this analysis):

```text
train-domain band/horizon sensitivity scan (train-inner domain evidence only;
no cell selected)
```

What this experiment IS: a preregistered robustness probe of the frozen label
construction. It rebuilds the train-segment labels at five predeclared
(no_trade_band_bps, horizon_k) cells — a CROSS through the frozen cell, never
a grid — runs the protocol's own train-inner machinery unchanged at each cell,
and asks ONE question: does the frozen cell (3.0 bps, 9 bars) sit on a knife
edge, or is the sign of the same-row macro-F1 delta over the per-cell
stratified dummy stable across the adjacent cells on each axis?

**TUNING GUARD (load-bearing, verbatim in the notebook and every summary):
this scan is NEVER a tuning pass. No cell is preferred, cells are never
ranked, no alternative (band, horizon) is ever recommended, and the frozen
protocol values (3.0 bps, 9 bars) remain frozen regardless of outcome. The
only admissible reading is sign stability versus sign flip, reported
descriptively.** The runner writes `no_cell_preferred=true`,
`no_cell_ranked=true`, and `no_alternative_cell_recommended=true` into the
reading readout and the run manifest, and the config forbids `cell_ranking`
and `cell_selection` as search axes.

What this experiment is NOT: NOT a threshold search, NOT a horizon search, NOT
a label-policy amendment, NOT market evidence about any model, NOT a selection
event, NOT a validation or holdout readout. The V2 frozen selection
(`price_volume_time_w20` / `tcn` / `tcn_p01`) and the frozen Stage 00 label
policy `h09_bps3p0` are unchanged regardless of outcome. Its numbers are
train-inner-domain evidence ONLY and are never fused with the three existing
evidence domains (official validation n=2, train-inner control, guarded
walk-forward); per-cell deltas live at rebuilt label policies and are not
comparable to any frozen-cell headline number.

**DOMAIN INVARIANT (enforced in code): the entire experiment runs on the
frozen TRAIN segment only, 1998-01-02 (inclusive) through 2013-09-16
(exclusive), using the existing train-inner fold machinery. ZERO contact with
the official validation split (2013-09-16 onward). ZERO contact with post-2017
rows. The code raises `ValueError` on any timestamp at or after 2013-09-16**
(`src/lst_models/synthetic_control.py`: `assert_train_domain_only`, applied by
`stages/band_horizon_sensitivity.py` and
`robustness.load_robustness_inputs` to the frozen event index, the raw train
bars, the feature frame, every cell's rebuilt events and window metadata, and
the fold boundaries; `require_frozen_train_boundaries` cross-checks the frozen
Stage 00 `split_freeze.json` against these literals before any row is
touched, and each cell's fold `eval_end_exclusive` is additionally asserted
against the train boundary).

Forbidden strings in every output and summary of this analysis (verbatim):
`best band`, `best horizon`, `optimal band`, `optimal horizon`,
`recommended band`, `recommended horizon`, `tuned threshold`, `final model`,
`clean test`, `profitable`, `statistically significant`. Per-cell Student-t
lower bounds are DESCRIPTIVE context, never significance tests.

## 2. Motivation: The Paper's Own Limitation Sentence

The paper concedes the gap this experiment addresses (quoted verbatim; these
are the exact sentences the section 10 outcome map could change AFTER the
run):

- `paper/sections/09_limitations_conclusion.tex:31-33`: "The remaining
  limitations concern construct and claim scope. The no-trade band ($3.0$ bps)
  and the label horizon (nine bars) are pre-registered and frozen, with no
  threshold or horizon sensitivity scan."
- Supporting protocol facts (frozen, not changed by this experiment):
  `paper/sections/03_protocol.tex:29-33` defines the label as the sign of the
  9-bar forward return outside the band and states "We set \(\theta\) to
  \(3.0\) bps."; the freeze source is
  `configs/stages/00_data_split_label_freeze.yaml` (`label_config_id:
  h09_bps3p0`, `horizon_k: 9`, `no_trade_band_bps: 3.0`) and
  `docs/protocols/00_data_split_label_freeze_protocol.md` sections 6 and 15
  (Stage 01+ "may not search ... horizon_k, no_trade_band_bps").
- The claims ledger registers the limitation as written with "未作新实验" (no
  new experiment run): `paper/outline_and_claims.md`, open-items section 3,
  the "(写作 limitation, 一句话)" row (~lines 338-340).

Because both frozen values were set before any model was scored and never
scanned, the paper cannot currently say whether the reported train-inner
behavior is specific to the exact cell (3.0, 9) or holds in its neighborhood.
This experiment answers that within the train segment already consumed by
Stage 01/02 selection, so it costs zero validation budget and cannot
contaminate any frozen readout.

## 3. Design: The Preregistered Cross (five cells, frozen)

| cell_id | horizon_k (bars) | band (bps) | axis | role |
|---|---:|---:|---|---|
| `h09_bps2p0` | 9 | 2.0 | band | adjacent band, tighter |
| `h09_bps3p0` | 9 | 3.0 | frozen | THE frozen protocol cell |
| `h09_bps4p0` | 9 | 4.0 | band | adjacent band, wider |
| `h06_bps3p0` | 6 | 3.0 | horizon | adjacent horizon, shorter (30 min) |
| `h12_bps3p0` | 12 | 3.0 | horizon | adjacent horizon, longer (60 min) |

A CROSS, not a grid: band varies only at the frozen horizon (9 bars = 45
minutes), horizon varies only at the frozen band (3.0 bps); off-axis cells are
rejected by `robustness.validate_cell_specs`. Five cells including the frozen
one. Adding, removing, or re-running cells after the first fit is a forbidden
search axis (`configs/stages/v2_band_horizon_sensitivity.yaml`
`forbidden.search_axes`).

Per-cell label rebuild (`robustness.rebuild_cell_events`): the frozen Stage 00
label operator `labels.make_direction_labels` (`endpoint_cumulative_return`,
day-local, per-ticker, band rows dropped, the five invalidation flags) is
called with the cell's `(horizon_k, no_trade_band_bps)` — label logic is
IMPORTED, never re-implemented or forked. Everything else is the executed
Stage 02 path by the same functions: frozen Stage 00 artifacts ->
`data.load_train_bars` -> `features.build_feature_frame` (feature set
`price_volume_time`, the frozen Stage 01 candidate `price_volume_time_w20`,
window w=20) -> `splits.build_train_inner_folds` (3 chronological expanding
day-block folds, zero event overlap required, rebuilt from each cell's own
eligible-day universe by the same deterministic rule) ->
`windows.build_window_dataset` -> the Stage 02 fold-row caps
(50000/20000, deterministic even-stride by ticker x label) ->
`fitting.fit_stage_control` with probe `tcn_tiny`, the frozen profile
`tcn_p01`, and torch training defaults identical to
`configs/stages/02_model_hpo_train_inner.yaml` -> frozen seeds [101, 202].

Eligibility is mechanical and disclosed up front: a tighter band (2.0 bps)
keeps MORE rows and a wider band (4.0 bps) FEWER (the band drops near-flat
rows); a longer horizon (12 bars) invalidates MORE end-of-day rows and a
shorter one (6 bars) fewer (labels are day-local). Each cell therefore has its
own eligible-row universe, its own label prior, and its own fold-row caps.
`bhs_cell_eligibility.csv` reports, per cell: eligible-row counts (total, per
ticker, per invalidation reason), windowed-row counts, label prior, trading-day
count, and identity hashes. These counts are reported facts, never quality
scores.

Frozen-cell anchor gates (the rebuild must reproduce the freeze, or nothing is
read): for `h09_bps3p0` ONLY, the runner fails closed unless (a) the rebuilt
eligible events exactly match the frozen Stage 00 `sample_event_index.csv`
train events on row identity AND labels
(`robustness.require_frozen_cell_event_parity`), (b) the rebuilt windowed
counts match the frozen Stage 01 summary
(`windows.validate_rebuilt_candidate_counts`), and (c) the capped fold-row
hashes equal the recorded hashes in the frozen executed Stage 02 plan ledger
`02_hpo_plan_ledger.csv` of run `20260610_082130_797479`
(`windows.require_recorded_fold_hash_parity`). The other four cells rebuild
labels by construction, so no recorded-hash parity exists for them; their fold
boundaries and row hashes are recorded in `bhs_fold_manifest.csv` and the
trial ledger for audit.

## 4. Readout Machinery (identical to the executed Stage 02 path)

- Same frozen upstream inputs, pinned by exact run id: Stage 00
  `20260610_051705_347450`, Stage 01 `20260610_075002`, executed Stage 02
  `20260610_082130_797479` (plan-ledger parity source).
- Same fold design rule, same caps, same frozen seeds [101, 202], same fit
  path, same metrics: macro-F1, balanced accuracy, MCC, ROC-AUC, same-row
  `delta_macro_f1_vs_baseline`, per-ticker deltas and positivity count,
  per-(ticker, trading_day) block deltas, and the fold/seed Student-t LCB
  (`metrics.compute_metric_lcb`) — all descriptive.
- Budget: 5 cells x 3 folds x 2 seeds = 30 tcn_tiny fits (config cap 36),
  plus 120 registry-baseline scorings. Fail-closed before any fit if the plan
  exceeds the cap.

## 5. Per-Cell Dummy Handling (frozen; the load-bearing detail)

The same-row stratified dummy (`stratified_dummy_train_prior`, via
`metrics.score_registry_baseline`) is RE-DRAWN per cell, per fold, per seed:

- it is fitted on THAT cell's capped inner-train labels (each cell has its own
  label prior — the band shifts the up/down mix mechanically);
- it predicts on THAT cell's capped inner-eval rows (each cell has its own
  eligible rows and so its own draw length);
- it is seeded with the trial seed (101 or 202), the Stage 02 convention.

No dummy draw, prior, or floor is ever shared or reused across cells. All four
registry baselines (stratified dummy, majority, constant up, constant down)
are recomputed per cell/fold/seed on the identical rows
(`bhs_baseline_control_summary.csv`); the stratified dummy is the predeclared
primary comparator. Deltas are therefore per-cell same-row quantities; a delta
at one cell is never subtracted from, divided by, or ranked against a delta at
another cell.

## 6. Predeclared Reading Rules (frozen BEFORE any run)

Definitions, per cell, over the 6 fold-by-seed rows (3 folds x 2 seeds):

- `mean_delta` = mean same-row macro-F1 delta versus that cell's stratified
  dummy; `lcb_delta` = Student-t lower bound over the 6 deltas (descriptive);
- the cell's SIGN is the sign of `mean_delta` (`positive` / `negative`; an
  exactly-zero or non-finite mean is `zero`/`undefined` and makes its axis
  sign-unstable); per-row sign counts are reported alongside so within-cell
  sign mixing is visible.

Rules (`robustness.band_horizon_reading`, emitted mechanically to
`bhs_reading_readout.json` so any human deviation would be visible):

- R1 (report everything): all five cells are always reported — no cell is
  dropped for being unfavorable, thin, or inconvenient; eligible-row counts
  per cell are always reported next to the deltas.
- R2 (not a knife edge): the frozen cell is read as "not a knife edge in this
  train-inner scan" when the sign is stable across ALL cells of the band axis
  {2.0, 3.0, 4.0 at h=9} AND all cells of the horizon axis {6, 9, 12 at 3.0}
  (`overall_outcome = not_knife_edge_sign_stable_both_axes`).
- R3 (sign flips strengthen the limitation): any sign flip on either axis is
  reported honestly, per axis and per cell
  (`sign_flip_on_band_axis_limitation_strengthened`,
  `sign_flip_on_horizon_axis_limitation_strengthened`, or
  `sign_flip_on_both_axes_limitation_strengthened`). A flip STRENGTHENS the
  paper's stated limitation — the frozen values sit in a sign-unstable
  neighborhood — and triggers no re-scan, no extra cell, no preference, and no
  protocol change.
- R4 (undefined sign): an exactly-zero or undefined mean at any axis cell
  yields `sign_undefined_on_an_axis_reported_descriptively`; reported as such,
  not resolved by re-running.
- R5 (never a ranking): per-cell deltas are descriptive; cells are NEVER
  ranked and no alternative cell is ever recommended, whatever the pattern.
  The readout carries `no_cell_preferred=true`, `no_cell_ranked=true`,
  `no_alternative_cell_recommended=true`,
  `frozen_protocol_values_unchanged=true` in every outcome.
- R6 (incomplete voids the reading): any cell with failed or missing fit rows
  voids the scientific reading entirely
  (`incomplete_run_fix_and_rerun`); fix the engineering fault and rerun under
  the section 11 deviation log.

## 7. Outputs

```text
/content/lst_models_results/v2_band_horizon_sensitivity/<run_id>/
  run_manifest.json                  # train_domain_only=true, holdout_test_contact=false,
                                     # official_validation_contact=false, no_cell_preferred=true,
                                     # feature-rebuild hash gate vs Stage 01, raw integrity,
                                     # device provenance, train-domain bounds, reading outcome
  artifact_inventory.csv
  bhs_trial_ledger.csv               # per cell x fold x seed, Stage 02 ledger schema + cell columns
  bhs_trials_h09_bps2p0.csv          # per-cell slices of the same ledger (5 files)
  bhs_trials_h09_bps3p0.csv
  bhs_trials_h09_bps4p0.csv
  bhs_trials_h06_bps3p0.csv
  bhs_trials_h12_bps3p0.csv
  bhs_cell_summary.csv               # per-cell mean/LCB delta, sign, dummy floor, row counts
  bhs_cell_eligibility.csv           # per-cell eligibility profile (the mechanical-count table)
  bhs_fold_manifest.csv              # per-cell fold boundaries and overlap counts
  bhs_baseline_control_summary.csv   # four registry baselines per cell/fold/seed
  bhs_reading_readout.json           # section 6 rules applied mechanically + overall_outcome
```

Durable backup: `My Drive/lst_models/results/v2_band_horizon_sensitivity/<run_id>/`
(drive_backup_manifest.json written and uploaded last). Checkpoints per
completed cell under
`My Drive/lst_models/checkpoints/v2_band_horizon_sensitivity/<run_id>/`
(local-first; recovery policy is rerun-from-scratch under a fresh run id, with
the checkpoint as audit state).

## 8. Compute Scope

`tcn_tiny` profile `tcn_p01` ONLY — the predeclared primary configuration.
This experiment measures the label-construction sensitivity of the protocol's
train-inner readout, not a family comparison; one family suffices. Cost: 30
tiny-TCN fits on capped fold rows (5 cells x 2 seeds = 10 fit units, each
spanning the 3 train-inner folds), 120 trivial baseline scorings, one raw-data
rebuild, one feature-frame build, five label rebuilds, and five window-dataset
builds. This is roughly 1.5x the fit count of the executed synthetic positive
control (24 fits) and about a sixth of the executed Stage 02 (192 rows) under
identical caps; a single Colab GPU session is the expected envelope.

## 9. Start Gate

The runner fails closed unless all of these hold (enforced in
`stages/band_horizon_sensitivity.py` + `robustness.load_robustness_inputs`):

- exact-run-id Stage 00 / Stage 01 / Stage 02 artifacts resolve, with
  `holdout_test_contact=false` in every upstream manifest and the run-id chain
  verified against the config pins;
- `split_freeze.json` matches the preregistered boundaries verbatim
  (1998-01-02 / 2013-09-16 / 2017-01-25), and `label_policy.json` matches the
  frozen cell verbatim (`endpoint_cumulative_return`, 9, 3.0);
- the Stage 01 handoff contains exactly one `price_volume_time_w20` candidate;
- the Stage 01 manifest's `feature_rebuild_code_sha256` matches the current
  rebuild code (same gate as Stage 02/03/04);
- the cell list is the exact section 3 cross (canonical ids, one frozen cell,
  no off-axis cell);
- the frozen-cell anchor gates of section 3 pass (event parity, count parity,
  plan-ledger fold-row parity);
- the planned fit count (cells x folds x seeds) is within the declared budget;
- every timestamp guard in section 1 passes.

## 10. Outcome -> Paper Integration Map (NO edits now)

No paper file, and no row of `paper/outline_and_claims.md`, is edited as part
of this preparation. After the run completes and the user signs off, outcomes
map to edits as follows, all numbers quoted only from `bhs_cell_summary.csv` /
`bhs_reading_readout.json` and entered through the claims-ledger process first
(proposed new ledger rows live in the train-inner domain, never fused with the
other domains, and support sensitivity wording only).

On `not_knife_edge_sign_stable_both_axes`:

- `paper/sections/09_limitations_conclusion.tex:31-33` — "The no-trade band
  ($3.0$ bps) and the label horizon (nine bars) are pre-registered and frozen,
  with no threshold or horizon sensitivity scan." -> the trailing clause
  becomes a one-clause completed-scan statement: a preregistered train-inner
  scan of adjacent cells (2.0/4.0 bps at nine bars; six/twelve bars at 3.0
  bps) found the same-row delta sign stable across both axes, with the domain
  caveat (train-inner folds only, tcn_tiny only, eligibility shifts
  mechanically with the band) in the same sentence. The frozen-value statement
  itself never changes.
- `paper/outline_and_claims.md` open item "(写作 limitation, 一句话)"
  (~lines 338-340) — its "未作新实验" note is superseded by a proposed new
  train-inner-domain ledger row citing the run id and the per-cell table.

On any `sign_flip_*` outcome:

- the same 09 sentence STAYS and gains a strictly more cautious clause: the
  train-inner scan found the delta sign unstable at the named adjacent
  cell(s), so conclusions are tied to the exact frozen cell; no softening
  anywhere, no alternative cell named as better, and the diagnostics/regime
  discussion may cite the flip as additional evidence that the readout is
  regime- and construction-sensitive.

On `sign_undefined_on_an_axis_reported_descriptively`: the 09 sentence stays;
at most a neutral clause reports the scan ran and was uninformative at the
stated cell(s). On `incomplete_run_fix_and_rerun`: no paper change; deviation
log + rerun decision first.

In every outcome: `paper/sections/03_protocol.tex` label subsection (the
"We set \(\theta\) to \(3.0\) bps." sentence and the frozen-label framing)
is NOT edited; the protocol remains frozen and this scan never becomes a
tuning narrative.

## 11. Deviation Log

(Empty at pre-registration. Every post-freeze change — config edit, cell
change, rerun, seed change, criteria reinterpretation — must be recorded here
with date, reason, and effect BEFORE results are interpreted.)

| date | deviation | reason | effect on section 6 rules |
|---|---|---|---|
| — | — | — | — |

## 12. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this pre-registration document
- the target notebook, config, module, or test

Placement decision recorded for this implementation:

```text
placement_decision:
  target_file_type: protocol + stage_config + python_module + test + notebook
  target_path:
    - docs/protocols/v2_band_horizon_sensitivity_preregistration_20260701.md
    - configs/stages/v2_band_horizon_sensitivity.yaml
    - src/lst_models/robustness.py
    - src/lst_models/stages/band_horizon_sensitivity.py
    - notebooks/v2_band_horizon_sensitivity_colab.ipynb
    - tests/stages/test_band_horizon_sensitivity.py
    - tests/contracts/test_v2_train_domain_robustness_config_contract.py
    - tests/notebooks/test_v2_band_horizon_sensitivity_notebook_static.py
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: the per-cell label-rebuild adapter, the frozen-cell parity
    gate, the train-domain date-bound wiring, and the sign-stability reading
    rules are safety-critical and shared by the stage entry point and the
    tests; they must be provably identical between the test suite and Colab.
  why_not_utils: purpose-specific domain module (robustness.py) mirroring the
    synthetic_control.py precedent; label logic is imported from labels.py
    (never forked), folds from splits.py, fits from fitting.py, and the hard
    date-bound guards from synthetic_control.py.
  safety_tests: the three test files above
```

The implementation MUST preserve: Colab-first execution; one user-facing
notebook; one `run_stage(config)`; canonical package path `src/lst_models/`;
no stage-to-stage imports; train-domain-only scope; the per-cell same-row
dummy contract of section 5; `holdout_test_contact=false` plus
`train_domain_only=true` and `sensitivity_scan_no_cell_selected=true` in the
manifest; the durable Drive result-save cell immediately after `run_stage`
succeeds; checkpoint writing per completed cell; runtime paths injected into
the config before `run_stage` and before the config contract assertions;
notebook static-gate compatibility.

---

Provenance: motivation quotes verified against
`paper/sections/09_limitations_conclusion.tex` and
`paper/sections/03_protocol.tex` on 2026-07-01; frozen label policy
`h09_bps3p0` from `configs/stages/00_data_split_label_freeze.yaml` and
`docs/protocols/00_data_split_label_freeze_protocol.md` sections 6/15.
Upstream pins: Stage 00 `20260610_051705_347450`, Stage 01 `20260610_075002`,
executed Stage 02 `20260610_082130_797479` (the Stage 03-pinned frozen run).
Structural precedents:
`docs/protocols/v2_1_conditional_predictability_preregistration.md` and
`docs/protocols/v2_positive_control_preregistration_20260701.md`. Governance:
`AGENTS.md` (research safety, no fabrication) > claims ledger
`paper/outline_and_claims.md` > red lines (`.claude/CLAUDE.md` §3) > anti-AI
style gates. This document adds no number to the ledger; ledger rows may be
PROPOSED only after the run completes.

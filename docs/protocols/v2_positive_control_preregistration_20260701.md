# V2 Synthetic Positive Control Pre-Registration (Train-Domain, Semi-Synthetic Labels)

Status: pre-registration SIGNED OFF 2026-07-01 (author authorization via
working session: run order "M4 -> M1 -> E5 -> E3 -> E4", Colab GPU execution
by the author). This
document MUST be committed BEFORE any arm is fitted. Once the first fit cell of
`notebooks/v2_synthetic_positive_control_colab.ipynb` runs, sections 3-8 are
frozen; changing any of them afterwards requires a new dated pre-registered
revision recorded in section 12 (Stage 03 / V2.1 precedent). This document
contains NO result numbers; every quantity it names is either a design
parameter fixed here or a pointer to a frozen artifact read at run time.

## 1. Designation & Scope

Fixed designation (mandatory, verbatim, in every artifact header, notebook
title cell, and summary built on this analysis):

```text
train-domain synthetic positive control (semi-synthetic labels,
protocol-validation evidence only)
```

What this experiment IS: an injection study that plants a KNOWN synthetic
signal of controlled strength into a copy of the frozen train-segment labels,
runs the protocol's own train-inner machinery unchanged, and checks whether
the readout (same-row stratified-dummy floor, macro-F1 delta, per-ticker
positivity, fold/seed LCB, label-shuffle sentinel) responds monotonically to
the planted strength and reads null when the strength is zero. It measures the
protocol's measurement chain, not any market phenomenon.

What this experiment is NOT: NOT market evidence, NOT model evidence, NOT a
model comparison, NOT a selection event, NOT a validation or holdout readout.
No model is selected; the V2 frozen selection (`price_volume_time_w20` /
`tcn` / `tcn_p01`) is unchanged regardless of outcome. Its numbers may never
be fused with the three existing evidence domains (official validation n=2,
train-inner control, guarded walk-forward); they form a separate fourth
domain that supports protocol-sensitivity wording only.

**DOMAIN INVARIANT (load-bearing, enforced in code): the entire experiment
runs on the frozen TRAIN segment only, 1998-01-02 (inclusive) through
2013-09-16 (exclusive), using the existing train-inner fold machinery. ZERO
contact with the official validation split (2013-09-16 to 2017-01-25). ZERO
contact with post-2017 rows. The code raises `ValueError` on any timestamp at
or after 2013-09-16** (`src/lst_models/synthetic_control.py`:
`assert_train_domain_only`, applied to the event index, the raw train bars,
the feature frame, every arm's window metadata, and the fold boundaries;
`require_frozen_train_boundaries` cross-checks the frozen Stage 00
`split_freeze.json` against these literals before any row is touched).

Forbidden strings in every output and summary of this analysis (verbatim):
`market evidence`, `real edge confirmed`, `model evidence`, `profitable`,
`clean test`, `final model`. The synthetic-control outcome is never described
as validating any real-data edge; at most it validates the instrument that
measured that edge.

## 2. Motivation: The Paper's Own Gap Statements

External review reduces the paper's headline weakness to one sentence: the
protocol is a detector that has never been shown to detect anything. The paper
already concedes this in four places (quoted verbatim; these are the exact
sentences the section 11 outcome map would change AFTER the run):

- `paper/sections/03_protocol.tex:14-17`: "One limit is built in: we exercise
  the protocol on a single near-null case with no known-signal positive
  control. Its power to separate signal from noise rests on construction here,
  not on a demonstration."
- `paper/sections/01_intro.tex:66-68`: "... with no profit-and-loss, cost
  model, or known-signal positive control. Whether the same protocol flags
  these signs as absent on a genuine signal is the positive-control next
  step."
- `paper/sections/04_models.tex:10-13`: "None is a known-signal positive
  control. The roster therefore exercises the protocol on a near-null case: it
  cannot prove that a surviving edge is not manufactured by an uncontrolled
  confound, nor that the protocol would catch a real signal."
- `paper/sections/09_limitations_conclusion.tex:22-23`: "The protocol runs on
  one near-null case with no known-signal positive control, so its sensitivity
  to a genuine signal is untested." And `:53-55`: "The defined next step is a
  known-signal positive control: confirming that the same protocol flags these
  signs as absent when a genuine signal is present."

This experiment is that defined next step, scoped so that it cannot contaminate
any frozen readout: it runs entirely inside the train segment already consumed
by Stage 01/02 selection, on synthetic labels, with the predeclared primary
configuration only.

## 3. Injection Specification (semi-synthetic labels on real features)

Mechanism (`src/lst_models/synthetic_control.py`: `planted_rule_values`,
`inject_planted_labels`):

1. Build the train-segment data EXACTLY as the executed Stage 02 does, by
   calling the same functions: frozen Stage 00 artifacts ->
   `data.load_train_bars` -> `features.build_feature_frame` ->
   `splits.train_valid_events` -> `splits.build_train_inner_folds` ->
   `windows.build_window_dataset`. No label, feature, window, or fold logic is
   re-implemented.
2. Planted rule, fixed: `r(row) = 1` if the target bar's day-local
   `log_return` is strictly positive, else `0` (non-finite values map to 0 and
   are counted; see leak-freeness note below). `log_return` is a column of the
   real feature frame and a member of the frozen primary candidate's feature
   set (`price_volume_time`, Stage 01 config
   `configs/stages/01_feature_window_search.yaml:50-60`), evaluated at the
   LAST bar of every input window.
3. For a planted-signal arm of strength `s`, each ELIGIBLE train row's binary
   label is independently replaced by:

   ```text
   label := r(row)      with probability 0.5 + s
   label := 1 - r(row)  with probability 0.5 - s
   ```

   Per-row randomness is the first 8 bytes of
   `sha256(injection_seed | arm_id | sample_id)` mapped to [0, 1), with
   `injection_seed = 20260701` fixed here. The synthetic label set per arm is
   therefore frozen, order-invariant, and exactly reproducible; each arm's
   labels are hashed into the injection manifest.
4. ONLY the `label` column changes. Row eligibility (the Stage 00 no-trade-band
   and validity flags), features, timestamps, tickers, fold boundaries, and
   sample identity are untouched. The runner enforces this: the windowed
   dataset's `sample_id` hash must be identical across all arms
   (`eligibility_invariance` in `spc_injection_manifest.json`), and the run
   fails closed otherwise.

Why the rule is leak-free: `r` reads `close[t-1]` and `close[t]` only — both
at or before the window's final bar, strictly before the 9-bar label horizon
(`t+1 .. t+9`). No information from the horizon or from any future row enters
the synthetic label; the only forward-looking machinery (eligibility flags) is
inherited unchanged from the REAL pipeline and is identical across arms, so it
cannot encode the plant. The rule is row-local: it crosses no ticker, no
trading day, and no split boundary.

Why the rule is learnable in principle: `r` is a threshold on a single input
coordinate the model receives — the `log_return` channel at the last time step
of the 20-bar window. The tcn_tiny profile (two residual blocks, kernel 2,
causal) sees that coordinate directly at the window's final position; a
one-feature threshold is far inside its capacity. Global z-scoring (the real
pipeline's train-fit normalization) is a monotone affine map per feature, so
the threshold remains a threshold. Deliberately choosing an EASY rule is the
point: it isolates the protocol's measurement chain from model capacity, so a
failure to detect indicts the readout, not the learner.

Delta calibration by construction: with a roughly balanced rule
(`log_return` sign on 5-minute bars) the synthetic class prior stays near 0.5,
the recomputed stratified-dummy floor stays near the balanced level, the
Bayes-optimal accuracy is `0.5 + s`, and the achievable same-row macro-F1
delta over the dummy has ceiling approximately `s`. Injected strength is
therefore expressed directly in the readout's own units.

Rows whose rule value is non-finite (`log_return` NaN at the first bar of a
day) are relabeled with `r = 0` and counted in the manifest; such rows can
never appear as a scored window target for the primary candidate, because
window validity already requires every in-window feature value to be finite
(`windows.build_window_dataset`). The runner's eligibility-invariance hash
covers this: those rows drop out identically in every arm.

Known, accepted asymmetry (predeclared): the fold-row caps
(`hpo_sample_policy` 50000/20000, deterministic even-stride by ticker x label)
stratify on the SYNTHETIC labels, exactly as the real pipeline stratifies on
real labels. Capped row subsets may therefore differ slightly across arms.
The same-row model-versus-dummy contract — the contract the protocol actually
relies on — holds within every trial row (identical `eval_sample_id_hash` for
model and baselines), and per-fold row hashes are recorded in the trial
ledger for audit.

## 4. Arms

| arm_id | strength s | role | justification |
|---|---:|---|---|
| `arm_s0p000` | 0.000 | mandatory null arm | labels become independent fair coins (P(label=r)=0.5 exactly), feature-independent by construction; the protocol MUST read null here |
| `arm_s0p010` | 0.010 | observed-edge-scale threshold arm | one macro-F1 point is the scale of the ledger-recorded real validation margin (the paper's 1.69 pp row-pooled delta, `paper/outline_and_claims.md` / `paper/sections/09_limitations_conclusion.tex:15-16`); this is the scientifically interesting detection threshold. Reported, never gated |
| `arm_s0p020` | 0.020 | must-detect arm | twice the observed-edge scale; if the protocol cannot flag this, its sensitivity claim fails at any relevant scale |
| `arm_s0p050` | 0.050 | must-detect ceiling arm | comfortably above the train-inner noise floor; anchors the monotone response and confirms the readout scales with s |

Four arms, frozen. Adding, removing, or re-running arms after the first fit is
a forbidden search axis (`configs/stages/v2_synthetic_positive_control.yaml`
`forbidden.search_axes`).

## 5. Readout Machinery (identical to the executed Stage 02 path)

- Same frozen upstream inputs, pinned by exact run id: Stage 00
  `20260610_051705_347450` (splits, labels, event index), Stage 01
  `20260610_075002` (the frozen primary candidate input
  `price_volume_time_w20`: feature set, feature columns, window size 20).
- Same fold design: 3 chronological expanding day-block train-inner folds from
  `splits.build_train_inner_folds`, zero event overlap required.
- Same frozen seeds: [101, 202]. The injection seed is separate and fixed
  (20260701), so the two protocol seeds exercise only the protocol's own
  stochasticity (dummy draws, torch init, batch order) exactly as on real data.
- Same fold-row caps and stride sampling as the executed Stage 02 config.
- Same four registry baselines recomputed per fold/seed ON THE SYNTHETIC
  labels (`metrics.score_registry_baseline`): stratified dummy (primary,
  seeded with the trial seed), majority, constant up, constant down.
- Same fit path: `fitting.fit_stage_control` with probe `tcn_tiny` and the
  frozen primary profile `tcn_p01` read from
  `configs/models/tcn/search_space.yaml`; torch training defaults identical to
  `configs/stages/02_model_hpo_train_inner.yaml` (64 epochs max,
  inner-train chronological-tail early stopping, patience 8, clip 1.0) —
  equality is pinned by
  `tests/contracts/test_v2_synthetic_positive_control_config_contract.py`.
- Same metrics: macro-F1, balanced accuracy, MCC, ROC-AUC, same-row
  `delta_macro_f1_vs_baseline`, per-ticker delta and positivity count
  (`metrics.ticker_delta_macro_f1`), per-(ticker, trading_day) block deltas,
  and the fold/seed Student-t LCB (`metrics.compute_metric_lcb`) — all
  descriptive, none a significance test.
- Sentinels per completed trial row (`metrics.same_row_delta_sentinels`,
  n_perm=200, seed 20260617, blocks = ticker|trading_day): within-day
  label-shuffle null and within-day time-reverse delta.

## 6. Predeclared Expectations And Pass/Fail Criteria

Definitions, fixed before any fit. Per arm, over the 6 completed fold-by-seed
rows (3 folds x 2 seeds):

- `mean_delta` = mean same-row macro-F1 delta versus the stratified dummy;
- `lcb_delta` = Student-t lower bound over those 6 deltas
  (`compute_metric_lcb`, the same conservative ranking statistic Stage 02
  uses);
- an arm **flags a signal** when ALL of: `mean_delta > 0`, `lcb_delta > 0`,
  and every completed row's `positive_ticker_count >= 3` (the predeclared
  Stage 02 floor, `selection_rules.minimum_positive_ticker_count`).
- **Null band B** (pointer definition, no number restated here): the maximum
  absolute `delta_macro_f1_vs_baseline` over the 6 completed real-data rows of
  the IDENTICAL machinery — candidate `price_volume_time_w20`, family `tcn`,
  profile `tcn_p01` — in the frozen executed Stage 02 trial ledger
  (`02_hpo_trial_ledger.csv` of run `20260610_082130_797479`, the run pinned
  by the Stage 03 config). B is the observed train-inner control spread of the
  near-null real case; the runner reads it from the frozen artifact at run
  time and records it in `spc_criteria_readout.json`.

Predeclared expected patterns:

- (a) the s=0 arm reads within the null band: `|mean_delta| <= B`, with
  `lcb_delta <= 0` and no signal flag;
- (b) `mean_delta` increases monotonically in s; the primary monotonicity gate
  is over the pass/fail arms {0, 0.02, 0.05} (strict increase); the full
  four-arm ordering including s=0.01 is reported as the empirical
  dose-response curve, with the 0.01 arm's placement read as the protocol's
  detection threshold, not gated (it sits at the scale of the train-inner
  noise floor, where either outcome is informative);
- (c) the 0.02 and 0.05 arms both flag a signal.

PASS requires all three of:

- P1 (null honesty): the s=0 arm does not flag a signal, its `lcb_delta <= 0`,
  and `|mean_delta| <= B`.
- P2 (monotone response): `mean_delta(0) < mean_delta(0.02) < mean_delta(0.05)`.
- P3 (detection): the s=0.02 arm AND the s=0.05 arm each flag a signal.

FAIL modes and their predeclared meanings
(`spc_criteria_readout.json:overall_outcome`, computed by
`synthetic_control.evaluate_predeclared_criteria`):

- `fail_insensitive` — P3 fails: the protocol as configured cannot flag a
  planted signal at twice the observed-edge scale. Honesty requires the paper
  to KEEP and STRENGTHEN the §9 sensitivity limitation (the "untested" wording
  would become "tested and not demonstrated at the 2-point scale"), and the
  intro/§4 sentences may not be softened. Any capacity/budget investigation
  (more epochs, different caps) is a NEW dated preregistration revision, never
  a silent rerun.
- `fail_manufacturing` — the s=0 arm flags a signal: the readout can
  manufacture an edge from feature-independent coin-flip labels. This is the
  most serious outcome: it would put the real-data near-null reading itself
  under suspicion, must be reported prominently, and freezes any further
  paper-facing use of the readout until the mechanism is diagnosed under a new
  preregistered revision.
- `fail_nonmonotone_or_null_band` — endpoints behave but the ordering or the
  null band fails: measurement instability; report as partial validation; no
  sensitivity sentence enters the paper.
- `incomplete_run_fix_and_rerun` — any arm has failed/missing fit rows: no
  scientific reading at all; fix the engineering fault and rerun under the
  deviation log.

The s=0.01 threshold arm maps to wording only, in either direction: if it
flags, the demonstrated sensitivity reaches the scale of the recorded observed
edge; if it does not, the demonstrated sensitivity is at twice that scale and
the observed-edge scale remains at or below the detection threshold. Both
statements are admissible only with the run's numbers cited from
`spc_arm_summary.csv`.

## 7. Predeclared Diagnostics Per Arm

- Dummy-floor flatness: the stratified-dummy macro-F1 per arm/fold/seed
  (`mean_dummy_macro_f1` in `spc_arm_summary.csv`). Expected: near the
  balanced level and flat across arms, because the injection preserves an
  approximately 0.5 class prior (the prior shift is `s * (2*P(r=1) - 1)`,
  second-order small for a balanced rule; the realized per-arm prior is
  recorded in the injection manifest). A material drift of the floor with s
  flags marginal contamination and voids the delta reading pending
  investigation.
- Per-ticker positivity: expected near chance-split at s=0 and rising toward
  5/5 at s=0.05; the per-trial counts and per-ticker deltas are in the trial
  ledger.
- Label-shuffle sentinel (within-day permutation, per completed trial row) —
  expected behavior per arm, reasoned in advance:
  - The plant is a ROW-LEVEL feature-label coupling inside each trading day
    (`r` varies bar to bar; relabeling is independent per row). Permuting
    labels within each (ticker, trading_day) block preserves the day's label
    marginals but destroys the row correspondence, so the planted edge MUST
    collapse toward the permutation null. The plant does NOT survive the
    shuffle by construction — and that is the point: a plant that survived
    (for example a day-level base-rate plant) would say nothing about
    row-level detection.
  - s=0: observed delta and shuffle null are both near zero; the permutation
    p-value is uninformative by design (nothing to collapse).
  - s>0: observed delta positive, shuffle null centered near zero; the
    separation (and the descriptive permutation p-value) should sharpen as s
    grows. Expected qualitatively: clear separation at 0.02 and 0.05.
  - This is itself a second positive control — of the sentinel. On real data
    the label-shuffle sentinel has only ever confirmed near-null; here it is
    exercised against a known genuine row-level signal for the first time. If
    a planted arm's delta SURVIVES the shuffle, the sentinel itself is
    measuring marginals rather than row-level structure — investigate before
    any paper use.
  - Honest scope note (unchanged by any outcome): this validates the sentinel
    against row-level plants only. It adds no power against artifact classes
    the sentinel is already known to be blind to — in particular the
    Roll (1984) bid-ask bounce discussed at
    `paper/sections/09_limitations_conclusion.tex:43-51`, which is itself a
    genuine row-level alignment and passes the shuffle. The positive control
    does not close that limitation and must not be quoted as if it did.
  - Time-reverse sentinel: same collapse expectation for s>0 (predictions
    realigned to other bars' labels within the day).
- Fit health: all 24 rows `fit_status = completed`; early-stopping source and
  hashes recorded per row; device provenance recorded in ledger and manifest.
  Any failed row triggers the `incomplete_run_fix_and_rerun` outcome.

## 8. Compute Scope

`tcn_tiny` profile `tcn_p01` ONLY — the predeclared primary configuration
(paper §4; frozen by Stage 02). This experiment measures the sensitivity of
the protocol's readout chain, not a family comparison; one family suffices,
and the primary is the only configuration whose sensitivity the paper's
narrative depends on. Cost: 4 arms x 3 folds x 2 seeds = 24 tiny-TCN fits on
capped fold rows (at most 50000 train / 20000 eval rows per fold, the same
caps as the executed Stage 02), plus 96 trivial baseline scorings, 24
sentinel computations (200 within-day permutations each on at most 20000
rows), one raw-data rebuild, and four window-dataset builds. This is roughly
an eighth of the executed Stage 02 run's fit count (192 rows across four
families under identical caps) on the same Colab GPU class; a single Colab
session is the expected envelope. The runner writes a local checkpoint after
every completed arm (`checkpoint_manifest.json` + partial ledger); recovery
policy is rerun-from-scratch under a fresh run id (24 fits is inside a
session), with the checkpoint as audit state, mirroring the compact end of
the AGENTS checkpoint rules.

## 9. Outputs

```text
/content/lst_models_results/v2_synthetic_positive_control/<run_id>/
  run_manifest.json                    # synthetic_labels=true, train_domain_only=true,
                                       # holdout_test_contact=false, official_validation_contact=false,
                                       # feature-rebuild hash gate vs Stage 01, raw integrity,
                                       # device provenance, train-domain bounds, null-band record
  artifact_inventory.csv
  spc_trial_ledger.csv                 # per arm x fold x seed, Stage 02 ledger schema + arm columns
  spc_trials_arm_s0p000.csv            # per-arm slices of the same ledger
  spc_trials_arm_s0p010.csv
  spc_trials_arm_s0p020.csv
  spc_trials_arm_s0p050.csv
  spc_arm_summary.csv                  # per-arm mean/LCB delta, dummy floor, flags, sentinel means
  spc_baseline_control_summary.csv     # four registry baselines per arm/fold/seed
  spc_sentinel_ledger.csv              # label-shuffle + time-reverse per completed row
  spc_injection_manifest.json          # rule, seed, per-arm label sha256, agreement rate, priors,
                                       # eligibility-invariance hash check
  spc_criteria_readout.json            # P1/P2/P3 booleans + overall_outcome + null-band source
```

Durable backup: `My Drive/lst_models/results/v2_synthetic_positive_control/<run_id>/`
(drive_backup_manifest.json written and uploaded last).

## 10. Start Gate

The runner fails closed unless all of these hold (enforced in
`stages/synthetic_positive_control.py`):

- exact-run-id Stage 00 / Stage 01 / real-Stage-02 artifacts resolve, with
  `holdout_test_contact=false` in every upstream manifest and the run-id chain
  verified against the config pins;
- `split_freeze.json` matches the preregistered boundaries verbatim
  (1998-01-02 / 2013-09-16 / 2017-01-25);
- the Stage 01 handoff contains exactly one `price_volume_time_w20` candidate
  and its feature columns include `log_return` (otherwise the plant would not
  be learnable in-window);
- the Stage 01 manifest's `feature_rebuild_code_sha256` matches the current
  rebuild code (same gate as Stage 02/03/04);
- the null-band source rows exist, are exactly 6, and are all completed;
- the planned fit count (arms x folds x seeds) is within the declared budget;
- every timestamp guard in section 1 passes.

## 11. Outcome -> Paper Integration Map (NO edits now)

No paper file, and no row of `paper/outline_and_claims.md`, is edited as part
of this preparation. After the run completes and the user signs off, outcomes
map to edits as follows, all numbers quoted only from `spc_arm_summary.csv` /
`spc_criteria_readout.json` and entered through the claims-ledger process
first (proposed new ledger family: "synthetic positive control (train-domain,
semi-synthetic labels)" — a fourth evidence domain, never fused with the other
three, supporting protocol-sensitivity wording only).

On PASS (P1+P2+P3):

- `paper/sections/09_limitations_conclusion.tex:22-23` — "The protocol runs on
  one near-null case with no known-signal positive control, so its sensitivity
  to a genuine signal is untested." -> replaced by one sentence stating the
  worked positive control: a planted train-domain signal at strengths
  {0.01, 0.02, 0.05} produced a monotone same-row delta readout with a null
  reading at strength zero (numbers from the run), with the domain caveat
  (train segment, semi-synthetic labels, tcn_tiny only) in the same sentence.
- `paper/sections/09_limitations_conclusion.tex:53-55` — "The defined next
  step is a known-signal positive control: ..." -> the next-step framing
  becomes a completed-control statement, or is replaced by the remaining
  genuinely-open next steps (e.g., the deferred half-spread control at
  `:49-51`, which this experiment deliberately does NOT close).
- `paper/sections/03_protocol.tex:14-17` — "Its power to separate signal from
  noise rests on construction here, not on a demonstration." -> "rests on
  construction and a train-domain synthetic positive control" with the
  one-clause result and a pointer to the artifact.
- `paper/sections/01_intro.tex:66-68` — the "positive-control next step"
  clause updates to a one-clause worked control; the contribution list may
  cite it as protocol validation, still never as evidence about the real edge.
- `paper/sections/04_models.tex:10-13` — "nor that the protocol would catch a
  real signal" weakens to the demonstrated scope (a planted feature-measurable
  signal at the stated strengths), leaving the uncontrolled-confound half of
  the sentence intact — the synthetic control does not address confounds such
  as the Roll bounce.

On `fail_insensitive`: the four sentences above stay; §9's "untested" is
replaced by the strictly more damaging "tested and not demonstrated at twice
the observed scale" with the run cited; the paper's sensitivity narrative must
not be softened anywhere. On `fail_manufacturing`: additionally, the
real-data near-null interpretation is re-opened — §9 gains an explicit
warning that the readout produced a positive flag on feature-independent
labels, and no protocol-sensitivity claim of any kind enters the paper. On
`fail_nonmonotone_or_null_band` or `incomplete_run_fix_and_rerun`: no paper
change; deviation log + rerun decision first.

## 12. Deviation Log

(Empty at pre-registration. Every post-freeze change — config edit, arm
change, rerun, seed change, criteria reinterpretation — must be recorded here
with date, reason, and effect BEFORE results are interpreted.)

| date | deviation | reason | effect on section 6 criteria |
|---|---|---|---|
| — | — | — | — |

## 13. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this pre-registration document
- the target notebook, config, module, or test

Placement decision recorded for this implementation:

```text
placement_decision:
  target_file_type: protocol + stage_config + python_module + test + notebook
  target_path:
    - docs/protocols/v2_positive_control_preregistration_20260701.md
    - configs/stages/v2_synthetic_positive_control.yaml
    - src/lst_models/synthetic_control.py
    - src/lst_models/stages/synthetic_positive_control.py
    - notebooks/v2_synthetic_positive_control_colab.ipynb
    - tests/stages/test_synthetic_positive_control.py
    - tests/contracts/test_v2_synthetic_positive_control_config_contract.py
    - tests/notebooks/test_v2_synthetic_positive_control_notebook_static.py
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: label injection and train-domain date-bound guards are
    safety-critical and shared by the stage entry point and the tests; they
    must be provably identical between the test suite and Colab execution.
  why_not_utils: purpose-specific domain module mirroring the V2.1 precedent
    (guarded_walkforward.py + stages/guarded_walkforward_readout.py).
  safety_tests: the three test files above
```

The implementation MUST preserve: Colab-first execution; one user-facing
notebook; one `run_stage(config)`; canonical package path `src/lst_models/`;
no stage-to-stage imports; train-only scope (this stage is stricter:
train-domain only, synthetic labels); same-row dummy baselines wherever model
metrics are reported; `holdout_test_contact=false` plus
`synthetic_labels=true` in the manifest; the durable Drive result-save cell
immediately after `run_stage` succeeds; checkpoint writing per completed arm;
runtime paths injected into the config before `run_stage` and before the
config contract assertions; notebook static-gate compatibility.

---

Provenance: motivation quotes verified against the paper sources listed in
section 2 on 2026-07-01. Upstream pins: Stage 00 `20260610_051705_347450`,
Stage 01 `20260610_075002`, real Stage 02 `20260610_082130_797479` (the Stage
03-pinned frozen run). Governance: `AGENTS.md` (research safety, no
fabrication) > claims ledger `paper/outline_and_claims.md` > red lines
(`.claude/CLAUDE.md` §3) > anti-AI style gates. This document adds no number
to the ledger; a ledger row may be PROPOSED only after the run completes.

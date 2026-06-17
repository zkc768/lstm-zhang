# V2.1 Guarded Walk-Forward Readout Protocol (Pre-Registration)

Status: pre-registration DRAFT, awaiting user + Ian sign-off. No V2.1 contact
with rows at or after `2017-01-25` — not even a metadata read — may occur
before section 16 records (a) user sign-off on the open decisions OD-A..OD-F,
and (b) the coverage-probe authorization. No guarded scoring event may occur
before section 16 additionally records (c) the filled period table from the
coverage probe and (d) Ian's confirmation of the period design and model
roster. Once the first guarded scoring event has occurred, sections 2-12 are
frozen; changing any of them afterwards requires a new pre-registered protocol
revision and a fresh run, recorded as such (Stage 03 precedent).

Scope: V2.1 route extension only. This document pre-registers the one-shot
guarded, historically-contacted walk-forward readout on the post-2017 closed
segment, requested by Ian on 2026-06-04. It does not change any V2 frozen
artifact, decision, or claim, and it does not authorize any other contact with
the closed segment.

Stage identity (route guide §6 naming; executable surface is follow-up work,
section 13):

```text
stage_name:        v2_1_guarded_walkforward_readout
protocol:          docs/protocols/v2_1_guarded_walkforward_readout_protocol.md
config (planned):  configs/stages/v2_1_guarded_walkforward_readout.yaml
notebook (planned): notebooks/v2_1_guarded_walkforward_readout_colab.ipynb
runner (planned):  src/lst_models/stages/guarded_walkforward_readout.py
```

Requirement provenance (verbatim source:
`docs/ian_lan_requirement_extracts.md`, Gmail msg `19e9479d4932a413`,
2026-06-04):

> "run the current model on 2–3 additional walk-forward holdout periods to
> check whether the positive result is stable over time. For each period,
> please report tested results."
> "prepare one final comparison table using the same setting. The table should
> include Dummy, LightGBM, standard DLinear, TCN, and MS-DLinear+TCN."

Guarded premise (user → Ian, msg `19e83446cbf5ee8f`, 2026-06-01, accepted by
Ian):

> "Since this holdout period has already been used before, I would not present
> this as final evidence."

Revision record:

- 2026-06-10: initial pre-registration draft (zero V2.1 contact events have
  occurred; the V2 chain 00-03 is frozen; Stage 04 bundle implemented and
  awaiting its one Colab execution).

## 1. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `AGENTS.md`
- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- `docs/protocols/06_ian_final_progress_record_protocol.md` (D4 freeze; the
  guarded-wording obligation originates there)
- `docs/protocols/03_frozen_validation_readout_protocol.md` (mechanism source
  for refit recipe, ledger, checkpoint, and resume contracts)
- the target notebook, config, module, or test

Before writing code, the implementer MUST record a placement decision with the
AGENTS.md §2 fields. For this protocol document:

```text
placement_decision:
  target_file_type: protocol
  target_path: docs/protocols/v2_1_guarded_walkforward_readout_protocol.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; pre-registration protocol text only
  why_not_utils: not applicable; pre-registration protocol text only
  safety_tests: not applicable at pre-registration; section 13 declares the
    V2.1 test triad for the implementation bundle
```

Implementation must preserve:

- Colab-first execution; one user-facing V2.1 notebook; one config; one
  `run_stage(config)`; sidecars updated in the same task.
- All V2 stage protocols, configs, notebooks, manifests, and static gates
  UNCHANGED: V2 stages keep `holdout_test_contact=false` and their forbidden
  holdout-read patterns. The V2.1 surface gets its own gates; it never
  weakens a V2 gate.
- Chronological discipline: no random or shuffled splits; per-period training
  rows strictly precede that period's scored rows; labels, windows, and
  preprocessing obey the frozen Stage 00 rules (sections 5-6).
- Train-only preprocessing per period: every learned statistic, including
  class weights and scalers, is fit on that period's training fit-subset rows
  only.
- Zero new HPO: every model-row hyperparameter is a verbatim copy from frozen
  Stage 02/03 artifacts (section 7); only early-stopping iteration/epoch,
  class weights, and preprocessing statistics are re-derived, on training
  rows only, under the frozen D1 mechanism.
- Same-row registry baselines wherever model metrics are reported.
- One scoring event per period x model row x seed, with a scoring-event
  ledger (section 10).
- AMENDED MANIFEST LINE (scoped to this stage only): the V2.1 run manifest
  records `holdout_test_contact=true` together with
  `holdout_contact_tier=guarded_historically_contacted` and
  `holdout_contact_authorization` pointing at this protocol and its sign-off
  record. Writing `false` here would be a fabrication; the AGENTS.md §7
  template line "run manifest with holdout_test_contact=false" applies to V2
  validation-only stages and is explicitly amended for this pre-registered
  stage. `official_validation_scoring_events=0` and
  `official_validation_for_selection=false` still hold (section 9).
- Durable Drive result save immediately after `run_stage(config)`;
  checkpoints + exact-run-id resume (section 10).
- Runtime paths injected into config before `run_stage(config)`; GPU/CUDA
  device provenance recorded; exact-commit Colab bootstrap pinned to a
  full-bundle commit; notebook static-gate compatibility.

## 2. Stage Role And Guarded Characterization

V2.1 is a route EXTENSION, not a V2 stage. The V2 route (00-06) remains
exactly as frozen; roadmap decision D4(a) — Stage 06 is a progress record and
V2 claims remain validation-only — is unchanged by this document.

Fixed designation (mandatory, verbatim, in every V2.1 artifact header,
notebook title cell, report, thesis section, and email summary):

```text
guarded, historically-contacted walk-forward readout
```

What this readout IS:

- The pre-registered D4-compatible opening of the post-2017 segment that the
  06 protocol §4 anticipated: the V1 route historically contacted the
  post-2017 segment, so opening it can only ever yield a "guarded,
  historically-contacted test", never a clean test.
- A one-shot stability check of the V2 frozen primary candidate over 2-3
  consecutive post-2017 walk-forward periods, plus a same-setting comparison
  table (Dummy, LightGBM, standard DLinear, TCN, MS-DLinear+TCN), exactly as
  Ian requested on 2026-06-04 and under the guarded premise Ian accepted on
  2026-06-01.
- Supplementary guarded evidence for the paper, reported alongside — never in
  place of — the V2 validation-only evidence.

What this readout is NOT:

- NOT a clean test, NOT final evidence, NOT proof of generalization. The V1
  contact history taints the entire closed segment at the route level; no
  sub-period is exempt.
- NOT a selection event. It cannot change the V2 frozen selection
  (primary `price_volume_time_w20` / `tcn` / `tcn_p01`), cannot activate or
  promote the Stage 02 fallback, cannot crown any roster row a winner, and
  cannot feed any tuning, thresholding, calibration, or model revision.
- NOT a license for further closed-segment contact. Rows at or after the
  final period's end-exclusive boundary stay closed. After execution, the
  consumed periods are spent: any future work (V2.2 or later) must use rows
  after the final boundary, future-collected data, or pre-registered external
  tickers.

The V2 frozen evidence basis this protocol builds on:

| Item | Frozen value |
|---|---|
| Stage 00 run | `20260610_051705_347450` (R3 chain) |
| Stage 01 run | `20260610_075002` |
| Stage 02 run | `20260610_082130_797479` (superseded ids rejected: `20260609_100637_704705`, `20260610_010019_507648`) |
| Stage 03 run | `20260610_133305_716174`, decision `met_predeclared_validation_readout_criteria` |
| Frozen primary | `price_volume_time_w20`, family `tcn`, profile `tcn_p01` (`channels [16,16]`, `kernel_size 2`, `dropout 0.0`, `learning_rate 0.001`, `weight_decay 0.0001`), window 20 |
| Stage 03 aggregate | pooled macro-F1 0.51703; delta vs stratified dummy +0.01689; positive tickers 5/5 |
| Label policy | `endpoint_cumulative_return`, h=9 bars (45 min), no-trade band ±3.0 bps |
| Modeling scope | pooled five-ticker (CSCO, JPM, KO, MSFT, WMT) |
| Splits | train 1998-01-02 → 2013-09-16 (excl.); official validation 2013-09-16 → 2017-01-25 (excl.); closed segment ≥ 2017-01-25 |
| Seeds | `[101, 202]` |

## 3. Wording Rules

V2.1 inherits the full Stage 03 forbidden list and extends it. Forbidden
strings in all V2.1 outputs, notebook text, decision records, emails built on
V2.1 evidence, and thesis text:

```text
final model
official validation winner
holdout winner
test winner
proved best model
generalization proven
profitable
holdout-ready
selected by official validation
chosen threshold
clean test
clean holdout
untouched test
untouched holdout
final evidence
out-of-sample proof
walk-forward winner
```

Allowed wording:

```text
guarded, historically-contacted walk-forward readout
guarded walk-forward evidence
guarded period-stability readout
primary candidate met/did not meet predeclared guarded stability criteria
validation-only evidence (for V2 results quoted alongside)
```

Mandatory qualification rules:

- Every quantitative claim from V2.1 artifacts carries the guarded
  qualification. Ian's phrase "tested results" may be echoed only inside a
  guarded construction, e.g. "tested results from the guarded,
  historically-contacted walk-forward readout".
- The V1 contact history must be stated wherever V2.1 results are first
  presented in any document: the 06 progress record, the thesis, and any
  email summary. Silently upgrading guarded results into clean-test claims is
  forbidden (06 protocol §4).
- Comparison-table rows other than the frozen primary are comparison
  evidence. No text may rank them into a recommendation, e.g. "X was the best
  model in period 2" is forbidden; "X's guarded delta in period 2 was +d" is
  allowed.

## 4. Entry Gates

V2.1 must fail closed before any closed-segment contact when any gate fails.
Gate failures raise exact-path/exact-field errors and produce a
`do_not_start_v2_1_*` decision record with `guarded_scoring_events=0`.

1. Pre-registration complete: section 16 records user sign-off (OD-A..OD-F
   resolved), the coverage-probe artifact reference with sha256, the filled
   period table, and Ian's confirmation reference (email message id). The
   runner re-asserts the config echoes of these values; unfilled placeholders
   block the run.
2. Exact V2 chain by run id (no parent-folder inference): Stage 00
   `20260610_051705_347450`, Stage 01 `20260610_075002`, Stage 02
   `20260610_082130_797479`, Stage 03 `20260610_133305_716174`. Superseded
   Stage 02 ids are rejected. Required artifacts per upstream run mirror the
   Stage 03/04 entry-gate lists, verified against each
   `artifact_inventory.csv` `bytes`/`sha256` via `artifacts.require_artifacts`
   (not existence-only). From Stage 02, `02_best_params_by_family.json` is
   additionally required (section 7 reads it). From Stage 03,
   `03_decision_record.json` with `readout_complete=true` is required.
3. Stage 04 ordering (OD-E): default — the frozen Stage 04 run id is recorded
   in the V2.1 config before execution (Stage 04 runs first; it costs zero
   scoring events). If the user overrides the ordering at sign-off, the
   override and its reason are recorded in section 16 and echoed in the
   decision record; the override changes ordering only, never any other gate.
4. Raw files downloaded by Google Drive file ID
   (`configs/lst_models_data.yaml`); per-file `sha256` and `bytes` verified
   against the frozen Stage 00 `raw_data_manifest.json` (the R3 chain records
   full hashes; no legacy tolerance applies to the pinned chain).
5. `artifacts.feature_rebuild_code_sha256()` computed at the V2.1 execution
   commit must equal the value recorded in the Stage 02 and Stage 03
   manifests. A mismatch means the frozen feature/window mechanism drifted
   and blocks the run.
6. Rebuild parity on the known span: rebuilt eligible train-row totals and
   per-ticker counts for the primary candidate input over the original train
   partition must equal `01_feature_window_search_summary.csv` (the same
   parity check Stages 02/03 ran). This proves the extended-span rebuild uses
   the identical mechanism before any closed-segment row is touched.
7. Upstream safety flags: `holdout_test_contact=false` and
   `official_validation_for_selection=false` on every V2 upstream manifest
   and handoff (their truthful V2 values).
8. Coverage-probe consistency: the probe artifact's per-ticker coverage and
   derived period table must equal the period table frozen in the config and
   in section 5. Any disagreement blocks the run.
9. Feasibility pre-flight (section 6) passes before any refit or scoring.

## 5. Period Design (Frozen Rule + Fill-In Block)

### 5.1 Frozen carving rule (zero discretion)

Periods are carved from the closed segment by rule, not by inspection:

- Periods are consecutive, non-overlapping, gap-free, earliest-first, and
  start at the closed boundary `2017-01-25`.
- Nominal period length: 12 calendar months (OD-B). Period i spans
  `[start_i, start_i + 12 months)`, start-inclusive, end-exclusive;
  `start_1 = 2017-01-25`.
- Period count: k = 3 (OD-A default; k = 2 is the predeclared reduction).
- Truncation rule: the final period is truncated at the end of the last
  trading day fully covered by all five raw ticker files. If the truncated
  final period contains fewer than 120 covered trading days (about half the
  nominal window), it is dropped and k reduces by one; the drop is recorded
  in `v2_1_period_registry.json`. No other boundary may move.
- Rows at or after the final period's end-exclusive boundary remain closed
  and untouched.

Resulting default table (k=3, pending coverage verification):

| period_id | start (inclusive) | end (exclusive) | note |
|---|---|---|---|
| `wf_p1` | 2017-01-25 | 2018-01-25 | fixed by rule |
| `wf_p2` | 2018-01-25 | 2019-01-25 | fixed by rule |
| `wf_p3` | 2019-01-25 | 2020-01-25 | end truncates to verified coverage |

Honest regime note: the earliest-first rule means a k=3 / 12-month design
covers 2017-2020 and stops before the 2020 COVID regime because those are the
first rows after the boundary, not because a favorable regime was selected.
Rows beyond the final boundary stay closed; a later regime-stress extension
would require its own pre-registered revision.

### 5.2 Pre-declared coverage probe (the only pre-execution contact)

The actual coverage end of the five raw files is NOT recorded anywhere in
this repository and MUST NOT be asserted from memory. It is verified by a
one-time, metadata-only coverage probe, executed once after user sign-off
(section 16 item (b)) and before Ian's final confirmation:

- Inputs: the five raw `.txt` files downloaded by Drive file ID, hashes
  verified against the frozen Stage 00 `raw_data_manifest.json`.
- Reads ONLY the `Date` and `Time` columns. Computes, per ticker: first
  calendar date, last calendar date, last fully-covered regular-session
  trading day, and per candidate period the covered trading-day count and raw
  1-minute row count.
- Derives the period table mechanically from the section 5.1 rule and writes
  `v2_1_coverage_probe.json` (schema in section 9) with the raw-file sha256
  values it verified.
- FORBIDDEN inside the probe: reading OHLC/volume values into any output,
  resampling, computing returns/labels/features, constructing any model or
  windowed tensor, and any per-period statistic beyond timestamp coverage
  counts.
- The probe is logged in the guarded contact ledger as event type
  `coverage_probe` (a metadata contact, not a scoring event) with timestamp
  and artifact sha256. It runs at most once; a re-run requires a recorded
  reason (e.g. raw-file hash change, which would itself block everything).

The probe's derived period table is then copied into section 16 and into the
V2.1 config. That copy is the ONLY permitted edit of the period table, the
exact analogue of Stage 03's `<NEW_STAGE02_RUN_ID>` fill rule.

### 5.3 Period split semantics (walk-forward contract)

For each period i, with day-aligned boundaries:

- Scored rows of period i: eligible target rows whose `trading_day` lies in
  `[start_i, end_i)`.
- Training rows of period i (expanding walk-forward): ALL eligible target
  rows whose `trading_day` lies strictly before `start_i` — the original
  train partition, the official validation partition, and the closed-segment
  prefix before `start_i`. Training data therefore rolls forward period by
  period.
- Eligibility is computed by the frozen Stage 00 operators run over the full
  covered span with the V2.1 period assignment as the split table: same label
  operator (`endpoint_cumulative_return`, h=9, ±3.0 bps), same invalidation
  flags (including `invalid_cross_split` against period boundaries), same
  window validity rules (per ticker, per split=period, per trading day; no
  lookback across any boundary; day-start warmup rows ineligible), same
  builders (`windows.build_window_dataset` and the domain modules hashed by
  `feature_rebuild_code_sha256`). No new mechanism code; only new boundary
  inputs.
- Because h=9 bars (45 min) and window 20 both live inside one trading day,
  day-aligned period boundaries cannot be crossed by any label horizon or
  window; the frozen invalidation flags assert this rather than assume it.
- Per-period disclosure: period i's training rows include rows scored as
  period i-1 readout rows and the official validation rows scored once in
  Stage 03. This is inherent to walk-forward training contact and is recorded
  in the decision record; within every period, all training rows strictly
  precede all scored rows, and no scored row of any period is ever used to
  tune, stop, threshold, calibrate, or select anything.

## 6. Refit Recipe (D1/D2 Mechanism Inherited, Frozen)

Per period x model row x seed, V2.1 refits with the exact mechanism-frozen
recipe of D1/D2 as implemented in Stage 03 §5 — frozen mechanism, re-derived
stopping point, full rows:

- Refit rows: ALL eligible training rows of the period (no cap); scored rows:
  ALL eligible rows of the period (no cap, natural label distribution).
- LightGBM rows: effective `n_estimators` resolved by early stopping on a
  chronological tail carved from the refit rows only
  (`early_stopping_validation_source=inner_train_chronological_tail`,
  fraction 0.2, minimum 128 fit-subset rows, minimum 128 tail rows,
  `early_stopping_rounds=25`). Scored period rows are never the `eval_set`.
- Torch rows (tcn, standard_dlinear, ms_dlinear_tcn): early stopping on the
  inner-train chronological tail (fraction 0.2, minimums 128/128,
  `early_stopping_patience=8`, maximum 64 epochs, best-epoch restoration).
  Scored period rows never participate in epoch selection.
- Class weights recomputed on the refit fit-subset rows (refit rows minus the
  early-stopping tail), never on scored rows.
- Preprocessing statistics fit per period on that period's training rows
  only, then applied to that period's scored rows.
- Seeds: `[101, 202]`, the frozen V2 seed policy. Per-refit
  `best_iteration`/`best_epoch`, tail-split fallback reasons, and
  train/tail/eval sample-id hashes are recorded in the readout artifacts and
  `refit_records`.
- The planned config carries `lightgbm_training_defaults` and
  `probe_training_defaults.torch` blocks as byte-equal copies of the frozen
  Stage 02/03 values; the V2.1 config contract test asserts the equality so
  the refit mechanism cannot drift.

Non-comparability declarations (inherited and extended):

- Stage 02 absolute metrics (stylized equal-allocation subsamples) are not
  comparable to V2.1 absolute metrics (natural distribution; Zadrozny 2004).
- Stage 03 absolute metrics and V2.1 absolute metrics are computed on
  different periods and different training-row regimes; per-period same-row
  deltas against the section 7 baselines are the supported comparison unit,
  not absolute levels across stages.

Feasibility clause (frozen before execution): the notebook pre-flight cell
estimates materialized float32 tensor bytes for the LARGEST period (the final
period's training side plus its scored side, `rows x window_size x
n_features x 4` per side, upper bound from the rebuilt event counts) and
compares against the predeclared `max_materialized_train_bytes` cap (planned
default: the Stage 03 value `2000000000`) BEFORE any scoring event. If
infeasible, the run aborts with zero scoring events; the config is amended to
the predeclared fallback sample policy — the same
`deterministic_even_stride_by_ticker_label` method with a raised cap declared
in config — and a fresh run starts. The sample policy is never changed after
any scoring event has occurred.

## 7. Model Roster And Parameter Provenance (Frozen, Zero New HPO)

The comparison table contains exactly these rows. No row may be added,
dropped, or re-parameterized after sign-off; every hyperparameter is a
verbatim copy from a named frozen artifact. There is no fallback candidate in
V2.1 and no substitution rule: a row that fails mechanically is reported as
failed (`fit_status`, `error_message`), never replaced.

Registry baseline rows (fit on each period's refit fit-subset labels only;
scored on identical rows; baseline scoring is required context, not a scoring
event — Stage 03 precedent):

| table_row_id | source | notes |
|---|---|---|
| `stratified_dummy_train_prior` | Stage 00 baseline registry | the "Dummy" row of Ian's table; seeded with the trial seed |
| `majority_train_prior` | Stage 00 baseline registry | context row |
| `constant_up` | Stage 00 baseline registry | context row |
| `constant_down` | Stage 00 baseline registry | context row |

Model rows (fitted; each period x row x seed is one guarded scoring event):

| table_row_id | family | parameter source (verbatim) |
|---|---|---|
| `tcn_frozen_primary` | `tcn` | `03_decision_record.json → primary_candidate.hpo_profile_params` (the V2 frozen primary: `tcn_p01`, `channels [16,16]`, `kernel_size 2`, `dropout 0.0`, `learning_rate 0.001`, `weight_decay 0.0001`; candidate input `price_volume_time_w20`). This is "the current model" of Ian's request and the ONLY judged row (section 8). |
| `lightgbm_family_best` | `lightgbm` | `02_best_params_by_family.json → best_params_by_family["lightgbm"]` |
| `standard_dlinear_family_best` | `standard_dlinear` | `02_best_params_by_family.json → best_params_by_family["standard_dlinear"]` |
| `ms_dlinear_tcn_family_best` | `ms_dlinear_tcn` | `02_best_params_by_family.json → best_params_by_family["ms_dlinear_tcn"]` |

Provenance facts about `02_best_params_by_family.json` (verified against the
Stage 02 runner): each family record is the best COMPLETED profile of that
family ranked by the frozen keys
(`lcb_delta_macro_f1_vs_stratified_dummy_train_prior` desc, then
`mean_delta_macro_f1_vs_stratified_dummy_train_prior` desc, then
`mean_macro_f1` desc) and carries its own `candidate_id`, `feature_set`,
`window_size`, `hpo_profile_id`, and `hpo_profile_params`. All four families
were enabled in the frozen Stage 02 run; the presence and content of all four
records are verified mechanically when the resolved roster is copied into
section 16 — a missing family record blocks sign-off completion (no
substitution rule exists).

Candidate-input policy (OD-C, must be resolved at sign-off):

- OPTION A (default): each family row runs on the candidate input recorded
  inside its own `best_params_by_family` record (its own feature set and
  window). Honesty cost: rows may differ in feature set as well as
  architecture; the comparison table therefore always carries `candidate_id`,
  `feature_set`, and `window_size` columns, and any cross-row sentence must
  name both differences.
- OPTION B (alternative, closer to a literal "same setting" reading of Ian's
  request and his 2026-05-29 "rerun the other baselines for a fair
  comparison"): pin ALL model rows to the frozen primary's candidate input
  `price_volume_time_w20`, and resolve each family's parameters as that
  family's best completed profile ON that candidate input from the frozen
  `02_hpo_summary.csv`, ranked by the same frozen keys. Also zero new HPO;
  the resolution is deterministic from a frozen artifact.

The resolved option, and under it each row's resolved `candidate_id` +
`hpo_profile_id` + `hpo_profile_params` (read mechanically from the frozen
artifacts), are echoed in section 16, the config, and
`v2_1_decision_record.json` before execution.

Ablation-variant rows (OD-D, must be resolved at sign-off): default —
EXCLUDED. The Stage 04 ablation arm already answers the ingredient question
on train-inner folds at zero scoring cost; adding the four architectural
controls here would double the guarded scoring events without a predeclared
question they answer. If the user (or Ian) opts them in, the roster above is
extended with the four Stage 04 control rows (parameters per Stage 04
protocol OD3, verbatim), the budget formula in section 10 is updated BEFORE
sign-off, and the criteria of section 8 still bind ONLY the
`tcn_frozen_primary` row.

Scoring-event budget (frozen formula):

```text
guarded_scoring_events = k periods x 4 model rows x 2 seeds
  k=3 -> 24 events; k=2 -> 16 events
  (+ k x 4 x 2 additional events only if OD-D opts the ablation rows in)
coverage_probe -> 1 metadata contact event (non-scoring)
official_validation_scoring_events -> 0
```

## 8. Predeclared Stability Criteria (Frozen)

The criteria bind ONLY the `tcn_frozen_primary` row. All other rows are
comparison evidence: they are never judged, never ranked, and never feed any
selection. Whatever the table shows — including another row outperforming the
primary in any or all periods — the V2 frozen selection is unchanged and no
winner is declared.

Definitions, per period p and seed s, on identical rows:

```text
delta(p, s) = macro_f1(tcn_frozen_primary, p, s)
            - macro_f1(stratified_dummy_train_prior, p, s)
period_delta(p) = mean over seeds of delta(p, s)
pooled_delta(s) = macro_f1 delta computed on the union of all scored period
                  rows for seed s (candidate predictions and per-period
                  baseline predictions concatenated across periods)
pooled_delta = mean over seeds of pooled_delta(s)
```

Criteria (both must hold):

1. `positive_period_count >= 2`, where a period counts as positive when
   `period_delta(p) > 0`. With k=3 this is "at least 2 of 3"; with k=2 it is
   "both".
2. `pooled_delta > 0`.

Judged decision strings (exactly one, for any run with at least one completed
scoring event on the primary row):

```text
met_predeclared_guarded_stability_criteria
did_not_meet_predeclared_guarded_stability_criteria
```

Incomplete and zero-scoring outcomes (pre-registered, Stage 03 §7 pattern):

- A crash after the first scoring event leaves `readout_complete=false` with
  `readout_incomplete_reason`; the decision is judged on the periods/seeds
  whose scoring completed and must always be quoted with the incomplete flag.
  Completion goes through the section 10 exact-run-id resume; a fresh full
  rerun while the incomplete ledger is recoverable would repeat scoring
  events and is forbidden.
- Zero completed scoring events → decision
  `do_not_start_v2_1_mechanical_failure` with `guarded_scoring_events=0`
  (same family as the section 4 gate strings).

Outcome semantics:

- Met: the paper and the 06 record may state, with the guarded
  qualification, that the primary candidate met the predeclared guarded
  stability criteria over the executed periods. No stronger claim.
- Not met: recorded as such, reported honestly to Ian and in the paper as
  guarded evidence of instability over the contacted periods. NO retuning,
  NO model switch, NO criteria revision, NO additional periods. The only
  forward path is honest reporting plus an optional, separately
  pre-registered V2.2 design.
- Either way: per-period and per-ticker tables are reported descriptively;
  uncertainty context uses only the already-frozen trading-day block
  bootstrap (`metrics.block_bootstrap_macro_f1_delta`, blocks =
  `ticker|trading_day`, 1000 draws, seed 12345), per period and pooled; it is
  context, never a gate substitute and never a standalone significance claim.

## 9. Required Artifacts (Schema Draft)

All artifacts live in the run folder
(`/content/lst_models_results/v2_1_guarded_walkforward_readout/<run_id>/`),
are inventoried with `bytes`/`sha256`, and are backed up to
`My Drive/lst_models/results/v2_1_guarded_walkforward_readout/<run_id>/`.
Prediction dumps stay out of git (route guide §11).

```text
v2_1_coverage_probe.json        (produced by the section 5.2 probe; copied
                                 into the run folder and re-verified by hash)
v2_1_period_registry.json       (frozen period table echo + per-period
                                 covered-trading-day and eligible-row counts
                                 + truncation/drop record)
v2_1_walkforward_readout.csv    (one row per period x table row x seed,
                                 plus seed-aggregate rows)
v2_1_per_ticker_readout.csv
v2_1_period_summary.csv         (per-period seed-aggregates; criteria
                                 booleans for the primary row only)
v2_1_comparison_table.csv       (the Ian table, long format)
v2_1_same_row_baselines.csv
v2_1_predictions.csv            (REQUIRED per-row dump for all fitted model
                                 rows; rough scale: ~45k eligible rows/year
                                 x 4 rows x 2 seeds x k periods ≈ 1.1M rows
                                 at k=3; CSV on Drive with sha256, gitignored)
v2_1_decision_record.json
run_manifest.json
artifact_inventory.csv
drive_backup_manifest.json      (written and uploaded last by the save cell)
```

Draft column contracts (to be frozen verbatim against the runner constants in
the implementation bundle; Stage 03 §10 shapes extended with period and
provenance fields):

```text
WALKFORWARD_READOUT_COLUMNS ≈ [
    "table_row_id", "row_kind",            # model | registry_baseline
    "candidate_id", "feature_set", "window_size",
    "model_family", "hpo_profile_id", "params_source",
    "period_id", "period_start", "period_end_exclusive", "seed",
    "n_refit_train_samples", "n_scored_rows",
    "train_sample_id_hash", "eval_sample_id_hash",
    "macro_f1", "balanced_accuracy", "accuracy", "mcc", "roc_auc",
    "precision_down", "recall_down", "f1_down", "support_down",
    "precision_up", "recall_up", "f1_up", "support_up",
    "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior",
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason",
    "requested_device", "resolved_device", "device_fallback_reason",
    "fit_status", "error_message", "scope", "readout_tier",
]

PREDICTION_COLUMNS ≈ [
    "table_row_id", "candidate_id", "model_family", "hpo_profile_id",
    "period_id", "seed", "sample_id", "ticker", "target_timestamp",
    "trading_day", "y_true", "p_up", "y_pred", "scope", "readout_tier",
]
```

Every V2.1 output row carries `scope="guarded_walkforward_readout"` and
`readout_tier="guarded_historically_contacted"`. The V2 value
`scope="validation_only"` is never written into a V2.1 artifact.

`v2_1_decision_record.json` required fields:

```text
route, stage_name
source_stage00/01/02/03_run_id (+ superseded_stage02_run_ids)
stage04_run_id_or_ordering_override (per OD-E)
protocol_reference + protocol_sha256 + sign_off (user date, Ian msg id,
  resolved OD-A..OD-F values)
coverage_probe (artifact sha256, probe timestamp)
period_registry echo
roster echo: every table row's resolved candidate_id / hpo_profile_id /
  hpo_profile_params / params_source
predeclared_criteria echo
per-period outcome rows for the primary (period_delta, per-seed deltas)
pooled_delta + per-criterion booleans + decision
readout_complete (+ readout_incomplete_reason when false)
guarded_scoring_events + scoring_event_ledger (one entry per event:
  table_row_id, period_id, seed, n_rows, timestamp_utc; plus the
  coverage_probe entry flagged event_kind=metadata_contact)
refit_records (row, period, seed, best_iteration/best_epoch, early-stopping
  fields, tail hashes)
walkforward_training_contact_disclosure (section 5.3 sentence)
holdout_test_contact = true
holdout_contact_tier = guarded_historically_contacted
holdout_contact_authorization = this protocol + sign-off date
clean_test_claim = false
official_validation_scoring_events = 0
official_validation_used_as_training_rows = true
official_validation_for_selection = false
no_final_model_selected = true
v2_frozen_selection_unchanged = true
```

`run_manifest.json` mirrors the Stage 03 manifest shape (config/notebook
sha256, exact upstream run ids, input/output artifacts, device provenance,
repo/commit) and additionally records the same guarded-tier block as the
decision record (`holdout_test_contact=true`, tier, authorization,
`guarded_scoring_events`, `official_validation_scoring_events=0`,
`clean_test_claim=false`).

## 10. Execution Discipline

- One-shot rule: each period x model row x seed is scored exactly once, in
  ONE notebook execution (one run id). Execution order is predeclared and
  deterministic: periods chronologically, model rows in the section 7 table
  order, seeds in `[101, 202]` order.
- No quantity computed from any scored period row may influence any later
  fit, stop, threshold, calibration, parameter, period boundary, roster
  entry, or criteria value, within the run or after it.
- Every scoring event is appended to the `scoring_event_ledger`;
  `guarded_scoring_events` must equal the ledger's scoring-entry count and
  the section 7 budget formula. Registry-baseline scoring on identical rows
  is required context recorded with the readout, not a scoring event.
- Checkpoints after each completed period x model row (both seeds) to
  `My Drive/lst_models/checkpoints/v2_1_guarded_walkforward_readout/<run_id>/`
  with `checkpoint_manifest.json` (`status=incomplete`, completed units,
  pending units, resume instructions) plus partial output rows, mirroring the
  Stage 03 §11 contract. Checkpoints are recovery state, not evidence.
- Resume requires the exact `run_id` and checkpoint folder; a resumed run
  rebuilds the ledger from the partials, skips every recorded scoring event,
  and never repeats one. Resuming from a parent-folder scan is forbidden.
- Lost-runtime disclosure: if the runtime dies before any checkpoint or
  result reached Drive, the lost partial run (date, rows started) is
  disclosed in the next run's notes and in the Stage 05 budget accounting.
  Unrecorded guarded contact is a protocol breach to report, not a license to
  silently restart.
- Durable save: immediately after `run_stage(config)` returns, the notebook
  validates the required artifact list and uploads via the Drive API to the
  canonical results path, refusing upload unless the manifest records the
  guarded-tier block exactly (`holdout_contact_tier`, `clean_test_claim=false`,
  `official_validation_scoring_events=0`); `drive_backup_manifest.json` is
  written and uploaded last. Duplicate Drive folders/files under the exact
  target parent are a hard error.
- Heavy cells default off (`RUN_V2_1 = False`); the notebook prints one
  compact progress line per completed period x model row x seed.

## 11. Interfaces To V2, Stage 05, And Stage 06

- V2 unchanged: D4(a) stands; V2 claims remain validation-only; the closed
  boundary marker `2017-01-25` keeps its V2 meaning everywhere outside this
  stage. No V2 artifact, config, protocol, or test is edited by V2.1
  execution (the only V2-adjacent edits are the additive ledger/mapping rows
  below, made in Stages 05/06 under their own protocols).
- Stage 05 (S5.1 validation budget ledger): the route budget table gains a
  `readout_tier` dimension with the guarded events listed in their own tier,
  never merged with the official-validation tier:

```text
tier official_validation:    Stage 03 scoring events (2); Stage 04 new events (0)
tier guarded_walkforward:    V2.1 scoring events (8k per section 7) +
                             1 coverage_probe metadata contact
```

- Stage 05 claim register: every V2.1-derived sentence enters the register
  with the guarded qualification and a pointer to
  `v2_1_decision_record.json`.
- Stage 06: the §4 honesty section reports this protocol as the pre-registered
  guarded opening (with the V1 contact history sentence); the §5 mapping rows
  for Ian's 2026-06-04 walk-forward and comparison-table requirements point
  here; the roadmap Phase 7 exit gate's "route closed or V2.1
  pre-registration opened explicitly" is satisfied by this document.
- Paper: V2.1 results appear in their own clearly-labeled guarded subsection;
  the comparison table carries the fixed designation in its caption and a
  footnote stating the V1 contact history and the zero-new-HPO parameter
  provenance.

## 12. Scientific Risks And Protections

| Risk | Protection |
|---|---|
| Post-hoc selection among multi-model rows scored on the same periods (the table quietly becomes a second HPO) | Roster + parameters frozen verbatim from named artifacts before execution; criteria bind only the primary row; no fallback/substitution rule; forbidden ranking wording (§3); `no_final_model_selected=true`; `v2_frozen_selection_unchanged=true`. |
| Period boundaries adjusted after seeing data or results | Zero-discretion carving rule frozen in §5.1 before any contact; boundaries derived mechanically by the §5.2 probe; fill-in is the only permitted edit; entry gate 8 cross-checks probe vs config; once a scoring event occurs, boundaries are unchangeable. |
| Data coverage shorter than the nominal design | Predeclared truncation + drop rule (§5.1) with the 120-trading-day floor; k reduction recorded, never improvised; criteria constants already defined for k=2 and k=3. |
| Coverage probe itself leaking information that steers design | Probe is metadata-only (timestamps/counts), runs after the carving rule is frozen, is logged as a contact event, and runs at most once. |
| Wording drift toward clean-test claims (in the paper or in mail to Ian) | Fixed designation (§2) mandatory in every surface; extended forbidden list (§3); §14 provides pre-approved email language; 06 §4 honesty obligation; notebook/static gates check designation presence and forbidden strings. |
| Validation/holdout budget creep | One-shot rule; scoring-event ledger; budget formula frozen (§7); Stage 05 guarded tier keeps the count auditable; rows after the final boundary stay closed. |
| Seed/period multiplicity read as significance | Only two frozen seeds and ≤3 periods, all reported; uncertainty context restricted to the predeclared block bootstrap; no new significance machinery; criteria are sign/count rules, not p-values. |
| Walk-forward training contact misread as evaluation contamination | §5.3 discloses that later periods train on earlier scored rows (standard walk-forward); per-period chronology is asserted by the frozen invalidation flags; the disclosure sentence is a required decision-record field. |
| Refit regime differs from tuning regime | D1 mechanism inherited byte-equal (config contract asserts); D2 full-row policy with predeclared feasibility fallback; non-comparability declarations in §6. |
| Mechanical failure of one row biasing the table | Failed rows reported as failed with `fit_status`/`error_message`; no substitution; criteria unaffected unless the primary row itself fails (then incomplete/zero-scoring semantics of §8 apply). |
| Colab loss mid-run | Checkpoint + exact-run-id resume + lost-runtime disclosure (§10). |
| V2 static gates accidentally weakened to let the V2.1 notebook pass | V2 gates untouched; V2.1 notebook gets its own gate set (§13); the implementation task must show the V2 gates still pass unchanged. |

## 13. Follow-Up Implementation Bundle (Not Part Of This Freeze)

This protocol freezes the scientific contract. The executable surface is a
separate implementation task (its own plan document, AGENTS.md §2 gate and
placement decisions), producing in one bundle:

```text
configs/stages/v2_1_guarded_walkforward_readout.yaml
src/lst_models/stages/guarded_walkforward_readout.py   (run_stage(config))
notebooks/v2_1_guarded_walkforward_readout_colab.ipynb (+ generator script)
tests/contracts/test_v2_1_config_contract.py
tests/stages/test_v2_1_run_stage_smoke.py
tests/notebooks/test_v2_1_notebook_static.py
```

Implementation requirements already fixed by this protocol:

- Config: run-id pins (00-03 + Stage 04 per OD-E), period table echo,
  roster + params-source echo, byte-equal training-defaults blocks, criteria
  echo, scope/tier flags, forbidden-wording list, checkpoint/resume blocks.
- Runner: domain-module imports only (no cross-stage stage-module imports);
  reuse `fitting.py` refit mechanics, `windows.build_window_dataset`,
  `artifacts.require_artifacts`, and the Stage 03 checkpoint/resume helpers;
  stage module within the 700-line ratchet.
- Smoke test musts: gates fail closed (including unfilled sign-off/period
  placeholders and superseded run ids); max training `trading_day` <
  period start and scored rows inside the period for every period; exactly
  one scoring event per period x row x seed; resume never repeats a recorded
  event; decision-record/manifest guarded-tier fields present; weak metrics
  trigger nothing.
- Static gate musts: pinned full-bundle commit; runtime-path injection;
  durable-save refusal conditions; `RUN_V2_1 = False` default; fixed
  designation string present; §3 forbidden strings absent; no
  official-validation scoring patterns. V2 notebooks' existing
  holdout-forbidden gates remain untouched and green.
- The coverage probe ships as a guarded, flag-gated step of the V2.1 surface
  (default off), not as an edit to any V2 notebook.

## 14. Confirmation Points For Ian (Email-Ready)

The following bullets are pre-approved language for the confirmation email to
Ian. They may be pasted verbatim; the bracketed items are filled before
sending.

- Per your 2026-06-04 instruction, we will run the walk-forward check as a
  pre-registered, one-shot readout on the post-2017 segment. As agreed in my
  2026-06-01 note, that segment was touched by the earlier (V1) experiments,
  so all results will be labeled "guarded, historically-contacted walk-forward
  readout" rather than clean held-out test evidence, and the paper will state
  this explicitly.
- Proposed periods: three consecutive 12-month walk-forward periods starting
  right at the closed boundary — 2017-01-25 to 2018-01-25, 2018-01-25 to
  2019-01-25, and 2019-01-25 to 2020-01-25 (end-exclusive; the last period
  truncates to the verified end of our raw data, which we will confirm with a
  pre-declared, metadata-only coverage check before running). Please confirm
  three periods of 12 months, or tell us if you prefer two.
- Training per period is expanding walk-forward: each period's models train
  on all data before that period's start (original train + validation +
  earlier post-2017 months), with the same frozen labels (45-minute horizon,
  ±3 bps no-trade band), features, windows, and chronological rules as the
  registered V2 pipeline; two fixed seeds per model.
- Comparison table rows, exactly as you listed: Dummy (stratified, with
  majority/constant context rows), LightGBM, standard DLinear, TCN, and
  MS-DLinear+TCN. "The current model" is the TCN configuration that the
  registered pipeline froze before its one-shot validation readout; all other
  rows reuse their best already-tuned configurations from the same tuning
  stage. Zero new hyperparameter tuning happens on these periods.
  [If OD-C Option B is chosen, add: all rows run on the same frozen feature
  set and window as the current model, for a like-for-like architecture
  comparison.]
- Stability standard, fixed before running: the current model counts as
  "stable over time" if its macro-F1 lead over the stratified dummy is
  positive in at least two of the periods and positive pooled across all
  periods. The other table rows are comparison context only — we will not use
  these periods to re-select or re-tune any model.
- Discipline: every period x model x seed is scored exactly once; every
  scoring event is logged; period boundaries and the model list are frozen
  before execution and cannot move afterwards.
- [Optional, if you want] The ablation variants (multi-scale DLinear alone,
  etc.) currently stay in the train-inner ablation study; tell us if you also
  want them as rows in this walk-forward table.
- Timeline: once you confirm the periods and the table rows, we can execute
  within your 1-2 week experiment window and bring the table plus per-period
  results into the draft.

## 15. Evidence Basis

Internal:

- `docs/protocols/00_data_split_label_freeze_protocol.md`: split freeze (§5),
  label operator and invalidation (§6-7), window validity (§9), train-only
  preprocessing (§10), baseline registry (§11).
- `docs/protocols/02_model_hpo_train_inner_protocol.md`: family/profile
  contracts; `02_best_params_by_family.json` provenance (§3, §15).
- `docs/protocols/03_frozen_validation_readout_protocol.md`: D1/D2 refit
  mechanism (§5), one-shot ledger/checkpoint/resume discipline (§11),
  decision-string and incomplete-readout semantics (§7).
- `docs/protocols/06_ian_final_progress_record_protocol.md`: D4 freeze; the
  "guarded, historically-contacted test" obligation (§4).
- `docs/lst_models_v2_route_roadmap.md`: D4 options (b)/(c) and the explicit
  V2.1 pre-registration path (Phase 2, Phase 7, §13).
- `docs/ian_lan_requirement_extracts.md`: verbatim requirement source.

External method anchors (all already in the project knowledge base):

- Dwork et al. (2015), "The reusable holdout", Science 349(6248): adaptive
  reuse hazard behind the one-shot rule, frozen criteria, and the event
  ledger. https://arxiv.org/abs/1506.02629
- Cawley & Talbot (2010), JMLR 11: selection bias from repeated evaluation;
  why the roster is frozen and only one row is judged.
  https://jmlr.org/papers/v11/cawley10a.html
- López de Prado (2018), Advances in Financial Machine Learning: walk-forward
  evaluation mechanics and their leakage/overfitting caveats; purge/embargo
  context for boundary handling.
- Zadrozny (2004), ICML: sample-selection bias; basis for the absolute-metric
  non-comparability declarations in §6.

## 16. Sign-Off Record (fill before execution; empty = execution blocked)

```text
open_decisions:
  OD-A period_count_k: <2 | 3>            (default 3)
  OD-B period_length_months: <12 | other> (default 12)
  OD-C candidate_input_policy: <A_family_best_verbatim | B_pin_primary_input>
                                           (default A; see §7)
  OD-D ablation_rows_included: <false | true> (default false)
  OD-E stage04_ordering: <stage04_first | override_with_reason>
                                           (default stage04_first)
  OD-F criteria_accepted: <yes | revised-before-signoff>

user_sign_off:
  date: <YYYY-MM-DD>
  note: <approval wording>

coverage_probe:
  executed_utc: <timestamp>
  artifact: v2_1_coverage_probe.json
  artifact_sha256: <sha256>
  per_ticker_last_full_trading_day:
    CSCO: <date>  JPM: <date>  KO: <date>  MSFT: <date>  WMT: <date>

frozen_period_table:
  wf_p1: 2017-01-25 -> 2018-01-25 (end exclusive)
  wf_p2: 2018-01-25 -> 2019-01-25 (end exclusive)
  wf_p3: 2019-01-25 -> <filled from probe per §5.1> (or dropped per rule)

resolved_roster:
  tcn_frozen_primary: <candidate_id / hpo_profile_id / params echo>
  lightgbm_family_best: <...>
  standard_dlinear_family_best: <...>
  ms_dlinear_tcn_family_best: <...>

ian_confirmation:
  date: <YYYY-MM-DD>
  gmail_message_id: <id>
  confirmed_items: <periods / roster / guarded framing / (ablation rows)>
```

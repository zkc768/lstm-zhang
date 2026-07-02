# V2 Half-Spread Settlement Control Pre-Registration (2026-07-01)

Status: pre-registration SIGNED OFF 2026-07-01 (author authorization via
working session: run order "M4 -> M1 -> E5 -> E3 -> E4", local execution
approved). Execution note, recorded before any measurement: runs execute on
the author's local Windows machine (CPU) through the same `run_stage(config)`
entry with sha256-verified inputs — raw files verified against the Stage 00
`raw_data_manifest.json` (5/5 PASS, 2026-07-01), guarded dumps against the
frozen addenda hashes before any guarded-domain read. The Colab notebook
remains the reference execution path. This document MUST be
committed BEFORE the analysis touches any prediction dump or computes any
spread proxy on eligible rows. It is a MEASURE-ONLY re-aggregation of already
frozen artifacts plus a raw-bar-derived conditioning variable: no retraining,
no new scoring events, no reselection, no operating point. Once the first
measurement cell runs against a dump, sections 4-9 are frozen; changing any of
them afterwards requires a new dated entry in the section 12 deviation log
(the V2.1 conditional-predictability pre-registration is the structural
precedent for this document).

Scope: V2 route, disclosed diagnostic branch. This control adjudicates ONE
registered open item and nothing else. It does not change any frozen V2 or
V2.1 artifact, decision, or headline claim, and it selects no model. Whatever
the outcome, it changes only the INTERPRETATION of the activity-tercile
conditional map (limitation resolved, or limitation confirmed and sharpened);
it never upgrades or downgrades the headline same-row dummy deltas.

## 1. Designation & Scope

Fixed designation (verbatim, in every artifact header, notebook title cell,
and summary built on this analysis):

```text
half-spread settlement control (measure-only re-aggregation; no new scoring)
```

What this analysis IS: a measure-only re-slice of the frozen per-row
prediction dumps by a NEW conditioning variable — a Roll (1984) effective
half-spread proxy computed from raw 5-minute bars — compared against the
frozen +/-3.0 bps no-trade band. It answers: does the calm-bar (low-activity
tercile) concentration of the same-row macro-F1 edge sit where bid-ask bounce
is mechanically capable of producing it (half-spread comparable to or above
the band), or does it persist where bounce is mechanically too small
(half-spread well below the band)?

What this analysis is NOT: NOT a clean test, NOT a new scoring event, NOT a
selection event, NOT a tradeability analysis. No model is refit or re-scored;
the model and dummy per-row predictions are read from frozen dumps only. The
V2 frozen selection (`price_volume_time_w20` / `tcn` / `tcn_p01`) is
unchanged regardless of outcome.

Forbidden strings in every output of this analysis (verbatim): `clean test`,
`unseen holdout`, `untouched holdout`, `final model`, `best model`,
`superior`, `outperforms`, `profitable`, `tradable alpha`,
`economically profitable`, `statistically significant`, `well-calibrated`,
`out-of-sample proof`. Block-bootstrap intervals below are DESCRIPTIVE
uncertainty context, never significance tests.

## 2. Motivation — The Registered Open Item

The claims ledger (`paper/outline_and_claims.md`, LEDGER_VERSION v1.13 /
2026-06-19 header note, and open item E at lines ~320-325) registers this
control as fully OPEN until run:

> 日内 label-shuffle 哨兵对 Roll(1984) 买卖价反弹**零功效** (close[t] 同为特征分子
> features.py:28 与标签分母 labels.py:28, 反弹是真行级对齐, 置换只破坏 shuffle 不破坏
> observed; 纯反弹世界可通过该哨兵), 故 Roll 仅被 "dummy floor 跨三分位近恒定" 部分降权,
> 结算控制 (原始 5min half-spread vs 3bps band) 跑完前保持完全 open

Mechanism, stated precisely. `src/lst_models/features.py:28` sets the
most-recent-return feature `log_return = log(close[t] / close[t-1])`;
`src/lst_models/labels.py:28` sets the label return
`future_cumulative_return = close[t+9] / close[t] - 1`. The SAME transacted
print `close[t]` is the numerator of the last feature bar and the denominator
of the forward label. Under Roll (1984), `close[t]` deviates from the
efficient mid by approximately +/- one half-spread depending on trade
direction. A close printed at the ask simultaneously (a) pushes `log_return`
up and (b) pushes the forward label return down — a mechanical, row-level,
NEGATIVE feature-label coupling that any flexible classifier can exploit as
an apparent reversal edge. Because the coupling lives on the observed row
alignment itself, the within-day label-shuffle sentinel
(`artifacts/05_label_shuffle_sentinel/`) has ZERO power against it: shuffling
destroys the shuffled null, not the observed statistic; a pure-bounce world
passes that sentinel. The tercile base-rate check
(`artifacts/05_guarded_base_rates/`) down-weights Roll only partially (the
dummy floor is near-constant across terciles). This control is the registered
discriminating instrument.

Why the calm-bar map is where bounce would live: the +/-3.0 bps band removes
rows whose forward move is inside the band, and low-activity days are, by the
proxy's construction, days where few rows clear the band. On such days the
bounce displacement (about one half-spread per endpoint) is a larger fraction
of the observed returns that DO clear the band. If the half-spread is
comparable to the band, bounce alone can carry a row across it; if the
half-spread is far below the band, it cannot. Frozen context (cited, not
re-measured): the validation-era conditional map shows low-tercile delta
+0.0543 and high-tercile -0.0154 (macro-F1 0.483); the guarded-era
replication shows +0.0408 / -0.0210
(`artifacts/05_guarded_activity_tercile/README.md`, register C3.4/C4.5).

## 3. Governance Position

- Disclosed diagnostic re-aggregation. New model fit/predict events: 0.
  Official-validation scoring events: 0. No selection, no operating point.
- The validation-domain pass reads the frozen Stage 03 dump plus raw bars up
  to the closed boundary 2017-01-25 ONLY (`holdout_test_contact: false`).
- The guarded-domain pass reads the frozen V2.1 dumps plus raw bars in the
  guarded window; it inherits the V2.1 designation "guarded,
  historically-contacted walk-forward readout"
  (`holdout_contact_tier: guarded_historically_contacted`,
  `clean_test_claim: false`) and is labeled non-independent confirmation
  wherever it appears.
- The two domains are computed in separate runs, written to separate run
  folders, and NEVER pooled into one number, one table row, or one claim.
- Validation-budget-ledger contact entries (template, to be appended to the
  Stage 05 budget ledger config after the run — same shape as
  `configs/stages/05_thesis_synthesis.yaml` `budget_ledger.stages`):

```yaml
- stage_name: v2_halfspread_control
  run_id_key: halfspread_validation
  evidence_domain: official_validation
  data_segment: validation_2013_2017
  contact_type: read_frozen_artifacts_only_plus_raw_bar_reaggregation
  events_source_key: halfspread_validation
  events_field: new_scoring_events        # resolved from the run manifest; must be 0
  for_selection: false
  notes: "disclosed diagnostic re-aggregation of the frozen Stage 03 dump by a raw-bar Roll half-spread proxy; zero new fit/predict events"
- stage_name: v2_halfspread_control
  run_id_key: halfspread_guarded
  evidence_domain: guarded_walkforward
  data_segment: guarded_holdout_2017_2024
  contact_type: guarded_historically_contacted
  events_source_key: halfspread_guarded
  events_field: new_scoring_events        # resolved from the run manifest; must be 0
  for_selection: false
  notes: "same measure-only re-aggregation on the frozen V2.1 dumps; non-independent guarded context, never pooled with validation"
```

## 4. Primary Spread Proxy (frozen before any measurement)

Estimator: Roll (1984) effective half-spread from the lag-1 serial covariance
of canonical 5-minute close-to-close log returns. Chosen as PRIMARY because it
targets exactly the H2 mechanism (bounce-induced negative serial covariance in
transaction prices) named in the V2.1 pre-registration section 5, and because
the ledger open item names it verbatim ("原始 5min half-spread"). The
high-low proxy of section 6 is a named robustness alternative only.

Construction, exact:

1. Bars: the canonical 5-minute bars from the frozen 1min->5min recipe
   (`configs/lst_models_data.yaml`; Stage 00 protocol sections 3-4). Sessions
   09:30-15:55 bar labels, per ticker.
2. Within-day returns: for each `(ticker, trading_day)`,
   `r_i = ln(close_i / close_{i-1})` over consecutive bars of that day (the
   day's first bar has no return; overnight gaps never enter). This matches
   the day-grouped `log_return` convention of `features.py`.
3. Lag-1 pairs: within each day, the pairs `(a, b) = (r_i, r_{i-1})` for
   consecutive within-day returns. Pairs never span days.
4. Estimation window for day `d` of ticker `k`: pool the pairs of the
   trailing `roll_window_days = 21` trading days of ticker `k` that END AT
   `d-1` (the day `d` itself is EXCLUDED, so the conditioning variable for a
   day never contains that day's own returns). The window may reach into the
   preceding split (train days before early validation days; validation days
   before early guarded days); it never reaches forward.
5. Autocovariance, pinned formula, over the pooled window pairs:
   `gamma_hat = ( sum(a*b) - sum(a)*sum(b)/n ) / (n - 1)` with `n` = number
   of pooled pairs.
6. Half-spread proxy:
   - if `gamma_hat < 0`: `c(k, d) = sqrt(-gamma_hat)` — the RELATIVE
     half-spread in log-return units. Note on conventions: Roll's full spread
     is `s = 2*sqrt(-gamma)`; the ledger item and the band comparison are in
     HALF-spread terms (one endpoint displacement), so `c = sqrt(-gamma)` is
     the registered quantity.
   - if `gamma_hat >= 0`: the Roll estimator is undefined for that cell. The
     day is assigned the named partition cell `roll_undefined_nonneg_autocov`
     and is NOT imputed to zero and NOT dropped. (Zero-imputation, the
     Harris-1990 convention, is listed as a robustness variant in section 6;
     it is not the primary treatment because imputing 0 would silently pour
     momentum-dominated days into the "spread far below band" cell.)
   - if `n < roll_min_pairs = 400` (about five or more full sessions):
     `insufficient_history`, its own named cell, never imputed.
7. Band ratio: `spread_band_ratio(k, d) = c(k, d) / theta` with
   `theta = 3.0 / 10000 = 3.0e-4`, the frozen no-trade band of the label
   policy `h09_bps3p0` (`no_trade_band_bps: 3.0`, `horizon_k: 9`).

Granularity note (why day-level with a trailing window, and why not
per-bar): a single day's 76 lag-1 pairs give a sampling error on `gamma_hat`
of the order of `sigma^2/sqrt(76)`, which for 5-minute large-cap returns is
roughly an order of magnitude larger than the `c^2` signal of a ~1 bp
half-spread, so a one-day window would be dominated by noise and produce
arbitrary cell assignments; pooling 21 trailing days (~1,600 pairs) brings
the error down by another factor of ~4.6 while preserving per-day
granularity in the assignment key. A per-BAR Roll estimate is not
identified at all (one bar contributes one return; the estimator needs an
ensemble of pairs), so day-level assignment from a trailing window is the
finest supported granularity; this is recorded here so the absence of a
per-bar variant is a stated design fact, not an omission.

## 5. Partition Of Eligible Rows (frozen)

Every eligible dump row `t` inherits the cell of its `(ticker, trading_day)`:

| cell id | definition |
|---|---|
| `ratio_le_0p5` | `spread_band_ratio <= 0.5` (half-spread clearly below band) |
| `ratio_0p5_to_1` | `0.5 < ratio <= 1.0` (buffer cell straddling parity) |
| `ratio_1_to_2` | `1.0 < ratio <= 2.0` |
| `ratio_gt_2` | `ratio > 2.0` (bounce alone can traverse the band) |
| `roll_undefined_nonneg_autocov` | `gamma_hat >= 0` in the window |
| `insufficient_history` | fewer than 400 pooled pairs in the window |

Coarse anchor cells (always also reported): `ratio_le_1` (= first two cells
pooled) and `ratio_gt_1` (= third and fourth cells pooled). The buffer cell
`ratio_0p5_to_1` exists because near parity (`c ~ theta`) neither hypothesis
makes a sharp prediction; the verdict anchors of section 8 deliberately skip
it. ALL cells are always reported for every readout — no cell is dropped for
being unfavorable, thin, or undefined.

## 6. Readouts (frozen; all computed measure-only from the frozen dumps)

Per DOMAIN (section 7), per model row (validation: `tcn_frozen_primary`, the
only role in the Stage 03 dump; guarded: `tcn_frozen_primary` primary, the
other three family rows as secondary context, no selection), per
`(partition_cell x seed)` plus a seed-mean row (seeds 101 and 202, the frozen
convention of the existing addenda):

- R1 `halfspread_partition_readout.csv` — over ALL eligible dump rows of the
  domain: `n_rows`, `n_days`, `up_rate`, candidate `macro_f1`, same-row dummy
  `macro_f1`, `delta_vs_dummy`, per-seed per-`(ticker, trading_day)` block
  bootstrap interval on the delta (`metrics.block_bootstrap_macro_f1_delta`,
  1000 draws, seed 12345 — descriptive only), `below_random_prior` flag
  (macro-F1 < 0.5), `thin_cell` flag (section 8 sizes).
- R2 `halfspread_low_tercile_readout.csv` — THE DISCRIMINATING TABLE: the
  same columns computed on the LOW-activity-tercile rows only, where the
  activity tercile is the frozen per-`(ticker, trading_day)`
  eligible-row-count proxy reused verbatim (`diagnostics.activity_terciles`),
  assigned per domain exactly as in the existing addenda. "Activity" remains
  an eligible-row-count (no-trade-band) proxy, NOT volume or liquidity.
- R3 `halfspread_occupancy.csv` — the two-way
  `partition_cell x activity_tercile` row- and day-count table (occupancy
  only), so the coupling between the two conditioners is visible and thin
  cells are disclosed before anyone reads a delta.
- R4 `halfspread_autocov_by_tercile.csv` — supporting H2 signature from the
  V2.1 pre-registration section 5: pooled within-day lag-1 autocovariance and
  autocorrelation of 5-minute returns per activity tercile (bars joined to
  the domain's dump days), showing whether negative short-lag serial
  correlation concentrates in the low tercile.
- R5 `halfspread_day_spread.csv` — the per-`(ticker, trading_day)` proxy
  table itself (`n_pairs`, `gamma_hat`, `halfspread`, `spread_band_ratio`,
  `cell`, plus the section 6 robustness proxy columns), so every assignment
  is auditable.
- R6 `halfspread_cs_robustness_readout.csv` — R1/R2 recomputed with the
  robustness proxy below. It has NO verdict power; it is reported as
  agreement/disagreement context only.

Robustness alternative (named, secondary): Corwin-Schultz (2012) high-low
half-spread from overlapping two-bar spans of within-day 5-minute bars,
pooled over the same trailing 21-day window: with
`beta = mean over spans of [ln(H_i/L_i)]^2 + [ln(H_{i+1}/L_{i+1})]^2`,
`gamma_cs = mean over spans of [ln(H_span/L_span)]^2` (span high/low over the
two bars), `alpha = (sqrt(2*beta) - sqrt(beta)) / (3 - 2*sqrt(2)) -
sqrt(gamma_cs / (3 - 2*sqrt(2)))`, spread `S = 2*(e^alpha - 1)/(1 + e^alpha)`
clipped at 0 when negative (the CS convention; the clipped share is
reported), half-spread `= S/2`. Zero-range bars contribute zero terms and are
counted. Named robustness variant 2: Roll with zero-imputation of
non-negative-autocovariance cells (Harris 1990), reported in R6 style if
computed; it cannot move the verdict.

## 7. Evidence Domains (frozen; never pooled)

- PRIMARY domain: official validation. Dump =
  `03_validation_predictions.csv` (Stage 03 run `20260610_133305_716174`;
  302,128 rows; seeds 101, 202; `candidate_role=primary` only). The same-row
  stratified dummy per-row predictions do not exist as a dump for this
  domain; they are obtained by the FROZEN deterministic replay already proven
  in Stage 04 (`diagnostics.reconstruct_dummy_baseline`): rebuild the
  windowed train labels through the frozen mechanism chain (Stage 00 events +
  raw bars -> features -> windows, with the rebuilt-count gate), replay
  `predict_stratified_dummy(train_labels, n_rows(seed), seed)` in dump row
  order, and accept ONLY on the dual equality gates against the frozen
  `03_same_row_baselines.csv` and `03_per_ticker_readout.csv`
  (tolerance 1e-9). Reconstruction-or-nothing: on any mismatch the
  validation-domain deltas are NOT computed and the run fails with the exact
  reason; nothing is imputed. The registered verdict of section 8 is read
  from THIS domain alone.
- SECONDARY domain: guarded walk-forward, the same measure-only
  re-aggregation of the frozen V2.1 dumps (`v2_1_predictions.csv` +
  `v2_1_baseline_predictions.csv`, run `20260618_063559_889276`), exactly as
  the existing Stage 05 addenda consumed them. It is non-independent,
  historically-contacted context (register grounding: expanding-window shared
  rows; spent-holdout second consumption). It is reported side by side,
  labeled, and never pooled with validation. If its pattern disagrees with
  the validation verdict, the disagreement is REPORTED as an open
  inconsistency; it does not overturn or rescue the validation reading.

Seed handling (frozen): the two frozen seeds 101 and 202 are read from the
dumps; per-seed rows are always reported; the seed-mean row is the headline
row of each table (mean of per-seed deltas — the same convention as the
existing addenda); the section 8 anchor conditions are evaluated PER SEED and
must hold for both seeds (a per-seed sign disagreement on any anchor is
automatic INCONCLUSIVE).

## 8. Predeclared Interpretation Rules (frozen BEFORE any run)

Anchors, evaluated on R2 (low-activity-tercile rows, validation domain,
`tcn_frozen_primary`):

- LOW anchor: cell `ratio_le_0p5` ("bounce mechanically too small").
- HIGH anchor: coarse cell `ratio_gt_1` ("bounce mechanically sufficient").

Minimum cell sizes (frozen): a readout row is `thin_cell` below
`report_min_rows = 200` rows (still reported, flagged). The verdict is
eligible only when BOTH anchors have at least `verdict_min_rows = 5000`
eligible rows PER SEED in R2. If either fine-grained anchor fails this and
the predeclared coarse fallback (LOW anchor -> `ratio_le_1`) also fails it,
the verdict is INCONCLUSIVE (insufficient occupancy) — reported as such, not
retuned.

Let `D(cell, seed)` be the R2 delta vs the same-row dummy, and let
`[lcb, ucb]` be its descriptive per-seed block-bootstrap interval.

- OUTCOME A — "consistent with bounce-domination" (H2 supported; the
  limitation is CONFIRMED and sharpened): for BOTH seeds,
  `D(low_anchor) <= 0` OR its interval contains 0, AND
  `D(high_anchor) > 0` with its interval above 0, AND the seed-mean deltas
  over the defined fine cells are non-decreasing in the ratio ordering with
  at most one adjacent inversion. A fine cell enters this monotonicity check
  only when its two-seed summed rows clear `2 * report_min_rows`; with fewer
  than three evaluable fine cells the monotonicity condition is not
  evaluable and Outcome A cannot fire (the reading is then C unless B holds).
- OUTCOME B — "calm-bar edge not explainable by bounce alone" (H2
  insufficient; the limitation is RESOLVED in the direction of genuine
  conditional structure): for BOTH seeds, `D(low_anchor) > 0` with its
  interval above 0, AND the seed-mean `D(low_anchor)` is at least half the
  seed-mean low-tercile all-rows delta (the edge survives, at comparable
  size, where bounce cannot reach).
- OUTCOME C — INCONCLUSIVE: anything else — anchor occupancy failure,
  per-seed sign disagreement on an anchor, or a pattern matching neither A
  nor B (for example: edge concentrated in `roll_undefined_nonneg_autocov`,
  or non-monotone with both anchors positive but intervals straddling 0).
  Reported as inconclusive with the exact failed conditions listed; no
  post-hoc re-partitioning.

Wording constraints on the outcome (frozen): Outcome A is reported as "the
calm-bar concentration is consistent with a Roll-type settlement artifact and
is a limitation of the conditional map" — it does NOT retract the (already
guarded) headline deltas. Outcome B is reported as "the calm-bar
concentration is not explained by the half-spread proxy" — it does NOT
upgrade any claim to clean-test or economic significance. Outcome C keeps the
current ledger wording (control open -> control run, inconclusive) verbatim
plus the occupancy facts. In all three cases the interpretation change is
confined to the tercile-map discussion (paper sections 8-9 and ledger open
item E); headline rows are untouched.

The machine verdict is emitted by `microstructure.verdict_from_readout` into
`halfspread_verdict.json` so the mapping from numbers to outcome is
mechanical, and any human deviation from it would be visible.

## 9. Out Of Scope / Constraints

No retraining, no new scoring, no reselection, no operating point, no
tradeability claim, no significance claim. The conditioning variable is a
diagnostic partition, not a feature: it is computed after the fact, is never
fed to any model, and day `d`'s own returns are excluded from its own
estimate (section 4.4) so the partition cannot mechanically encode the day
being sliced. Where a quantity requires data the dumps or bars do not carry
(true quotes, trade signs, realized volume-based liquidity), it stays out of
scope and is not proxied silently — this control measures the Roll proxy and
says so.

## 10. DATA_REQUIREMENTS — exact inputs the run needs

Nothing below exists in the local repo working tree (verified 2026-07-01: no
`*predictions*.csv` anywhere under the repo; `results/` is empty; local
`artifacts/05_*` folders hold only small derived addenda). All dumps and
upstream run folders are Drive-only and are pulled by the notebook via exact
Drive path parts / file IDs — no folder scanning.

Validation domain (PRIMARY):

| artifact | where | why |
|---|---|---|
| `03_validation_predictions.csv` (302,128 rows; columns exactly `candidate_role, candidate_id, model_family, hpo_profile_id, seed, sample_id, ticker, target_timestamp, trading_day, y_true, p_up, y_pred, scope`) | Drive `My Drive/lst_models/results/03_frozen_validation_readout/20260610_133305_716174/` | the frozen per-row candidate predictions |
| `03_same_row_baselines.csv`, `03_per_ticker_readout.csv` | same Drive run folder | dual equality gates for the dummy replay |
| `run_manifest.json`, `artifact_inventory.csv`, `03_decision_record.json` | same Drive run folder | run-id chain + entry gates |
| Stage 00 `raw_data_manifest.json`, `split_freeze.json`, `label_policy.json`, `baseline_registry.json`, `sample_event_index.csv`, `run_manifest.json`, `artifact_inventory.csv` | Drive `My Drive/lst_models/results/00_data_split_label_freeze/20260610_051705_347450/` | split boundaries, band value, train events for the label rebuild |
| Stage 01 `01_candidate_inputs.json`, `01_feature_window_search_summary.csv`, `run_manifest.json`, `artifact_inventory.csv` | Drive `My Drive/lst_models/results/01_feature_window_search/20260610_075002/` | frozen candidate feature columns / window size + rebuilt-count gate |
| raw `.txt` files for CSCO, JPM, KO, MSFT, WMT | Drive folder `154SlcH3nViUcvPXFBM-E4NPg_ybljBTG`, file IDs pinned in `configs/lst_models_data.yaml` | 5-minute bars for the spread proxy AND the train-label rebuild |

Guarded domain (SECONDARY):

| artifact | where | why |
|---|---|---|
| `v2_1_predictions.csv` (sha256 `6481f7958834b2c58cf3217ccbf7274ed25ec70cc176fd1b3955888317910300`, 569,232,348 bytes) | Drive `My Drive/lst_models/results/v2_1_guarded_walkforward_readout/20260618_063559_889276/` | frozen per-row predictions, 4 family rows x 7 periods x 2 seeds |
| `v2_1_baseline_predictions.csv` (sha256 `cd6925e1dfb0d5305b212586dfe84c2dde7d7cba244a036b3b61df7cac46fcdb`, 117,539,889 bytes) | same Drive run folder | frozen per-row per-seed stratified-dummy predictions (F10-fixed) |
| `run_manifest.json`, `artifact_inventory.csv`, `v2_1_decision_record.json` | same Drive run folder | run-id chain + entry gates |
| raw `.txt` files (as above) | as above | bars for the guarded-window spread proxy |

(The two dump sha256/byte values are copied from the frozen addenda
manifests `artifacts/05_guarded_activity_tercile/guarded_activity_tercile_manifest.json`
and `artifacts/05_label_shuffle_sentinel/label_shuffle_sentinel_manifest.json`;
the notebook re-hashes what it downloads and fails on mismatch.)

Availability note (checked before this design was frozen): per-row VALIDATION
dumps DO exist as a declared, Drive-backed Stage 03 artifact
(`03_validation_predictions.csv` is a required Stage 04/05 input consumed by
runs `20260619_082125_765984` and the Stage 05 run), so the validation domain
proceeds as PRIMARY as designed. Had it been aggregates-only, this document
would have had to flip the guarded domain to primary; it does not.

## 11. Implementation Gate

Before writing or changing code for this control, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this pre-registration
- the target notebook or module

Before writing code, the implementer MUST record a placement decision
(target_file_type, target_path, guide_sections, why_not_notebook,
why_not_utils, safety_tests). The implementation MUST preserve: Colab-first
execution; one user-facing notebook (`notebooks/v2_halfspread_control_colab.ipynb`);
sidecar config `configs/stages/v2_halfspread_control.yaml`; one
`run_stage(config)` (`src/lst_models/stages/halfspread_control.py`); pure
measurement logic in the domain module (`src/lst_models/microstructure.py`);
no stage-to-stage imports; zero new fit/predict events; the dummy-replay
equality gates for the validation domain; per-domain run manifests with the
correct contact flags (`holdout_test_contact=false` for validation;
`holdout_contact_tier=guarded_historically_contacted` for guarded);
`new_scoring_events=0` recorded in every manifest; the durable Drive
result-save cell immediately after a successful `run_stage`; artifacts saved
to `My Drive/lst_models/results/v2_halfspread_control/<run_id>/`;
`drive_backup_manifest.json` written and uploaded last with a null
self-reference size; exact-commit Colab bootstrap verified against a
full-bundle commit; notebook static-gate compatibility.

## 12. Deviation Log

(Empty at registration. Any post-first-measurement change to sections 4-9
must be recorded here as a dated entry stating what changed, why, what had
already been observed at the time of the change, and which outputs are
affected — the same discipline as the dated deviation note the ledger v1.13
records for the V2.1 conditional-predictability pre-registration. An entry
here never silently rewrites the sections above; the original text stays.)

---

Provenance: ledger open item E (`paper/outline_and_claims.md` v1.13 header
note and lines ~320-325); `docs/protocols/v2_1_conditional_predictability_preregistration.md`
(sections 5-7: H2 signatures, spread-proxy discrimination, controls);
`artifacts/05_guarded_activity_tercile/` and `artifacts/05_label_shuffle_sentinel/`
(frozen addenda manifests, input dump hashes); frozen label policy
`h09_bps3p0` (`configs/stages/v2_1_guarded_walkforward_readout.yaml`
`label_policy`); Roll 1984; Harris 1990 (zero-imputation variant, robustness
only); Corwin & Schultz 2012 (high-low proxy, robustness only); Lo &
MacKinlay 1990 (nonsynchronous-trading context).

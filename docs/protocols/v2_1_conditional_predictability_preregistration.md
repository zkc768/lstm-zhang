# V2.1 Conditional Predictability Localization Pre-Registration

Status: pre-registration, awaiting user sign-off. This document MUST be
committed BEFORE the analysis touches any prediction dump. It is a MEASURE-ONLY
re-read of already-frozen artifacts: no retraining, no new scoring events, no
reselection, and no operating point is marked. Once the first measurement cell
runs against the dumps, sections 3-7 are frozen; changing any of them
afterwards requires a new pre-registered revision recorded as such (Stage 03
precedent).

Scope: V2.1 route only. This pre-registers a localization re-read of the
guarded walk-forward evidence; it does not change any V2 or V2.1 frozen
artifact, decision, or claim, and it authorizes no new contact with the closed
segment. The authoritative source for findings and wording is
`docs/v2_1_limitation_claim_register_20260617.md`.

## 1. Designation & Scope

Fixed designation (mandatory, verbatim, in every artifact header, notebook
title cell, figure caption, and summary built on this analysis):

```text
guarded, historically-contacted walk-forward readout
```

What this analysis IS: a measure-only re-read of the frozen Stage 03
(validation, 2013-09-16 → 2017-01-25) and V2.1 (guarded holdout, 2017-01-25 →
2024-04) prediction dumps (`03_predictions.csv`, `v2_1_predictions.csv` on
Drive), to localize WHERE the weak guarded macro-F1-over-dummy edge lives and to
adjudicate whether the low-activity concentration reflects genuine conditional
structure or a microstructure/measurement artifact.

Dependency: this analysis runs under FIX-1. Every pooled quantity uses the
protocol-defined row-pooled estimand (the union of scored rows for a seed; see
register FIX-1, protocol lines 508-511), NOT the equal-weight per-period code
path at `src/lst_models/guarded_walkforward.py:959`. Where the equal-weight
number is also shown, it is labeled as such.

What this analysis is NOT: NOT a clean test, NOT an unseen holdout or untouched
holdout, NOT a selection event. NO final model is selected; the V2 frozen
selection (`price_volume_time_w20` / `tcn` / `tcn_p01`) is unchanged. The
LightGBM row is numerically highest in the guarded readout, but it is comparison
evidence only and crowns no winner.

Forbidden strings in every output of this analysis (verbatim): `clean test`,
`unseen holdout`, `untouched holdout`, `final model selected`,
`TCN outperforms all baselines`, `TCN is superior to LightGBM`, `TCN is SOTA`,
`TCN is best`, `economically profitable`, `tradable alpha`, `profitable`, and
`statistically significant` (the last only permitted if a valid test is added
and its assumptions are defended). The low-activity edge is NOT framed as a
feature or innovation; it is reported as a limitation / diagnostic.

Mandatory qualification: every quantitative claim carries the guarded
qualification, and the V1 contact history is restated wherever results first
appear. Allowed framing: guarded / historically-contacted walk-forward readout;
same-row dummy baseline; predeclared primary candidate met the guarded stability
criteria; LightGBM numerically highest, no final model selected; leakage control
is verified; a weak but reproducible edge of the expected size.

## 2. Motivation & Literature Tension

The verified guarded readout shows a weak same-row edge over a stratified dummy
(Dummy mean macro-F1 0.5008; TCN +0.0054, 5/7 periods; LightGBM +0.0069, 5/7,
numerically highest; standard DLinear +0.0042, 4/7; MS-DLinear+TCN +0.0055,
4/7). Our F1 diagnostic further shows this edge does not sit uniformly across
states: on the validation segment it concentrates in the LOW activity tercile
(Δ ≈ +0.054; net-pooled share ≈ 0.95, gross-positive share ≈ 0.71) and falls
BELOW the balanced random prior (≈ 0.498) on the HIGH activity tercile
(Δ ≈ −0.015; model macro-F1 ≈ 0.483).

This runs OPPOSITE to the dominant economic-predictability literature, which
places short-horizon predictability in high-activity / high-volatility states
(Heston, Korajczyk & Sadka 2010; Henkel, Martin & Nardari 2011). Either outcome
is informative: a confirmed calm-bar concentration that is robust to controls is
a genuine conditional-structure finding worth reporting, while a calm-bar
concentration that collapses under the section 6 controls points to a
measurement artifact. Both are reported.

Definition (load-bearing, stated to forestall the standard misreading):
"activity" is the per-`(ticker, trading_day)` eligible-ROW-COUNT proxy
(`diagnostics.py:113-126`), a no-trade-band proxy. The ±3.0 bps band drops
near-flat samples, so a low count tracks LOW-movement / calm days, NOT low
volume or low liquidity (the universe is five large-cap survivors). The dump
carries no volume or liquidity field.

## 3. Frozen Slice Plan (decided BEFORE touching dumps)

Committed before any dump contact; ALL slices are reported (no cherry-picking,
no slice dropped for being unfavorable):

- Slice axes: `activity_tercile`, `time_of_day_hour`, `calendar_quarter`, and a
  dump-derived realized-dispersion tercile IF computable from existing dump
  fields. If realized dispersion is NOT derivable from the dump fields, it is
  recorded as a deferred future test, not silently omitted and not back-filled by
  re-scoring.
- Model families: all four (`tcn_frozen_primary`, `lightgbm_family_best`,
  `standard_dlinear_family_best`, `ms_dlinear_tcn_family_best`).
- Eras: validation (Stage 03) and the guarded holdout (V2.1), reported side by
  side and never merged into one pooled level (different eras; register context).

Blind-spot closure: this analysis adds `activity_tercile` to the LOO sign-flip
axes. The verified F1 blind spot is that `loo_sign_flip_axes` at
`configs/stages/04_diagnostics_ablation.yaml:102` lists only
`[ticker, seed, calendar_year]`, so `activity_tercile` (present as a slice axis
on line 101) currently produces an empty `concentration_loo_sign_flips`. Closing
it is a measurement-side change only; no re-scoring is implied.

## 4. Metrics & Uncertainty

For every slice cell, computed measure-only on the frozen dump rows:

- Per-slice macro-F1 delta versus the same-row stratified dummy
  (`stratified_dummy_train_prior`) on identical rows.
- Leave-one-out pooled delta with sign-flip across each axis in section 3,
  including `activity_tercile`.
- Per-`(ticker, trading_day)` block bootstrap CI
  (`metrics.block_bootstrap_macro_f1_delta`, blocks = `ticker|trading_day`, 1000
  draws, seed 12345), per slice and pooled. This is uncertainty context, never a
  gate and never a standalone significance claim.
- Both the net-pooled and the gross-positive share of the pooled delta are
  reported for every pooled cell (the F1 LOW tercile already shows these diverge:
  net ≈ 0.95 vs gross ≈ 0.71).

All pooled deltas use the FIX-1 row-pooled estimand. The validation pooled delta
under that estimand is +0.0169; the like-for-like equal-weight code path yields
≈ +0.012 per FIX-1 and is shown only as a labeled comparison.

## 5. Two Pre-Stated Competing Hypotheses

- H1 (genuine conditional structure): the edge truly lives in calm / low-activity
  bars — directional predictability is real but concentrated where price movement
  is smallest.
- H2 (microstructure / measurement artifact): the apparent calm-bar edge is
  spurious short-horizon serial structure of the kind predicted by Roll (1984)
  bid-ask bounce and Lo & MacKinlay (1990) nonsynchronous trading, which is
  concentrated in low-movement / illiquid-print bars and decays or reverses on
  high-movement bars — consistent with the below-random HIGH tercile we observe.

Discrimination signatures, pre-stated:

- Favors H2: a negative short-lag (one-bar) return autocorrelation concentrated in
  the LOW activity / low-movement tercile; and a monotone relationship between the
  per-slice delta and a Roll-style effective-spread proxy IF that proxy is
  derivable from existing dump fields. If a Roll-style effective-spread proxy is
  NOT derivable from the dump fields, this is declared a limitation and recorded as
  a named future test (re-scoring or richer fields required), not fabricated.
- Favors H1: a calm-bar edge that persists with the expected sign after the
  section 6 sentinel and label-shuffle controls and is NOT explained by short-lag
  autocorrelation sign or the spread proxy where computable.

## 6. Controls

Two pre-stated negative controls, both expected to collapse the pooled delta
toward 0 if the pipeline is measuring what we think:

- A 1-bar / time-reversed sentinel: re-reading the frozen dumps under a
  time-reversed or one-bar-shifted alignment should drive the delta toward 0; a
  surviving delta flags a measurement artifact.
- A within-day label shuffle: permuting `y_true` within each `(ticker,
  trading_day)` block should drive the delta toward 0; a surviving delta flags a
  leakage or alignment problem. (Register F11 STANDS: 4/4 independent leak-hunt
  attempts found no leak; this control is a confirmatory guard, not an expectation
  of failure.)

## 7. Decision & Interpretation Rules (pre-stated)

- "Edge localized to calm bars" counts as supported when the LOW activity tercile
  delta stays positive with the expected sign under the FIX-1 row-pooled estimand,
  the block-bootstrap CI, the LOO sign-flip on `activity_tercile`, AND both
  section 6 controls collapse toward 0.
- H2 is supported over H1 when the calm-bar concentration co-occurs with the H2
  signatures of section 5 (short-lag autocorrelation sign; spread-proxy
  monotonicity where computable) and/or the HIGH-tercile below-random behavior
  persists.
- A confirmed H2 reading is reported as a LIMITATION on the headline guarded edge,
  NOT as failure: it sharpens, rather than negates, the guarded readout.
- NO model is selected, NO operating point is marked, and the V2 frozen selection
  is unchanged regardless of outcome.

## 8. Out of Scope / Constraints

No retraining, no new scoring events, no holdout reselection. No tradeability or
clean-test claim is made (`profitable`, `tradable alpha`, and `economically
profitable` stay forbidden; macro-F1 is not economic value). Guarded labeling
stays visible in every artifact header, caption, and summary. Where a quantity
requires fields the dumps do not carry (realized-dispersion tercile, Roll-style
spread proxy), it is declared a deferred future test, never improvised from
re-scoring.

---

Provenance: depends on FIX-1 (use the protocol-defined row-pooled estimand, not
the equal-weight code path). Sources: `docs/v2_1_limitation_claim_register_20260617.md`
(authoritative findings and wording; F1 concentration, F11 leak-hunt, FIX-1) and
the conditional-regime / microstructure literature (Heston-Korajczyk-Sadka 2010;
Henkel-Martin-Nardari 2011; Roll 1984; Lo & MacKinlay 1990).

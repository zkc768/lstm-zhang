# Red-line audit — are the paper's red lines data-faithful, or over-conservative?

Audit date: 2026-06-27. Question audited: *is the paper's "too conservative" feel
caused by red lines that are stricter than the experimental data requires?*

## Method
For each red line / canonical claim: trace to its source artifact + field, read the
actual value, classify as **CONFIRMED** (data demands exactly this), **OVER-CONSERVATIVE**
(data would support a stronger / less-hedged statement), **WRONG/TOO-LAX** (red line
misstates data or paper claims more than data supports), or **UNVERIFIABLE** (source
not local). All sources are local; nothing was Drive-gated.

## Headline answer
**The red lines are not the problem.** Every data-grounded red line is CONFIRMED exact
against source artifacts, and most are *machine-emitted by the synthesis pipeline itself*
(`05_thesis_synthesis_report.json::kb_wording_guardrails` and
`05_claim_boundary_register.csv`) — they are not editorial over-caution. The conservatism
reflects a genuinely near-null result (guarded pooled +0.636pp with PBO 0.514; LightGBM, a
tree, numerically beats the neural primary; high-activity tercile robustly below random).
Relaxing the red lines would be overclaiming, and a reviewer checking Fig 2 / the PBO would catch it.

**But two real findings give legitimate room without touching a red line:**
1. The draft **under-states ~4 honest robustness results** (below). That, plus the
   over-hedged prose the v2 draft already fixed, is where the legitimate "more positive" lives.
2. One **provenance fork** ("historically contacted") needs your ratification.

---

## Verdict table (data-grounded red lines)

| # | Red line / number | Source artifact : value | Verdict |
|---|---|---|---|
| 1 | Validation TCN macro-F1 0.5170 | `05_selective_autopsy.csv` all/seed_mean = 0.51703 | CONFIRMED |
| 2 | +1.69pp vs stratified dummy | `05_selective_autopsy.csv` all/seed_mean delta = 0.016885 | CONFIRMED |
| 3 | Worse-seed +1.63pp | `05_selective_autopsy.csv` all/101 = 0.016252 (min seed) | CONFIRMED |
| 4 | Dummy floor ≈ 0.499–0.501 | `04_same_row_dummy_baselines.csv` 0.50139 (s101) / 0.49889 (s202) | CONFIRMED |
| 5 | Majority 0.329 | `04_same_row_dummy_baselines.csv` 0.32869 | CONFIRMED |
| 6 | CSCO +2.21 / JPM +1.00 per-ticker | `03_..._per_ticker_readout.csv` CSCO mean +2.208 / JPM mean +1.001 | CONFIRMED |
| 7 | Per-ticker 5/5 positive; JPM weakest | `03_...` all 10 rows positive; JPM smallest | CONFIRMED |
| 8 | Control spread 0.66pp, 4 rows (2 last-step), not full-family | `13_train_inner_model_metric_comparison.csv` 0.51148−0.50492 = 0.656pp | CONFIRMED |
| 9 | Guarded +0.636 row-pooled / +0.550 eq-weight | `05_estimand_contrast.csv` 0.006362 / 0.005495 | CONFIRMED |
| 10 | 5/7 positive (descriptive), bar = ≥2/7 + pooled>0 (≈94% coin) | report `positive_period_count`=5; binom P(≥2/7\|0.5)=0.9375 | CONFIRMED |
| 11 | 56 guarded scoring events | report `scoring_event_budget.v2_1`=56 (total 58) | CONFIRMED |
| 12 | PBO 0.514; only TCN primary period-LCB clears zero (+0.047pp); min family LCB −0.46pp | `05_multiplicity_discount.csv` pbo 0.51429; tcn LCB +0.000470; std-dlinear −0.004645 | CONFIRMED |
| 13 | LightGBM numerically highest (+0.695pp) but no winner | `05_multiplicity_discount.csv` lightgbm mean 0.006950 (top) | CONFIRMED |
| 14 | Terciles (val) low +5.43 / mid +1.91 / high −1.54; high macro-F1 0.483 | `05_selective_autopsy.csv` 0.054336 / 0.019120 / −0.015392; high 0.48303 | CONFIRMED |
| 15 | Terciles (guarded) low +4.08 / mid +0.56 / high −2.10; high macro-F1 0.480 | `fig4_tercile_ci.csv` 4.083 / 0.558 / −2.104 | CONFIRMED |
| 16 | High tercile robustly below random prior (limitation) | `fig4_tercile_ci.csv` high CI entirely < 0 | CONFIRMED |
| 17 | ECE ≈ 0.010, Brier resolution ≈ 4.7e-4 (not "well-calibrated") | `08_validation_calibration_summary.csv` seed_mean eq-mass-10 ece 0.010247, resolution 0.000471 | CONFIRMED |
| 18 | e-AURC 0.330, AUGRC 0.237 | `05_selective_autopsy.csv` 0.330219 / 0.236872 | CONFIRMED |
| 19 | Guarded sign survives all LOO drops | `05_loo_robustness.csv` all rows sign_after_drop=True | CONFIRMED |
| 20 | Three evidence domains never fused | report `evidence_domains` (3); `05_estimand_contrast.csv` warns weight-units not cross-comparable | CONFIRMED |
| 21 | No final model selected; clean_test=false; holdout_contact=false | report `no_final_model_selected`/`clean_test_claim`/`holdout_test_contact` all aligned | CONFIRMED |
| 22 | Activity = eligible-row-count proxy, not volume/liquidity | `05_claim_boundary_register.csv` L1 | CONFIRMED |
| 23 | Calm-bar edge = limitation, not feature | report `kb_wording_guardrails`; register L1 is_limitation=True | CONFIRMED |
| 24 | macro-F1 ≠ economic/tradeable | register L2 | CONFIRMED |
| 25 | PBO/LCB descriptive, not significance test | `05_multiplicity_discount.csv` note; report `descriptive_only`=true throughout | CONFIRMED |
| 26 | Don't compare macro-F1 to 0.50–0.56 accuracy literature | `05_expectation_calibration.csv` rows flagged "qualitative context only, not a threshold" | CONFIRMED |

**OVER-CONSERVATIVE count: 0.** No red line forbids a claim the data would support.
**WRONG/TOO-LAX count: 0** on the numbers. (One provenance reason is stale — see below.)

---

## Finding A — four honest robustness results the draft UNDER-states
These are real, in-data, and currently buried under hedging. They stay **descriptive**
(within-sampling block bootstrap; they sit under the PBO 0.514 multiplicity discount and do
not establish significance), but they can be foregrounded without crossing any red line.

1. **Validation pooled margin clears its block-bootstrap interval.** +1.69pp, 95% CI
   **[1.21, 2.19] excludes zero** (`fig2_bootstrap_ci.csv` panel A); low & mid terciles also
   clear their MDE (`05_selective_autopsy.csv` delta_clears_mde=True). The draft buries this
   under "n=2 too small for variance" — both are true, but the per-trading-day bootstrap (846
   days) is a legitimate uncertainty estimate that the headline ignores.
2. **Guarded pooled delta clears its block-bootstrap interval.** +0.636pp, 95% CI
   **[0.24, 1.02] excludes zero** (`fig2_bootstrap_ci.csv` pooled) — even though 6/7 individual
   period CIs include zero. The draft emphasizes the weak 6/7 and omits that the pooled CI clears zero.
3. **Sign survives every leave-one-out drop** — all 7 periods and all 5 tickers, worst-case
   +0.44pp (drop wf_p2) / +0.41pp (drop CSCO) (`05_loo_robustness.csv`). The guarded edge is
   not carried by a single period or ticker.
4. **Leakage negative controls pass.** Within-day label-shuffle + time-reversed sentinels
   collapse the same-row delta toward zero (`claim_boundary_register.csv` C2;
   `05_label_shuffle_sentinel.csv`). The edge is not a within-day-leakage artifact — a passed
   control currently stated defensively rather than as the strength it is.

**Caveat:** keep all four "descriptive." They are within-sampling resampling, do not address
between-period regime clustering, and remain under the PBO≈0.5 multiplicity discount. Roll(1984)
bid-ask-bounce remains an open confound. So: foreground them, do not upgrade them to significance.

---

## Finding B — provenance fork on "historically contacted" (needs your ratification)
- **Artifacts say:** the guarded readout is guarded **because the V1 route historically
  contacted the post-2017 segment** (`05_claim_boundary_register.csv` C4/C7/L4; report
  `kb`; upstream `v2_1_decision_record.json`).
- **Claims ledger v1.13 top-note (2026-06-26, author-confirmed, later) RETRACTS this:** post-2017
  was never contacted before the V2.1 walk-forward. It re-grounds "guarded" on (1) non-independence
  (expanding-window row sharing, fixed 5-ticker survivor universe, no final model) + (2) spent-holdout
  reuse within V2 (Dwork 2015).
- **Live paper (v1) is stale:** `paper/main.tex:58,63` still say "historically contacted."
  The new skill draft (v2) already dropped it — so v2 is the more current version here.

**This does not change the conservatism level** — guarded / not-a-clean-test / not-unseen holds
under *either* reason, so it is not a relaxation lever. It is a correctness + provenance issue:
the frozen artifacts encode a reason the author has retracted.

Decision needed from you:
1. Confirm the v1.13 re-base is correct (author-only knowledge).
2. If yes: the pipeline artifacts (`claim_boundary_register` C4/C7/L4, kb guardrail,
   `v2_1_decision_record.json`) carry a stale reason and should be annotated/corrected;
   the live `paper/` must drop "historically contacted" to match v2.

---

## Bottom line
- The red lines are **data-faithful and load-bearing**; the "too conservative" feel comes
  from the result being genuinely near-null, not from over-strict red lines.
- The legitimate way to read "more positive" is: (a) the prose-confidence the v2 draft already
  applied, plus (b) foregrounding the four under-stated robustness results above — all honest, all
  descriptive, none crossing a red line.
- One provenance item ("historically contacted") needs your ratification and propagation.

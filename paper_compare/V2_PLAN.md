# V2 transition plan — materials, results, framework, writing

Purpose: a single plan for fully adopting the v2 (skill-based) draft as the canonical
paper, with confident-but-honest framing, while keeping the entire evidence layer the 60
prior rounds produced.

## 0. What carries over vs what changes
- **Frozen / reused (the evidence layer):** claims ledger `outline_and_claims.md` (v1.13),
  all Stage 05 artifacts + sha-verified packets, figures, tables, `references.bib`, the
  three evidence domains, the red lines, the adversarial-review conclusions. **Do not
  re-litigate these.**
- **Replaced (the prose layer):** abstract + all 9 section bodies, rewritten in v2 for
  confidence-on-method + descriptive-honesty-on-numbers.
- Net: v2 = same science, better writing.

## 1. Materials (the source set the paper draws from)
- **Fact source of truth:** `paper/outline_and_claims.md` (claims ledger v1.13).
- **Contracts:** Doc A (format/figures), Doc B (narrative), anti-AI style guide.
- **Evidence artifacts (all local, sha-verified):**
  - `artifacts/05_thesis_synthesis/20260619_090454_562658/` — report, selective_autopsy,
    multiplicity_discount, estimand_contrast, loo_robustness, expectation_calibration,
    validation_budget_ledger, claim_boundary_register.
  - `artifacts/05_row_pooled_loo/`, `05_row_pooled_multiplicity/`,
    `05_guarded_activity_tercile/`, `05_guarded_base_rates/`, `05_label_shuffle_sentinel/`.
  - `artifacts/05_fig2_uncertainty/` — bootstrap CIs for Fig 2 / Fig 4.
  - `artifacts/ian_email_packet_20260611/tables/01–13` — seed summary, per-ticker, dummy
    baselines, ablation, calibration, selective, robustness slices, train-inner comparison.
- **Figures (vector PDFs):** fig_validation_deltas, fig_tercile_map, fig_risk_coverage,
  fig_protocol_timeline.
- **Writing method:** `.claude/skills/ml-paper-writing/` (narrative, abstract, Gopen-Swan,
  Lipton word choice) — overridden by the red lines on any conflict.
- **Open item before submission:** `references.bib` needs publisher-page verification
  (year/volume/DOI) — not blocking for drafting.

## 2. Results to use, by evidence domain (never fused)
- **Domain V — official validation (n=2 seeds), "on the frozen validation split":**
  TCN macro-F1 0.5170±0.0009; +1.69pp vs stratified dummy (1.63pp worst seed); +18.8pp vs
  majority; 5/5 tickers positive (CSCO +2.21 / JPM +1.00, JPM CI crosses zero); pooled CI
  [1.21,2.19]; terciles low +5.43 / mid +1.91 / high −1.54 (high macro-F1 0.483 < ~0.498);
  ECE ≈0.010 with resolution ≈4.7e-4; e-AURC 0.330, AUGRC 0.237.
- **Domain control — train-inner:** 4 control rows (2 last-step degenerate) spread 0.66pp;
  context only, NOT apples-to-apples with the +1.69pp full-family margin (ledger C2.3 sentence).
- **Domain G — guarded non-independent walk-forward:** row-pooled +0.636pp (binding) /
  equal-weight +0.550pp; 5/7 positive (descriptive); bar = ≥2/7 positive AND pooled>0 (~94%
  coin); 56 events; PBO 0.514; only TCN primary period-LCB clears zero (+0.047pp), LightGBM
  numerically highest (+0.726pp) but LCB negative; LOO sign survives all (worst +0.538/+0.514pp);
  terciles low +4.08 / mid +0.56 / high −2.10; sentinels pass.
- **The 8 mined characteristics:** see `EXPERIMENT_ANALYSIS.md` (estimand sensitivity,
  cross-era gradient, floor scale, per-ticker heterogeneity, calibration paradox,
  pre-registration survives multiplicity, small-but-stable sign, regime-break negatives).

## 3. Paper framework (8-page ICAIF, the v2 section plan)
| § | Section | Budget | Claims it carries |
|---|---|---|---|
| — | Abstract | — | Farquhar 5-sentence: protocol-first, near-null honest close |
| 1 | Introduction | 0.9pg | Overstatement problem → protocol gap → what we do → contributions C1/C2/C3 → near-null honesty |
| 2 | Related Work | 0.6pg | Six methodological threads (leakage/chronological validation; backtest overfitting; model families; selective/calibration; multiplicity; microstructure) |
| 3 | Task & Evaluation Protocol | 1.0pg | **The contribution.** Freeze label/band/splits/roster/budget; same-row dummy; counted budget. Most declarative section. |
| 4 | Models | 0.5pg | Roster drives the protocol; TCN primary; LightGBM fallback unused; no winner |
| 5 | Experimental Setup | 0.5pg | Data facts; n=2 honesty; no model selection |
| 6 | Validation Results | 1.0pg | Domain V readout; small-but-stable sign |
| 7 | Guarded Walk-Forward | 0.7pg | Domain G; pre-registration survives multiplicity; non-independent + spent-holdout |
| 8 | Diagnostics | 1.0pg | Calibration paradox; activity-tercile conditional boundary; cross-era recurrence |
| 9 | Limitations & Conclusion | 0.7pg | Honest near-null framing; positive-control as the named next step |

The narrative spine (one sentence): *a small, stable, well-characterized, deliberately
un-cashed edge — the contribution is the evaluation discipline, not a model.*

## 4. How to write it (methodology)
- Evidence layer frozen; prose layer follows the skill's narrative + Lipton de-hedging.
- Confidence goes on the **method** (freeze/force/count/map; protocol survives multiplicity).
- Honesty stays on the **numbers**: each caveat once, plainly; descriptive framing for CIs/PBO;
  three domains never fused; red lines hold; anti-AI grep gates pass; "novel" ≤ 1.
- Every number traces to a ledger/artifact field. No fabricated citations.

## 5. Transition steps (proposed)
1. **Regression check (safeguard):** diff v1 → v2 to confirm v2 did not drop any hard-won
   defensive content from the 60 rounds (the C2.3 sentence, caption locks, the budget-ledger
   asymmetry, similarity/text-recycling defenses, reviewer-attack pre-empts). Fix any gap.
2. **Promote v2 to canonical:** make v2 the working `paper/` (keep the shared ledger/artifacts).
3. **Propagate the contact fix** (already in v2) and confirm `paper/` no longer says
   "historically contacted".
4. **Pre-submission pass:** references.bib publisher-page verification; skeleton-trace grep;
   final 8-page + anti-AI gate confirmation.

## 6. Open decisions for you
- Confirm v2 becomes the canonical base (recommended).
- Run the regression check before promoting (recommended), or promote directly?
- Any change to the narrative spine / contribution framing in §1 before we lock it?

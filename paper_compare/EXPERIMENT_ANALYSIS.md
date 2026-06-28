# Experiment-analysis mining — characteristics of the lst_models experiment

Method: the GitHub `实验分析` discipline — each characteristic is a paper-ready
`\paragraph{Title-Case Conclusion}` plus analysis prose, comparison/trend/sensitivity
focused, no bold/emph, plain paragraphs. **No-hallucination guarantee:** every number
below is copied verbatim from a named local artifact field (listed under each item); no
value is from memory. Evidence domains (V = official validation n=2, C = train-inner
control, G = guarded non-independent walk-forward) are kept separate per the red lines.

Artifacts used (all local, sha-verified packets):
`05_thesis_synthesis/20260619_090454_562658/{05_selective_autopsy,05_estimand_contrast,05_multiplicity_discount,05_loo_robustness}.csv`,
`05_fig2_uncertainty/{fig2_bootstrap_ci,fig4_tercile_ci}.csv`,
`05_label_shuffle_sentinel/05_label_shuffle_sentinel.csv`,
`ian_email_packet_20260611/tables/{03_official_validation_per_ticker_readout,04_same_row_dummy_baselines,08_validation_calibration_summary}.csv`.

---

## Contact-history verification (gating provenance question)
**Verdict: the v1.13 / 2026-06-26 re-base is sound; "historically contacted" should be dropped from prose.**
- The author has confirmed, in two dated governance records ([v2_1_limitation_claim_register_20260617.md:216-228](docs/v2_1_limitation_claim_register_20260617.md) and the claims-ledger v1.13 top-note), that no V1 route or out-of-pipeline exploration contacted the post-2017 segment before the V2.1 walk-forward.
- Structural corroboration in-repo: the data-split protocol freezes the holdout boundary at 2017-01-25; stages 00–04 and official validation provably never score post-2017 (`holdout_test_contact=false`). Nothing in the repo records a pre-V2.1 post-2017 score.
- The guarded status is **unchanged** (still guarded, still not a clean test), re-grounded on two verifiable facts: (1) non-independence (expanding-window shared rows, fixed 5-ticker survivor universe, no final model selected); (2) the post-2017 holdout was scored more than once within V2 — run `20260617_051047_321730` then the bound re-run `20260618_063559_889276` — a spent-holdout reuse (Dwork 2015). Both run IDs are recorded in-repo.
- **This is not a relaxation.** Clean-test / unseen-holdout claims remain forbidden. The internal tier label `guarded_historically_contacted` stays (it is an identifier); only the prose reason changes. Honest replacement wording: "a non-independent confirmation of the validation-frozen primary, with the post-2017 holdout scored more than once within V2 — not a clean test."

---

## Characteristic 1 — the headline margin depends on the aggregation rule [V + G]
```latex
\paragraph{The Headline Margin Depends on the Aggregation Rule.}
On the frozen validation split the same-row \macrofone{} margin is $+1.69\pp$ when rows
are pooled but $+1.94\pp$ when the three activity terciles are weighted equally. In the
guarded walk-forward the margin is $+0.636\pp$ row-pooled and $+0.550\pp$ averaged over
the seven periods. Because the figure moves with the weighting unit, we report each
estimand against its own pooled value and treat no single number as the result.
```
Source: `05_estimand_contrast.csv` (official row 0.016885 / tercile-equal 0.019354; guarded row 0.006362 / period-equal 0.005495).

## Characteristic 2 — the conditional structure recurs across eras [V + G]
```latex
\paragraph{The Conditional Structure Recurs Across Eras.}
The same-row edge declines monotonically across activity terciles, from $+5.43\pp$ (low)
through $+1.91\pp$ (mid) to $-1.54\pp$ (high) on the validation split, where the
high-activity \macrofone{} of $0.483$ sits below the balanced random prior. The same
low-to-high sign pattern reappears in the guarded 2017--2024 segment ($+4.08$, $+0.56$,
$-2.10\pp$; high \macrofone{} $0.480$), a non-independent readout rather than a clean
test. The magnitude is small, but where the edge concentrates is stable across windows.
```
Source: `05_selective_autopsy.csv` seed_mean (low 0.054336 / mid 0.019120 / high −0.015392; high macro_f1 0.48303); `fig4_tercile_ci.csv` guarded (4.083 / 0.558 / −2.104).

## Characteristic 3 — the reference floor sets the honest scale [V]
```latex
\paragraph{The Reference Floor Sets the Honest Scale.}
The stratified dummy reaches \macrofone{} $\approx 0.499$--$0.501$, close to the
even-class value, while the majority-class baseline collapses to $0.329$. The $+18.8\pp$
gap over majority therefore measures the stratified dummy's two-sided coverage, not a
directional signal; the weak-signal scale is the $+1.69\pp$ gap over the stratified floor.
```
Source: `04_same_row_dummy_baselines.csv` (stratified 0.50139 / 0.49889; majority 0.32869).

## Characteristic 4 — the weakest ticker is weak on every axis [V]
```latex
\paragraph{The Weakest Ticker Is Weak on Every Axis.}
Per-ticker validation margins range from $+2.21\pp$ (CSCO) to $+1.00\pp$ (JPM), and the
panel is not uniform. JPM has the smallest margin, its block-bootstrap interval includes
zero (Figure~\ref{fig:validation_deltas}), and it also carries the largest calibration
error (equal-width ECE $\approx 0.022$ against $0.007$--$0.015$ for the others). The
heterogeneity is consistent across accuracy and calibration, not idiosyncratic to one metric.
```
Source: `03_official_validation_per_ticker_readout.csv` (CSCO mean +0.0220 / JPM mean +0.0100); `08_validation_calibration_summary.csv` (JPM ece 0.0224/0.0197); Fig 2 \Description (JPM interval crosses zero).

## Characteristic 5 — calibration is accurate but uninformative [V]
```latex
\paragraph{Calibration Is Accurate but Uninformative.}
The pooled probabilities are well-aligned in aggregate, with equal-mass ten-bin ECE
$\approx 0.010$, yet the Brier score $0.250$ is dominated by its uncertainty term $0.250$
and carries near-zero resolution ($\approx 5\times10^{-4}$). Selective prediction confirms
the consequence: the risk-coverage curve closes only about $3\%$ of the distance to an
oracle (e-AURC $0.330$, AUGRC $0.237$), so the confidence scores cannot define a usable
operating point.
```
Source: `08_validation_calibration_summary.csv` seed_mean eq-mass-10 (ece 0.010247, resolution 0.000471, brier 0.24959, uncertainty 0.24989); `05_selective_autopsy.csv` (e_aurc 0.330219, augrc 0.236872); ledger C3.2 (gap closed 3.0%).

## Characteristic 6 — pre-registration, not peak performance, survives multiplicity [G]
```latex
\paragraph{Pre-Registration, Not Peak Performance, Survives Multiplicity.}
Across the four-family by seven-period guarded roster the CSCV probability of backtest
overfitting is $0.514$, near a coin flip. The numerically largest family mean belongs to
LightGBM at $+0.695\pp$, yet its period lower bound is negative ($-0.030\pp$); only the
pre-declared TCN primary has a period lower bound above zero ($+0.047\pp$). Under the
multiplicity discount the pre-registered candidate, not the highest scorer, is the one
that survives, and no family is selected.
```
Source: `05_multiplicity_discount.csv` (pbo 0.51429; lightgbm mean 0.006950, LCB −0.000297; tcn LCB +0.000470).

## Characteristic 7 — the sign is small but stable [V + G]
```latex
\paragraph{The Sign Is Small but Stable.}
Although the magnitude is near-null, the direction is robust to resampling and ablation.
The pooled validation margin's block-bootstrap interval is $[1.21, 2.19]\pp$ and the
pooled guarded interval is $[0.24, 1.02]\pp$, both excluding zero as descriptive
resampling intervals. The guarded sign survives every leave-one-period-out and
leave-one-ticker-out drop (worst cases $+0.44\pp$ and $+0.41\pp$), and within-day
label-shuffle and time-reversed sentinels collapse the delta toward a negative null, so
the edge is not a within-day-leakage artifact. These are descriptive checks, not
significance tests, and they remain under the multiplicity discount above.
```
Source: `fig2_bootstrap_ci.csv` (panel A [1.2064, 2.188]; pooled [0.2409, 1.0153]); `05_loo_robustness.csv` (all sign_after_drop=True; worst eq-weight 0.004409 period / 0.004091 ticker); `05_label_shuffle_sentinel.csv` (observed_exceeds_shuffle_max=True all terciles).

## Characteristic 8 — negative periods coincide with regime breaks [G]
```latex
\paragraph{Negative Periods Coincide with Regime Breaks.}
Five of the seven guarded periods are positive. The two negative periods are the 2020--21
pandemic window ($-0.26\pp$) and the 2022--23 bear window ($-0.13\pp$), and both period
intervals include zero, as do five of the seven overall. The shortfall concentrates in
structural-break regimes rather than spreading uniformly across the walk-forward.
```
Source: `fig2_bootstrap_ci.csv` period rows (2020-21 −0.2574 [−1.22, 0.66]; 2022-23 −0.1337 [−1.11, 0.87]); `05_guarded_base_rates` (per-period deltas).

---

## What this buys the narrative (honest, not inflated)
The mined picture is a **small, stable, well-characterized, and deliberately un-cashed edge**:
near-null in magnitude (Ch.1,3), conditionally adverse where it would matter most (Ch.2),
useless for an operating rule (Ch.5), and fragile under multiplicity (Ch.6) — yet stable in
sign across resampling, leave-one-out, and leakage sentinels (Ch.7), structured in a way that
recurs across eras (Ch.2) and concentrates its failures in regime breaks (Ch.8), with the
pre-registered candidate (not the top scorer) the one that survives (Ch.6). That is a stronger
and more interesting methods story than the flat hedged version, and it crosses no red line.

## Integration constraint (needs your decision)
The paper is at the **8-page ICAIF hard limit** (verified). These eight paragraphs cannot all be
added without cutting elsewhere. Recommended priority for integration into the v2 draft:
Ch.7 (sign stability) and Ch.6 (pre-registration survives) first — they carry the most honest
"positive" weight; Ch.1, Ch.2, Ch.5 are largely present and need only reframing; Ch.3, Ch.4, Ch.8
are optional enrichments if space allows.

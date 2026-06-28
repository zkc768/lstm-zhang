# v2_skill_draft — fresh-draft notes

Fresh first draft of the paper prose, written from scratch following the
`ml-paper-writing` skill methodology and grounded in the project's real results.
Numbers, figure/table environments, `\label`/`\ref`/`\cite` keys, table cells,
and macros (`\macrofone`, `\pp`, `\numseeds`) were carried over unchanged from
the existing files; only the prose paragraphs and the abstract were rewritten.
This draft is isolated for an A/B comparison against `paper_compare/v1_current/`
(the frozen baseline); neither `paper/` nor `v1_current/` was touched.

## (a) The one-sentence contribution I committed to

> An evaluation protocol that holds a weak intraday stock-direction classifier to
> a same-row baseline and a counted look budget — freezing label, band, splits,
> roster, and decision rules before scoring — and that, run end to end on one
> deliberately near-null case, surfaces estimand sensitivity, a weak guarded
> stability bar, multiplicity fragility, and a conditional sign that a
> headline-only readout would hide.

The contribution is the **evaluation discipline**, not a model or architecture
(novelty ceiling LOW-to-MODERATE per Doc B). Confidence is placed on what the
protocol *does*; the numbers stay exactly honest.

## (b) Section-by-section: what changed in approach vs the conservative baseline

The pre-existing v2 files were a near-verbatim copy of `v1_current` (confirmed by
diff). So "baseline" below = that conservative text.

- **Abstract (`main.tex`).** Rebuilt on Farquhar's 5-sentence shape and led with
  the contribution ("We present an evaluation protocol that holds a weak ...
  classifier to a same-row baseline and a counted look budget, and we run it end
  to end on a deliberately hard case"). The baseline opened by listing inflation
  risks, then "We contribute, not a new model". Mine states the artifact first,
  then why it is hard, then how, then the evidence, then the honest limit. Also
  dropped the baseline's "historically contacted" phrasing for the post-2017
  segment (the ledger top-note re-base retracted the prior-contact premise; the
  guarded basis is now non-independence + within-V2 reuse), so this is also a
  small correctness fix.
- **§1 Introduction.** Reframed around a single confident thesis ("We answer with
  an evaluation protocol, and that protocol is the contribution. The protocol
  does four things ..."). Strong method verbs (freezes / forces / counts / maps).
  The numbers, the weak-bar honesty, and the conditional-sign caveat are all kept;
  hedge-stacking removed.
- **§2 Related Work.** Reorganised methodologically (task baselines / leakage +
  chronological validation / model families / selective + calibration /
  multiplicity / microstructure) rather than citation-by-citation. Leakage,
  backtest-overfitting, and microstructure threads kept (non-cuttable per Doc B).
- **§3 Task and Evaluation Protocol.** This is the contribution section, so the
  tone is most declarative here ("The protocol fixes the label, the splits, the
  baselines, the readout metric, and the decision rules before the first model is
  scored"). Each construction caveat (within-day locality substitutes for
  purge/embargo; cross-day dependence intact; no positive control) is stated once.
- **§4 Models.** Tightened to "the roster exists to drive the protocol, and only
  the TCN is primary". Kept the exact TCN spec, the four-family roster, the
  LightGBM-not-best red line, MLP-as-train-inner-control-only, no LSTM.
- **§5 Experimental Setup.** Light rewrite around Table 1; n=2 honesty and
  `no_final_model_selected=true` kept verbatim in meaning.
- **§6 Validation Results.** Killed the baseline's double-hedge ("All per-ticker
  intervals are descriptive rather than formal inference; ... should not be read
  as an inferential claim"). Now JPM's interval-crosses-zero is stated **once**,
  plainly. C2.3 canonical sentence preserved verbatim. Opening signpost reworded.
- **§7 Guarded Walk-Forward Readout.** Strongest "what the protocol exposes"
  framing while holding every Tier-G red line: "guarded, non-independent
  confirmation", bar = >=2/7 + positive pooled delta (~94% coin), 5/7 descriptive,
  PBO 0.514 descriptive, LightGBM numerically highest but never best/selected.
- **§8 Diagnostics and Robustness.** Each artifact-exclusion stated once
  (class-imbalance excluded; within-day leakage excluded; microstructure NOT
  excluded). Activity = eligible-row-count proxy, "not volume, liquidity, or
  volatility", stated in body and caption. Long sentinel sentence split.
- **§9 Conclusion and Limitations.** Leads with the three-part contribution
  confidently, then the mandatory limitation list, each said once, closing on the
  positive-control next step. Two long run-on sentences from the baseline split.

## (c) Uncertainties / framing choices flagged

- **Genuine uncertainty disclosures kept (not removed):** n=2 too few for
  variance; JPM bootstrap interval crosses zero; six of seven guarded period
  intervals include zero; PBO ~= 0.514 near a coin flip; guarded readout
  non-independent; high-activity tercile below the random prior; near-null edge;
  no positive control; macro-F1 != economic value; Roll(1984) bounce confound
  open. Each appears once, plainly, without apology-stacking.
- **Confidence vs honesty split:** strong verbs are confined to the *method*
  (freeze/force/count/map). Every *result* sentence keeps its honest qualifier.
- **"beats" -> "exceeds"/"improves on":** I replaced the four prose uses of
  "beats" (model-vs-floor) with "exceeds"/"improves on" to stay clear of the
  Doc B title-section's avoid-list (`beats`/`outperforms`) and to match the
  project's canonical "exceeds the stratified dummy floor" phrasing. The required
  Sharpe-ratio *negation* ("no P&L, cost model, Sharpe ratio ...") is retained.
- **Long-sentence exemptions (grep gate 7, >35 words):** ~9 conditional/
  definitional sentences remain in the 37–41-word range (e.g. the guarded-bar
  definition that must inline ">=2/7 AND positive pooled delta"; the
  three-evidence-domains sentence, kept whole on purpose so the anti-fusion red
  line is not split; the validation pass-criteria sentence). These are the style
  guide's allowed "conditional statistical statement" exemption; the worst
  offenders (a 69-word and a 50-word run-on) were split. Several flagged counts
  are inflated by the auditor counting numbers/hyphenated terms as words.
- **GenAI Usage Statement** (`main.tex` endmatter) was left on the Doc A §8
  mandated template wording (it is a required disclosure, not narrative prose).

## (d) Citation placeholders

None. All 40 `\cite{}` keys used resolve to existing entries in
`references.bib`; no new citations were needed, so no `\cite{PLACEHOLDER_...}`
was introduced and no BibTeX was fabricated. Per the ledger, `references.bib` is
**not** yet submission-verified (publisher-page year/volume/DOI checks are an
open pre-submission item); existing `% VERIFY:` flags in the bib are unchanged.

## (e) Self-audit — red lines + canonical-number locations

Anti-AI grep gates (style guide §8) on the final `.tex`:
- Gate 1 (Tier-1 banned words): **0 hits.**
- Gate 2 (Tier-2 replaceables): **0 hits.**
- Gate 3 (banned phrases): **0 hits.**
- Gate 4 (sentence-opening connectives): **0 hits.**
- Gate 5 (-ing tail clauses): **0 hits.**
- Gate 6 (Chinglish residue): **0 hits.**
- Gate 7 (>35-word sentences): worst two split; ~9 conditional statements remain
  as logged exemptions (see (c)).
- Gate 8 (project claims red line): every hit is either a negated/qualified usage
  ("not a clean test", "no final model is selected", "non-independent") or the
  `zhang2026whenalpha` cite-key false-positive on "alpha". No standalone
  best/profitable/tradable/well-calibrated/statistically-significant claim.
- `novel`: **0** (ceiling is <=1). `comprehensive`/`robust`/`significant`/
  `crucial`: 0. "demonstrat" only in the required negation "not a demonstration
  of effectiveness".

Compile: `latexmk -pdf main.tex` → **exit 0, 8 pages, 0 overfull hboxes, 0 LaTeX
errors, 0 undefined refs/citations.** Fits the ICAIF 8-page hard limit.

Cross-references: all 12 `\ref`/`\autoref` targets have matching `\label`s.

Nine red lines (Doc B §1 / ledger), each satisfied — with locations:
1. **Three evidence domains never fused.** §3 names all three; every result
   sentence tags its domain; validation (+1.69pp) and guarded (+0.636pp) are
   stated in separate sentences (abstract, §1, §9).
2. **Tier-V wording.** "On the frozen validation split", n=2 stated; "meets the
   predeclared criteria" framed as fact, "not a demonstration of effectiveness"
   (§6).
3. **Tier-G wording.** "met the predeclared guarded stability criteria in a
   ... non-independent walk-forward"; "guarded"/"non-independent" carried; bans
   honored (§7, §1, abstract).
4. **No model selected; LightGBM not best.** "no final model is selected"
   (§3/§4/§5/§6/§7/§9); LightGBM "numerically highest" only (§7).
5. **PBO/LCB/bootstrap = descriptive.** "descriptive PBO", "descriptive
   discounts, not significance tests" (§7); no significance claims anywhere.
6. **Novelty ceiling.** "novel" used 0 times; contribution framed as evaluation
   discipline (§1, §9).
7. **Conditional/calm-bar edge = limitation, not selling point.** Stated as a
   "diagnostic boundary" with the Roll(1984) caveat (§1, §7, §8, §9).
8. **Activity = eligible-row count**, "not volume, liquidity, or volatility"
   (§1, §8 body + caption).
9. **C2.3 = control-row spread**, not apples-to-apples with the full-family
   validation margin; canonical sentence preserved verbatim (§6).

Canonical-number locations (file → what):
- `0.5170 ± 0.0009` TCN macro-F1 — abstract n/a, §1, §6 body + Table 2.
- `+1.69pp` validation Δ vs dummy — abstract, §1, §6 (body + table), §9.
- `+1.63pp` worse-seed Δ — abstract, §1, §6 (body + table).
- `+18.8pp` Δ vs majority — §6 body + Table 2.
- dummy floor `0.499–0.501`, majority `0.329` — §6 body + Table 2.
- CSCO `+2.21pp` / JPM `+1.00pp` — §6 body + Table 2.
- positive-ticker `5/5` — §6 Table 2; JPM interval-crosses-zero — §6 body.
- control-row spread `0.66pp` (4 rows, 2 last-step) — §1, §6 (C2.3 sentence).
- guarded row-pooled `+0.636pp` / equal-weight `+0.550pp` — abstract, §1, §7, §9.
- guarded bar `>=2/7` + positive pooled, `~94%` coin, `5/7` descriptive — §1, §7.
- `56` guarded scoring events — §3, §7.
- PBO `0.514` — abstract, §1, §7, §9; TCN period-LCB `+0.047pp`,
  Std-DLinear LCB `-0.464pp` — §7.
- guarded means LightGBM `+0.726` / MS-DLinear+TCN `+0.672` (6/7) /
  Std-DLinear `+0.513` (4/7) — §7.
- LOO `+0.538pp` by period / `+0.514pp` by ticker — §7.
- ECE `0.010`, Brier `0.2496` (uncertainty `0.2499`), resolution `~4.7e-4` — §8.
- e-AURC `0.330`, AURC `~0.470` vs oracle `~0.140`, AUGRC `0.237`,
  ΔAURC `-0.010` CI `[-0.014,-0.006]`, `3%` gap-closed CI `[1.9,4.0]%`,
  partial `0.25/0.14/0.07pp` — §8.
- ablation gaps `+0.03/-0.14/-0.12/-0.63pp` — §8.
- terciles validation `+5.43/+1.91/-1.54`, high macro-F1 `~0.483`;
  guarded `+4.08/+0.56/-2.10`, high macro-F1 `0.480`; up-rate
  `0.523/0.515/0.502 (~2.1pp)`; balanced prior `~0.498–0.500` — §8 (body, Table 3,
  Fig 4 caption); validation high tercile / low tercile also in §9.
- data: 5 tickers, `736,685` train / `151,064` validation (`~29.9k–30.8k`/ticker),
  horizon `9`, band `3.0 bps`, window `w=20` — §3, §5, Table 1.

## Process note

This is prose-only. No training was run, no experiment re-run, and no number
changed. The work followed the project reading chain (ledger v1.13 + Doc A/B +
anti-AI guide override the skill on any conflict) and the skill's narrative,
abstract, Gopen–Swan, and Lipton word-choice principles for the prose itself.

---

## 2026-06-27 — Affirmative integration pass (recommended set, space-neutral)

Targeted edit to make the draft read more affirmatively without overclaiming:
added the two affirmative-core characteristics, reframed three present ones,
and re-grounded the guarded-status wording. Prose-only; no training; no
experimental number changed. All canonical numbers re-verified against the
sha-mirrored Stage 05 artifacts (paths below).

### Task 1 — "historically contacted" wording fix (correctness)

- Grep of the whole v2 draft confirmed the phrase was **already absent from every
  `.tex` file** (the abstract had been re-based in the original draft). The phrase
  survived only in (a) `figures/FIGURE_BRIEF.md` (5 occurrences, used as the
  guarded-panel *reason*) and (b) the identifier `guarded_historically_contacted`
  in `outline_and_claims.md:9`.
- Re-grounded the guarded *reason* in **`sections/07_guarded_walkforward.tex`**,
  first paragraph "What the guarded readout is." It now rests on the two verified
  facts: (1) **non-independent** confirmation of the validation-frozen primary
  (expanding-window shared rows, fixed 5-ticker survivor universe, **no final
  model selected**); (2) the post-2017 holdout was **scored more than once inside
  V2** (an earlier walk-forward run preceded the bound re-run), a spent-holdout
  reuse, cited `\cite{dwork2015reusable}` (verified key, `references.bib:155`,
  already used in §2). Removed the old "saw no validation-phase contact" sentence
  to avoid implying an untouched holdout. Kept "guarded", "non-independent", "not
  a clean test"; introduced no "clean test / unseen / out-of-sample proof / final
  model" upgrade.
- Updated the 5 `FIGURE_BRIEF.md` occurrences from "historically contacted" to
  "non-independent" so the figure brief matches the corrected basis (the rendered
  captions in the `.tex` were already correct and were not touched).
- Abstract left as-is: it already reads "non-independent and not a clean test"
  (concise form the task permits).

### Task 2 — reframed Ch.1 / Ch.2 / Ch.5 (no new numbers, no new length)

- **Ch.1 (estimand sensitivity):** already crisp in the §7 "headline delta is
  estimand-sensitive" paragraph and the abstract; left at target framing.
- **Ch.2 (cross-era conditional gradient):** tightened the recurrence sentence in
  **`sections/08_diagnostics.tex`** ("The edge concentrates in calm bars") to the
  affirmative-but-bounded Ch.2 line — "The same low-to-high sign pattern recurs in
  the guarded 2017--2024 era ... The magnitude is small, but where the edge
  concentrates is stable across both windows." Kept the non-independent /
  re-aggregation caveat and the high-tercile-below-prior limitation framing.
- **Ch.5 (calibration accurate but uninformative):** already at the crisper
  framing (small ECE + near-zero resolution -> "Small calibration error therefore
  does not mean the confidence scores rank cases usefully"; selective prediction
  "barely improves on random ranking" + abstention "compounds that limitation").
  Left unchanged to avoid change-for-change churn.

### Task 3 — added Ch.7 and Ch.6 (the affirmative core), space-neutral

Both `\paragraph{}` blocks placed in **`sections/07_guarded_walkforward.tex`**
(the guarded / multiplicity section):

- **Ch.6 "Pre-registration, not peak performance, survives multiplicity."** —
  immediately after the (compressed) multiplicity-mechanism sentence. Replaces the
  old verbose multiplicity paragraph.
- **Ch.7 "The sign is small but stable."** — last paragraph of §7. Replaces the
  old standalone row-pooled LOO paragraph; V and G statements are in separate
  sentences (validation CI tagged "On the frozen validation split"; guarded CI,
  LOO, and sentinels in their own sentences). States the CIs/LOO/sentinels are
  **descriptive, not significance tests**, and that they sit **under the
  multiplicity discount above**.
- `\paragraph{}` heading case converted to **sentence case** to match the
  section's house style and the anti-AI guide (the EXPERIMENT_ANALYSIS blocks were
  Title Case); block prose otherwise used as written.

Hedge-stacking removed to reclaim the space (net length change ~0; final = 8 pp):

1. §7 "The bar is a weak floor" paragraph: deleted the redundant preview sentence
   "The protocol still reports what a headline-only readout would omit: a weak
   floor, a near-even multiplicity-discount readout, and a conditional sign." —
   the two new paragraphs now deliver exactly those three items.
2. §7 multiplicity paragraph: collapsed the triple "like-for-like / post-hoc
   within-family maxima / lone positive lower bound reflects its single profile"
   hedge into the single Ch.6 statement plus the retained Std-DLinear
   `-0.464\pp` worst-family lower bound; the descriptive-discount caveat is now
   stated once.
3. §7 LOO paragraph: the expanding-window "largely mechanical" framing is carried
   by the Ch.7 "robust to resampling and ablation" + LOO worst-case sentence;
   the verbose standalone LOO paragraph is gone (its load-bearing budget-ledger
   contact-asymmetry sentence — 56 events, `for_selection=false` — was kept).
4. §6 per-ticker paragraph: removed the apologetic double "The per-ticker
   intervals are descriptive ... not an inferential claim" (the descriptive
   nature is already stated in "How the bands are computed", the caption, and the
   figure `\Description`). JPM-interval-crosses-zero is now stated once, plainly.

### Number-by-number confirmation (Ch.6 / Ch.7 vs artifacts)

Estimand decision: the section is built end-to-end on the **binding row-pooled**
estimand (abstract `+0.636\pp` row-pooled; §7 estimand-sensitive paragraph;
"multiplicity discount on the binding row-pooled estimand"). EXPERIMENT_ANALYSIS
Ch.6 is sourced from the **equal-weight companion** `05_multiplicity_discount.csv`
(LightGBM `+0.695\pp`), and Ch.7's LOO worst cases there are the equal-weight
`+0.44 / +0.41\pp`. To avoid a `+0.695` vs `+0.726` numeric contradiction inside
the section and to hold the binding-estimand discipline, the two blocks were
dropped in with the **binding row-pooled** values, which are real artifact values
and the more affirmative ones. The LCBs are identical across both estimands.

Ch.6 (`artifacts/05_row_pooled_multiplicity/05_row_pooled_multiplicity.csv`):
- PBO `0.514`  = `pbo` 0.5142857 (identical in the equal-weight file).
- LightGBM family mean `+0.726\pp`  = `mean_delta` 0.007263 (row-pooled).
- LightGBM period LCB `-0.030\pp`  = `period_delta_lcb` -0.0002975.
- TCN-primary period LCB `+0.047\pp`  = `period_delta_lcb` +0.0004702.
- "no family is selected" — red line preserved.

Ch.7:
- Validation CI `[1.21, 2.19]\pp`  = `05_fig2_uncertainty/fig2_bootstrap_ci.csv`
  panel A overall [1.2064, 2.188].
- Guarded CI `[0.24, 1.02]\pp`  = same file panel B pooled [0.2409, 1.0153].
- LOO worst cases `+0.538\pp` (period) / `+0.514\pp` (ticker)  =
  `artifacts/05_row_pooled_loo/05_row_pooled_loo.csv` worst_after 0.005383 (drop
  wf_p2) / 0.005141 (drop CSCO); all `sign_after_drop=True`.
- Label-shuffle + time-reversed sentinels "collapse the delta toward a negative
  null": label-shuffle = `05_label_shuffle_sentinel.csv`
  (`observed_exceeds_shuffle_max=True` all terciles); time-reverse sentinel is the
  designed negative control in `src/lst_models/metrics.py` /
  `diagnostics.py` and `configs/stages/05_thesis_synthesis.yaml:129` (test
  `tests/contracts/test_metrics.py:111` asserts `time_reverse_delta <
  observed_delta`). Qualitative claim, no fabricated number.

Task 1 spent-holdout run IDs (ledger top-note / C4): earlier run
`20260617_051047_321730`, bound re-run `20260618_063559_889276`.

### Verification

- `latexmk -pdf main.tex`: **exit 0**, **8 pages**, **0 undefined refs/citations**,
  **0 overfull hboxes**, **0 LaTeX errors**.
- Anti-AI grep gates (main.tex + all sections): gates 1–6 **0 hits**; gate 8 only
  negated/qualified usages ("non-independent", "not a clean test", "no final
  model", cite-key "alpha" false positives) — no standalone red claim; `novel`
  **0**; `comprehensive`/`significant`/`crucial` **0**; `demonstrat` only negated.
  Gate 7: the two new paragraphs and the new Dwork sentence were split to stay
  <=35 words; the remaining flags are pre-existing caption/table content inflated
  by the auditor counting numbers/hyphenated terms (logged exemptions).
- Evidence domains kept separate: validation `+1.69\pp` and guarded `+0.636\pp`
  never share a claim; Ch.7's validation CI and guarded CI are in separate
  sentences; Ch.7 CIs/LOO/sentinels are descriptive, sit under the PBO 0.514
  discount, and the Roll(1984) bid-ask-bounce confound stays open.

### Flagged uncertainty

- **Binding-vs-companion estimand substitution** (above) is the one place the
  added blocks deviate from EXPERIMENT_ANALYSIS's literal numbers: Ch.6 LightGBM
  `+0.726\pp` (binding) replaces the block's `+0.695\pp` (equal-weight), and
  Ch.7 LOO `+0.538 / +0.514\pp` (binding) replaces `+0.44 / +0.41\pp`
  (equal-weight). Both substitutes are verified artifact values; the choice keeps
  one coherent estimand and avoids an in-section numeric contradiction. If the
  reviewer prefers literal-verbatim blocks, switch the whole section (abstract
  included) to the equal-weight companion instead — do not mix.

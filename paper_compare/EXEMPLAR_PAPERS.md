# Exemplar Papers for the lst_models ICAIF Submission

Purpose: a curated, ranked set of **real, independently verifiable** papers to study for
(1) submission style/structure, (2) human and rigorous prose (not AI-slop), and
(3) honest framing of a weak/conditional result. We imitate **structure and logic only** —
never copied text. See "How to use these without plagiarism" at the bottom.

Our paper, for matching: an 8-page ICAIF (ACM `sigconf`, double-blind) paper whose
contribution is an **evaluation protocol**, not a model — frozen
label/no-trade-band/chronological-split/roster/validation-budget before scoring,
same-row stratified-dummy baselines, a counted validation budget, CSCV/PBO
multiplicity discount, and no final model selected. The result is deliberately
near-null (validation macro-F1 +1.69pp over a ~0.50 dummy floor; guarded
non-independent walk-forward +0.636pp with PBO ≈ 0.51). The honest, interesting
finding is **conditional/regime-dependent** predictability: the edge concentrates in
calm/low-activity bars and inverts on high-activity bars, recurring across eras,
with a bid-ask-bounce microstructure confound left open. Framing is **finding-forward
but honest**: confident about the method, honest about the weak numbers, never
overclaiming.

---

## Verification status (read this first)

The live web-search / page-summarizer backend was failing during this pass (upstream
model-routing error), so papers were verified through **DOI / arXiv-ID resolution** plus
cross-check against the project's provenance-tracked `paper/references.bib` and
`hf_stock_ml_references2/papers/README.md`. Every paper below has a resolving DOI/arXiv
ID and is present in the verified bib. This is NOT fresh web discovery — it is the
project's own canonical references curated as exemplars. Author-name forms / exact titles
still need the standard VERIFY-BEFORE-SUBMIT eyeball on each publisher page at submission.
Two recent "foils" that could not be verified are quarantined at the bottom (not used).

---

## Ranked exemplars

### 1. Chalkidis & Savani — *Trading via Selective Classification* (ICAIF 2021)
- DOI `10.1145/3490354.3494379` (ACM DL). Open access: no.
- Category: venue-fit (same venue, same selective-classification machinery) + honest foil.
- Why closest match: same venue, same length class, same reject-option/coverage apparatus
  our diagnostics use, but it sells a *positive* coverage story. It is our direct foil —
  write the honest, floor-aware mirror.
- Lessons: (1) ICAIF `sigconf` skeleton at our exact 8-page budget; (2) present a
  risk-coverage curve as a first-class result object, annotated with our dummy floor; (3)
  same-venue hedging/citation density expectations.

### 2. Zeng, Chen, Zhang & Xu — *Are Transformers Effective for Time Series Forecasting?* (DLinear, AAAI 2023)
- arXiv `2205.13504`; DOI `10.1609/aaai.v37i9.26317`. Open access: yes.
- Category: honest-weak-finding-style ("simple beats complex," done rigorously).
- Why a top style model: canonical example of winning with a deflationary result by being
  ruthless about evaluation, not loud about a number — our exact posture.
- Lessons: (1) title-as-question that promises an honest verdict (cf. our "Small Edges,
  Strict Boundaries"); (2) baseline-as-hero (we elevate the same-row dummy + the protocol);
  (3) ablations that *remove* alternative explanations (model for our tercile-floor +
  label-shuffle sentinel tables); (4) state the limitation in the same breath as the claim.

### 3. Kapoor & Narayanan — *Leakage and the Reproducibility Crisis in ML-Based Science* (Patterns 2023)
- DOI `10.1016/j.patter.2023.100804`. Open access: yes (also arXiv).
- Category: evaluation-rigor (the leakage taxonomy our protocol defeats).
- Why: reference statement of the problem we solve; models turning "evaluation is broken"
  into a constructive, checklist-driven contribution.
- Lessons: (1) taxonomy-then-remedy structure — pair each protocol guard with a named leak;
  (2) authoritative, non-defensive prose about others' mistakes; (3) positioning a
  methodological contribution as broadly useful beyond one dataset.

### 4. Bailey, Borwein, López de Prado & Zhu — *The Probability of Backtest Overfitting* (J. Computational Finance 2016)
- DOI `10.21314/JCF.2016.322` (companion AMS `10.1090/noti1105`, freely readable). OA: partial.
- Category: evaluation-rigor — and the **source of the CSCV/PBO machinery we use**.
- Why: the method behind our PBO ≈ 0.51 discount; a craft model for stating an
  uncomfortable result with composure.
- Lessons: (1) introduce a multiplicity statistic then apply it to your own result; (2)
  sober declarative tone around a deflationary finding; (3) explicit "diagnostic only, no
  tradable claim" stance — our exact posture on the tercile map.

### 5. Gu, Kelly & Xiu — *Empirical Asset Pricing via Machine Learning* (RFS 2020)
- DOI `10.1093/rfs/hhaa009`. Open access: no (NBER/SSRN preprints exist).
- Category: honest-weak-finding-style (a small out-of-sample effect as a legitimate result).
- Why: field-defining example that a small, honestly-measured predictive effect is
  publishable; legitimizes our "small but survives strict evaluation" thesis.
- Lessons: (1) make the modest effect size the point, not an embarrassment; (2) conditional
  subgroup analysis adds weight without a single inflated headline; (3) measured senior prose.

### 6. Henkel, Martin & Nardari — *Time-Varying Short-Horizon Predictability* (JFE 2011)
- DOI `10.1016/j.jfineco.2010.09.008`. Open access: no.
- Category: conditional / state-dependent predictability (our finding's framing).
- Why: canonical "predictability is not constant — it is state-dependent/countercyclical";
  the anchor that makes our conditional finding credible, not a fluke.
- Lessons: (1) frame predictability as a function of state (their business cycle ↔ our
  activity regime); (2) reconcile an average-null with a regime-concentrated signal without
  contradiction — almost exactly our low/high-activity inversion; (3) honest scoping of
  where the effect holds.
- Conditional-predictability companions (related work, not separate exemplars): Heston,
  Korajczyk & Sadka, *J. Finance* 2010, DOI `10.1111/j.1540-6261.2010.01573.x`; Roll 1984,
  DOI `10.1111/j.1540-6261.1984.tb03897.x` (the open microstructure confound).

### 7. Grinsztajn, Oyallon & Varoquaux — *Why Do Tree-Based Models Still Outperform Deep Learning on Typical Tabular Data?* (NeurIPS 2022 D&B)
- arXiv `2207.08815`. Open access: yes.
- Category: honest-weak-finding-style ("standard beats fancy" as a careful benchmark) — secondary.
- Why: a second template for a deflationary benchmark-driven result; relevant because
  LightGBM is our highest-numeric roster model.
- Lessons: (1) the contribution is the fair-comparison design, not a new model — our shape;
  (2) control confounds across conditions without an inflated headline; (3) tables, not
  adjectives, carry the claim.

---

## Top 2 to imitate
1. **Chalkidis & Savani, ICAIF 2021** — same venue/length/machinery; tells us the exact
   ICAIF structure and is the perfect foil to invert (honest, floor-aware mirror).
2. **Zeng et al. (DLinear), AAAI 2023** — gold standard for landing a deflationary
   "simple beats complex" result through rigor: imitate the question-title,
   baseline-as-hero, and ablations-that-rule-out-alternatives.

Pair with Henkel et al. (2011) as the conditional-finding framing precedent.

---

## How to use these WITHOUT plagiarism
Study structure and logic only — never reuse sentences or distinctive phrasings. Extract
each paper's skeleton (section order, what each section accomplishes, where the limitation
sits, what the lead figure is) into an outline in our own words, then write from our own
claims ledger and evidence — not with any exemplar open in front of us. Borrow *moves*
(title-as-question, baseline-as-hero, taxonomy→guard pairing, self-applied PBO, regime
framing), not wording. Cite these normally in related-work/methods (esp. Bailey et al. for
PBO/CSCV, Kapoor & Narayanan for leakage, Henkel et al. for conditional predictability).
Before submission, run the project's Originality/Similarity Triage
(`docs/protocols/lst_models_paper_revision_workflow.md` §8) and the anti-AI style pass.

---

## Unverified this pass — DO NOT cite as exemplars
- **"When Alpha Disappears…"** listed as `arXiv:2605.23959` — suspicious ID (May-2026, high
  sequence; arXiv DOI redirect is auto-generated and does not prove existence). Already
  `% VERIFY`-flagged in our bib. Verify on arxiv.org before any use.
- **"…LLM-based Financial Investing Strategies…" (FINSABER)** listed as `arXiv:2505.07078` —
  plausible ID, but title/authors/venue unconfirmed live. Topically a backtest-realism
  foil, not a structure/prose exemplar.

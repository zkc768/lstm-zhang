# Methodology-as-contribution — positioning an evaluation design as the deliverable

When the contribution is *how you measure* (a benchmark / protocol), not *a new model*. This
is our exact shape: our contribution is the **guarded evaluation protocol**, and no final
model is selected. Grinsztajn is the primary template; DLinear supplies the baseline-as-
instrument move. Rule + paraphrased illustration + source.

---

## 1. Announce the method as the contribution, explicitly and early
**Rule:** in the abstract and the contributions list, name the protocol/benchmark as
contribution #1 — before any result. Do not let the method read as mere "setup."
- *Illus. (Grinsztajn, §1):* contribution (1) is literally "a new benchmark ... with a precise
  methodology," stated ahead of the empirical findings.
- **Ours:** contribution #1 = the protocol (frozen label / no-trade band / chronological split
  / roster / validation budget, fixed *before* scoring; same-row stratified-dummy baselines;
  counted validation budget; CSCV/PBO discount; no final model selected).

## 2. Inclusion / design criteria as the rigor argument
**Rule:** spell out the design choices as an *enumerated list of criteria*, each justified by
the artifact it prevents. The list itself is the evidence that the evaluation is fair — each
criterion pre-empts a "your setup is rigged" objection.
- *Illus. (Grinsztajn, §3.1-3.2):* dataset criteria are enumerated with rationale — exclude
  high-dimensional / too-small / too-easy / deterministic data; each line says *why*, so the
  benchmark cannot be accused of cherry-picking. "Not too easy" even defines a quantitative
  cutoff (a default linear model must not already be near the best).
- **Ours:** present each guard as a criterion with the leak it closes:
  - frozen label + no-trade band -> closes label/threshold leakage.
  - chronological split + counted validation budget -> closes look-ahead + multiple-looks
    leakage.
  - same-row stratified dummy -> closes class-imbalance illusion.
  - CSCV/PBO -> closes multiplicity/backtest-overfitting.
  - no final model selected -> closes selection leakage.
  (Pair-each-guard-with-a-named-leak is also the Kapoor & Narayanan taxonomy move; see
  `EXEMPLAR_PAPERS.md` #3.)

## 3. Specify the procedure precisely enough to be reusable
**Rule:** give the protocol the level of detail that lets someone re-run it; precision is what
turns "setup" into "contribution." Offer the reusable asset.
- *Illus. (Grinsztajn, §3.3 + "Reusable code"):* the hyperparameter-search procedure is
  pinned down (search spaces, iteration budget, repeated reshuffles to estimate variance), and
  raw search results are released so others can plug in new methods cheaply.
- **Ours:** state the validation budget as a *counted* number, the split boundaries, the dummy
  construction, and the CSCV/PBO configuration exactly. The protocol + frozen pre-registration
  is the deliverable that outlives the near-null number.

## 4. Make the comparator/instrument do the arguing (baseline-as-instrument)
**Rule:** if a simple baseline or a floor is your measuring stick, treat it as part of the
methodology contribution — define it carefully and foreground it.
- *Illus. (DLinear, §4):* the linear model is introduced as a *measuring instrument* for the
  whole Transformer line, not as a proposed product.
- **Ours:** the same-row stratified dummy is the instrument; the protocol's value is that it
  makes the dummy floor the honest yardstick for every roster model.

## 5. Aggregate fairly and show the aggregation rule
**Rule:** state how results are pooled across settings, and pick an aggregation that resists
outliers / inflation. Showing the rule is itself a rigor signal.
- *Illus. (Grinsztajn, §3.4):* a normalized distance-to-the-best-quantile aggregation, chosen
  specifically so outlier runs don't dominate; the choice is explained, not hidden.
- **Ours:** when pooling across strata/eras, state the pooling rule and why it doesn't
  manufacture an edge (e.g., report per-stratum floors rather than a single flattering
  average).

## 6. Position the contribution as broadly useful, then scope it
**Rule:** claim the method generalizes beyond your one dataset (that's why it's a
contribution), but bound the empirical claim to what you tested.
- *Illus. (Grinsztajn, Conclusion):* the benchmark is offered as reusable infrastructure to
  "stimulate research," while the empirical trend stays scoped to medium-sized data.
- **Ours:** the protocol transfers to any intraday direction study; the *finding* stays scoped
  to our instrument, label, band, and bars.

---

## [RED-LINE] flags
- Grinsztajn's framing leans on "remain **state-of-the-art**" and the title's "**outperform**."
  We keep the *methodology-as-contribution structure* and drop those verbs entirely. Our
  result language: "exceeds the same-row dummy floor by +1.69pp," "meets the predeclared
  criteria," "PBO ~0.51."
- Do not let "the protocol is rigorous" silently become "the result is strong." The method is
  the confident part; the number stays near-null and conditional. Keep that separation in
  every sentence that mentions both.

## One-line shape for our §3 (Protocol)
contribution-announced-as-method -> guards enumerated as criteria, each closing a named leak
-> procedure pinned down + pre-registration/asset released -> dummy floor as the instrument
-> fair aggregation rule shown -> broadly-useful-then-scoped.

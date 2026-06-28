# Weak-result framing — landing a small/conditional finding through rigor

**THE key file.** Both exemplars sell a deflationary result; we sell a *near-null* one. The
craft is identical: make **rigor** the source of confidence, not the size of a number. Each
move = rule + paraphrased illustration + source. **[RED-LINE]** marks verbs to swap.

---

## 1. Baseline-as-hero
**Rule:** elevate the simple comparator to a named protagonist with its own identity, figure,
and table column. The reader should root for the baseline. The "result" is then framed as
*the baseline (or the floor) holding up*, not a model winning.
- *Illus. (DLinear, §4 + Fig. 2):* the one-layer linear map is named, diagrammed, and given a
  family of variants — it is the star, not a control.
- *Illus. (Grinsztajn, Fig. 1-2):* tree models are drawn as the reference curve every NN is
  measured against.
- **Ours:** the **same-row stratified dummy** and **the protocol itself** are the heroes. The
  headline object is "the +1.69pp gap over the dummy floor," presented as *the floor being
  cleared by a hair*, not as a model triumph.
- **[RED-LINE]:** borrow the baseline-as-hero *structure*; DLinear's hero "outperforms" — ours
  only "exceeds the same-row dummy floor / meets the predeclared criterion."

## 2. Question-title that promises an honest verdict
**Rule:** title as a yes/no or why-question so the paper is allowed to answer "barely / only
sometimes." A question title licenses a deflationary answer.
- *Illus. (DLinear):* "Are Transformers Effective ...?" -> answer can be "not really, here."
- *Illus. (Grinsztajn):* "Why do tree models still outperform ...?" -> presumes the modest
  fact, investigates it.
- **Ours:** a question/contrast title (e.g., the project's "Small Edges, Strict Boundaries"
  register) signals up front that the answer is "a little, under conditions."

## 3. Ablations / sentinels that RULE OUT alternative explanations
**Rule:** the bulk of the evidence should *eliminate ways the result could be an artifact*,
not pile up effect size. Each ablation kills one "but maybe it's just X" objection. This is
how a small number becomes *credible* rather than *lucky*.
- *Illus. (DLinear, §5.3):* a battery of removals each closes an escape hatch —
  shuffle the input order (tests whether the model even uses order), vary the look-back
  window (tests whether more context helps), strip embeddings, shrink training size, compare
  practical efficiency. Every one removes a "the complex model must be doing something"
  alibi.
- *Illus. (Grinsztajn, §5):* targeted *data transformations* (smooth the target, add/remove
  uninformative features, randomly rotate features) each isolate one inductive-bias
  explanation for the gap.
- **Ours (direct mapping):**
  - **tercile / activity-regime split** = Grinsztajn's transformation that localizes *where*
    the effect lives (calm vs high-activity), instead of one averaged headline.
  - **label-shuffle sentinel** = DLinear's order-shuffle: if skill survives shuffled labels,
    the pipeline leaks. Reporting the sentinel near-floor *rules out leakage*.
  - **CSCV / PBO discount applied to our own result** = a self-administered ablation that
    rules out multiplicity (see move 5).
  - **same-row dummy across strata** rules out "the gap is just class imbalance."
- **Effect:** confidence comes from "we tried hard to make it vanish and it didn't (quite),"
  which is exactly right for a near-null edge.

## 4. State the limit in the SAME breath as the claim
**Rule:** never let a positive clause stand alone; bind the boundary to it in the same
sentence or the very next. This is the single highest-value honesty move for a weak result.
- *Illus. (DLinear, §5.2 / conclusion):* claims of skill are paired immediately with scope
  ("at least for the existing benchmarks") and with the baseline's admitted limits ("limited
  model capacity ... a simple yet competitive baseline").
- *Illus. (Grinsztajn, Discussion):* the headline trend is stated, then immediately fenced by
  a Limitation paragraph of open questions (very small / very large data, missing values).
- **Ours (templates, reword freely):**
  - "A +1.69pp macro-F1 edge clears the ~0.50 dummy floor; at PBO ~0.51 the same edge is one
    coin-flip from chance." (claim + discount, same breath)
  - "The edge concentrates in calm bars and **inverts** on high-activity bars" — the
    inversion is reported *with* the edge, not buried.
  - "A bid-ask-bounce confound remains open" stated next to the conditional finding, not in a
    footnote.

## 5. Apply the skeptical statistic to YOUR OWN result
**Rule:** introduce the multiplicity/overfitting discount, then turn it on yourself
*publicly*. Pre-empting the harshest reviewer is more persuasive than a bigger number.
- *Illus. (Grinsztajn, §3.3):* they build a tuning-cost-aware procedure that *jointly samples
  the variance of hyperparameter search* — i.e., they price in the thing that usually inflates
  benchmark claims, against their own numbers.
- *Illus. (DLinear, §5.3 efficiency/training-size):* they stress-test their own favorable
  reading (does less data hurt? is efficiency actually better?) rather than only the rivals'.
- **Ours:** CSCV/PBO ~0.51 is reported *as a property of our edge*, framed as "we discount our
  own result for the searches we ran." (Borwein/Bailey-style composure; see
  `EXEMPLAR_PAPERS.md` #4.)

## 6. Tables/figures carry the claim; adjectives do not
**Rule:** let a well-built table or curve be the argument; keep prose declarative and quiet.
For a weak result this prevents the reader from feeling oversold.
- *Illus. (DLinear, Tables 1-8):* dense tables with a stated reading direction ("the lower
  the better") and a fixed bold/underline convention; the prose mostly *points at* them.
- *Illus. (Grinsztajn, Figs. 1-6):* aggregated curves with confidence ribbons do the
  persuading; text narrates trend and scope only.
- **Ours:** make the **risk-coverage / tercile-floor / sentinel** tables first-class objects,
  each annotated with the dummy floor, so the near-null gap is *visible* and self-limiting.
- **[RED-LINE]:** DLinear's table caption highlights "best results." We do not write "best";
  annotate with "exceeds same-row dummy" / "meets predeclared criterion" instead.

## 7. Reconcile an average-null with a conditional signal (no contradiction)
**Rule:** when the average is ~null but a subgroup shows an effect, present it as
*structure discovered*, not as a save. State the average honestly, then localize.
- *Illus. (Grinsztajn, §5.2-5.4):* the overall gap is decomposed into *when* it appears
  (smooth targets, uninformative features, rotation) — the conditionality IS the contribution.
- **Ours:** "Averaged across bars the edge is near-null; resolved by activity regime it is
  positive on calm bars and negative on high-activity bars, recurring across eras." This is
  the project's Option-2 spine — the regime map is the interesting finding, framed as
  cartography ("we map where it holds and where it inverts"), not as rescue.
  (Conditional-predictability precedent: Henkel et al. 2011; see `EXEMPLAR_PAPERS.md` #6.)

---

## Anti-patterns to avoid (what NOT to copy)
- **Volume over rigor:** do not pad with extra datasets/runs to *look* bigger. Both exemplars
  win on *design*, not count. Our edge is small — more runs only raise PBO.
- **Strong verbs the exemplars use freely:** `outperforms`, `surprisingly outperforms`, `by a
  large margin`, `state-of-the-art`, `best`. **All forbidden for us.** Swap every one for
  red-line vocabulary bound to the ledger.
- **Burying the inversion / confound:** the high-activity inversion and the microstructure
  confound are features of the honest story — keep them in the main text, beside the claim.
- **Victory-lap conclusion:** end constructive (the protocol is reusable; here is the map),
  not triumphant.

# Abstract shapes — sentence-by-sentence move lists

Two deflationary abstracts, broken into ordered moves. Copy the **sequence**, not the words.
Our target abstract should be finding-forward but floor-aware.

---

## DLinear abstract (move list)
*Source: DLinear, Abstract.*

1. **Name the bandwagon, neutrally.** State that a class of complex models has surged on the
   task. (No praise, no attack — just "there has been a surge of X.")
2. **Plant the doubt as a stance, not an insult.** "We question the validity of this line."
3. **Give the mechanism for the doubt.** One crisp technical reason the complex approach may
   be mismatched to the problem (here: permutation-invariant attention loses temporal order).
   *This earns the doubt — it is not just contrarianism.*
4. **Introduce the deflationary instrument.** Name the embarrassingly simple comparator.
5. **State the headline empirical result.** [RED-LINE] DLinear says the simple model
   "surprisingly outperforms ... in all cases, often by a large margin." **We must NOT.**
   Our version: "a weak edge (+X pp over the same-row dummy floor) survives the protocol."
6. **Signal breadth of evidence, not size of effect.** "comprehensive empirical studies"
   across many conditions — rigor as the selling point.
7. **Close with a forward call.** Invite the field to revisit assumptions; point to released
   code. (Modest, constructive — not a victory lap.)

**Shape in one line:** bandwagon -> doubt -> *why* doubt -> simple instrument -> result ->
breadth-of-evidence -> constructive call.

---

## Grinsztajn abstract (move list)
*Source: Grinsztajn, Abstract.*

1. **Concede the rival's real wins.** Acknowledge deep learning's genuine successes
   elsewhere (text/image). Credibility through fairness.
2. **State the unsettled question.** On this data, superiority "is not clear." (Gap as a
   factual uncertainty, not a takedown.)
3. **Lead with the contribution = the evaluation.** "We contribute extensive benchmarks ..."
   — the benchmark is announced before any result.
4. **Specify the apparatus precisely.** A fixed set of N datasets with stated characteristics
   + a methodology that accounts for both model fit and hyperparameter search. *Precision
   signals rigor.*
5. **Report the result soberly, with scope.** [RED-LINE] "tree-based models remain
   state-of-the-art on medium-sized data" — note the **scope tag** ("medium-sized"). Borrow
   the scope tag; drop "state-of-the-art." Ours: "the edge holds on calm/low-activity bars
   and inverts on high-activity bars."
6. **Pivot from *what* to *why*.** "To understand this gap, we conduct an empirical
   investigation into ..." — turns a flat result into a mechanism study.
7. **Deliver mechanism as actionable structure.** Findings framed as a short numbered list of
   takeaways/challenges. (Reader leaves with a checklist, not a number.)
8. **Close with a reusable-asset offer.** Released benchmark + raw search data "to stimulate
   research." Contribution outlives the single result.

**Shape in one line:** concede rival -> unsettled question -> contribution-is-the-benchmark
-> precise apparatus -> sober scoped result -> pivot to *why* -> mechanism as list ->
reusable asset.

---

## For our abstract (synthesis, oriented)
Recommended ordered moves (pick the spine that fits the claims ledger):
1. Name the setting neutrally (intraday stock-direction prediction; many reported edges).
2. Plant the doubt via the *mechanism we fix*: standard evaluation leaks / multiplicity
   inflates apparent edges.
3. Announce the **contribution = the guarded protocol** (frozen choices, same-row dummy
   baselines, counted validation budget, CSCV/PBO discount, no final model selected).
4. State the near-null result **with its floor in the same sentence**: "+1.69pp validation
   macro-F1 over a ~0.50 dummy; +0.636pp guarded walk-forward at PBO ~0.51."
5. Pivot to the honest finding: the edge is **conditional/regime-dependent** (calm bars vs
   high-activity inversion), recurring across eras, with a microstructure confound left open.
6. Close: the protocol is the transferable asset; we map where the edge holds and where it
   inverts. **No "outperforms / best / significant."**

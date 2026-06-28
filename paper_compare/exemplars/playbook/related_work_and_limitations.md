# Related work (thread-based) + honest limitation craft

Two jobs: organize related work as *threads that converge on your gap*, and write limitations
that build trust instead of inviting rejection. Rule + paraphrased illustration + source.

---

## PART A — Thread-based related work

### A1. Group by theme/thread, not by paper
**Rule:** organize related work into a few named threads, each a bolded run-in paragraph;
within a thread, cluster citations and end on *how your work differs*. Never a chronological
citation list.
- *Illus. (Grinsztajn, §2):* threads are *deep learning for tabular data*, *comparisons
  between NNs and tree models*, *no standard benchmark*, *understanding the difference* — each
  gathers many citations and closes by positioning the paper.
- **Ours:** threads such as *reported intraday/short-horizon edges*, *evaluation-rigor &
  leakage*, *backtest-overfitting / multiplicity*, *conditional/state-dependent
  predictability* — each ends on the gap our protocol fills.

### A2. End each thread on the gap (the "but" sentence)
**Rule:** the last sentence of every thread states what is missing or unestablished, handing
off to your contribution. The gap is built incrementally, thread by thread.
- *Illus. (Grinsztajn, §2):* the comparisons thread ends by noting prior benchmarks used few
  datasets or biased methodology; the standard-benchmark thread ends "none are specific to
  tabular data." Each gap is the seed of a contribution.
- **Ours:** the edges thread ends "rarely evaluated under pre-committed, multiplicity-
  discounted protocols"; the conditional thread ends "intraday regime-dependence under strict
  evaluation is underexplored."

### A3. Claim novelty precisely and modestly
**Rule:** when claiming a first, scope it tightly ("to our knowledge, the first *empirical*
investigation of *why* ...") so it is defensible, not grandiose.
- *Illus. (Grinsztajn, §2):* novelty is claimed as the first empirical *why*-investigation —
  narrow, checkable.
- **Ours:** claim the contribution as "a pre-registered, multiplicity-discounted evaluation
  protocol for intraday direction, with a same-row dummy floor" — specific, not "the first to
  beat X."

### A4. Cite rivals fairly, then differentiate on design
**Rule:** describe the closest prior work accurately and credit it, then distinguish on a
concrete design axis (more datasets / tuning-cost accounting / stricter guards), not on tone.
- *Illus. (Grinsztajn, §2):* the "closest work" is named and credited, then separated by
  scope (more datasets, split by setting, tuning-cost-aware).
- **Ours:** credit the positive-coverage selective-classification foil (Chalkidis & Savani,
  ICAIF 2021) and differentiate by the floor-aware, pre-committed, PBO-discounted stance —
  we are its honest mirror, not its critic. (See `EXEMPLAR_PAPERS.md` #1.)

### A5. Authoritative-but-non-defensive tone about others' gaps
**Rule:** state the field's methodological weaknesses plainly and without sneering; let the
problem motivate you, not condemn others.
- *Illus. (Grinsztajn, §1-2):* "unequal hyperparameter tuning" and "no established benchmark"
  are stated as field facts that add evaluation noise — diagnostic, not accusatory.
- **Ours:** describe leakage/multiplicity as structural hazards of the setting (per Kapoor &
  Narayanan; Bailey et al.), framing our protocol as a constructive response.

---

## PART B — Honest limitation craft

### B1. A dedicated, up-front limitation block
**Rule:** give limitations their own labeled paragraph near the conclusion (not buried), as a
list of honest open questions.
- *Illus. (Grinsztajn, §6 "Limitation"):* an explicit paragraph listing open questions —
  behavior on very small / very large data, missing-value handling — stated as future work.
- **Ours:** a §9 limitation block naming: the bid-ask-bounce microstructure confound (left
  open), non-independent walk-forward windows, the near-floor effect size, single-market /
  single-label scope.

### B2. Name the confound you did NOT resolve, in the main text
**Rule:** the most credible move for a weak result is to name the alternative explanation you
could not rule out — visibly, beside the finding, not in a footnote.
- *Illus. (DLinear, conclusion):* openly concedes the baseline's limited capacity (can't track
  abrupt change points) — the weakness sits in the main text.
- **Ours:** state the microstructure (bid-ask-bounce) confound as an open competitor to the
  conditional edge, in §8 and §9.

### B3. Limitation paired with its contribution clause
**Rule:** pair each limitation with what the paper *does* deliver, so honesty doesn't read as
defeat. (Same "limit-in-the-same-breath" move as `weak_result_framing.md` #4.)
- *Illus. (DLinear / Grinsztajn conclusions):* the limited-capacity / open-questions admissions
  sit beside the reusable contribution (a competitive baseline; a reusable benchmark).
- **Ours:** "the effect is near-floor and the confound is open; nonetheless the protocol
  yields a reproducible, pre-committed yardstick and a regime map."

### B4. Conclusion = methodology-as-the-point, not a number
**Rule:** end on the durable contribution and an honest restatement of the scoped finding;
no triumphal effect-size claim.
- *Illus. (Grinsztajn, Conclusion):* the closing message is that *different methodologies give
  different results; a systematic benchmark reveals trends* — the method is the legacy. [RED-
  LINE] it still says "clear trends / outperform"; we soften to scoped, floor-relative wording.
- *Illus. (DLinear, Conclusion):* frames the contribution as "throwing out an important
  question" and a useful baseline, inviting future work — modest, forward-looking.
- **Ours:** close on the protocol as the transferable asset and the conditional map as the
  honest finding ("a weak edge survives strict evaluation; we map where it holds and where it
  inverts"). **No "outperforms / best / significant."**

---

## [RED-LINE] flags
- Both conclusions use strong verbs (`outperform`, `state-of-the-art`, `clear trends`). Keep
  the *thread-then-gap* and *limitation-then-contribution* structures; replace the verbs with
  ledger-bound red-line vocabulary.
- Keep the microstructure confound and the high-activity inversion in the main text — they are
  load-bearing for honesty, not blemishes to hide.

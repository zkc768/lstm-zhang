# Intro moves — earning a deflationary claim

How both papers march from problem -> gap -> question -> contribution, and how they earn the
right to a deflationary verdict before the reader resists. Each move is an actionable rule +
a paraphrased mini-illustration + source tag.

---

## The deflationary intro sequence (shared skeleton)

1. **Open on the uncontested ground.** Establish the task's importance plainly so no one can
   say you dismiss the field. *Rule: spend the first sentences being boring and fair.*
   - *Illus. (DLinear, §1):* time-series forecasting is long-standing and widely applied,
     and has moved from classical to deep methods. (Sets a neutral stage.)
   - *Illus. (Grinsztajn, §1):* deep learning drove real progress on image/text/audio. (Gives
     the rival its due first.)

2. **Localize the bandwagon you will question.** Name the specific sub-claim under scrutiny,
   with citations, without sneering. *Rule: quote the field's optimism faithfully, then
   question it — don't strawman.*
   - *Illus. (DLinear, §1):* a wave of Transformer variants now targets long-term forecasting
     and reports strong gains.
   - *Illus. (Grinsztajn, §1):* many recent papers claim to match or beat tree models, but
     those claims "have been put into question."

3. **Expose the structural reason the bandwagon may be hollow.** Give ONE clean mechanism or
   methodological gap that makes the optimism suspect. *Rule: the doubt must be earned by an
   argument, not asserted.*
   - *Illus. (DLinear, §1):* attention is permutation-invariant, yet order is the essence of a
     time series — so positional encodings only partly rescue it.
   - *Illus. (Grinsztajn, §1):* there is no established benchmark, so evaluations carry extra
     researcher degrees of freedom (uneven tuning, no variance accounting) -> noisy claims.

4. **Pose the question explicitly (often the title, restated and emphasized).** *Rule: convert
   the doubt into a falsifiable question the paper will answer.*
   - *Illus. (DLinear, §1):* it bolds the literal question "are Transformers really effective
     for long-term forecasting?"
   - *Illus. (Grinsztajn):* the title *is* the question; the intro re-poses it as "which
     inductive biases make tree models well-suited."

5. **State your hypothesis / posture before the evidence.** *Rule: tell the reader what you
   expect and why, so results read as confirmation, not luck.*
   - *Illus. (DLinear, §1):* not all series are predictable; long-horizon skill likely needs
     only trend + periodicity, which a linear map can already capture.

6. **List contributions as bullets — and make the *evaluation/instrument* a first-class
   bullet.** *Rule: name the simple comparator or the protocol as a contribution, not just the
   finding.*
   - *Illus. (DLinear, §1):* (i) first to challenge the assumption; (ii) introduce the simple
     linear baseline as a reusable comparator; (iii) comprehensive ablations on design
     elements.
   - *Illus. (Grinsztajn, §1):* (1) a new benchmark + inclusion/preprocessing methodology;
     (2) an extensive, tuning-cost-aware comparison; (3) an empirical *why* investigation.

7. **Close the intro on the deflationary thesis, scoped.** *Rule: say the deflation out loud,
   but bound it to the tested setting so it is defensible.*
   - *Illus. (DLinear, §1 close):* the temporal-modeling power of these models "is exaggerated,
     at least for the existing benchmarks." Note the scope clause.
   - *Illus. (Grinsztajn, §1):* tree models remain ahead on medium-sized data "even without
     accounting for" their speed advantage — bounded, fair.

8. **Add a roadmap sentence.** One line mapping the sections. (Grinsztajn does this
   explicitly at the end of §1; DLinear folds it into the contributions.)

---

## [RED-LINE] flags for our intro
- DLinear's deflation rides on **"outperforms ... by a large margin."** We replace the verb:
  our intro claims only that a **weak edge survives strict evaluation** and **exceeds the
  same-row dummy floor** — never "beats / best / significant."
- Both papers can afford a confident verdict because their effect is large. **Ours is
  near-null**, so our intro's confidence must attach to the **METHOD** (the protocol is
  sound, the guards are strict), while the **NUMBER** stays explicitly small and conditional.
  Move the confidence from the result to the evaluation.
- Keep the scope clause (move 7) non-optional: "in intraday equity bars, under this label and
  band" — it is what makes a modest claim safe.

## Our intro spine (oriented)
uncontested ground (intraday direction matters; many edges reported) -> bandwagon
(edges often reported under leaky/unguarded evaluation) -> mechanism gap (leakage +
multiplicity inflate apparent skill) -> question ("does any edge survive a pre-committed,
multiplicity-discounted protocol?") -> posture (we expect at most a weak, conditional edge)
-> contributions (the protocol as the headline contribution; same-row dummy baselines;
counted budget + PBO; the conditional map) -> deflationary-but-honest close (a weak edge
survives and is regime-dependent; confident in method, modest in number) -> roadmap.

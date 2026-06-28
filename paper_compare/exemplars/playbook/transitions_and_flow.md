# Transitions and flow — paragraph-to-paragraph connective tissue

Targets our **#1 problem: disjointed inter-paragraph logic** (PAPER_WORKFLOW.md step 4). The
exemplars rarely start a paragraph cold; each paragraph either answers a question the previous
one raised or sets up the next. Rule + paraphrased illustration + source.

---

## 1. Run-in topic headers that chain into a thesis
**Rule:** give each paragraph (esp. in related work / findings) a **bolded run-in phrase** that
names its job, and order the phrases so they read as an argument when skimmed.
- *Illus. (Grinsztajn, §2 & §5):* paragraphs open with bold leads like *deep learning for
  tabular data*, *comparisons between NNs and tree models*, *no standard benchmark* — skim the
  bolds and you get the gap. Findings reuse this: *Finding 1 ... / Finding 2 ... / Finding 3
  ...*
- **Ours:** in §2 and §8, use run-in leads that chain (e.g., *reported intraday edges* ->
  *why evaluation inflates them* -> *what a guarded protocol changes* -> *what survives*).

## 2. Question -> answer hand-off between paragraphs
**Rule:** end a paragraph on an explicit question or tension; open the next by answering it.
The seam becomes invisible because the reader is already asking.
- *Illus. (DLinear, §5.3):* the section advances as a chain of posed sub-questions — can these
  models use long inputs? do they preserve order? is efficiency real? — each its own
  paragraph that opens by answering the one just posed.
- **Ours:** §6->§7->§8 as a question chain: "does the edge survive in-sample validation?" ->
  "does it survive a guarded walk-forward?" -> "where does it live (which regime)?"

## 3. Close every paragraph on its consequence (no dangling evidence)
**Rule:** the last sentence of a paragraph states what the evidence *means* for the thesis, not
just what was observed. (PAPER_WORKFLOW principle "close every paragraph.")
- *Illus. (Grinsztajn, §5.2):* a result paragraph ends by tying the observation back to the
  inductive-bias claim ("NNs struggle to fit irregular targets"), not on a raw number.
- **Ours:** end each result paragraph with its bearing on the spine — e.g., "so the apparent
  edge is consistent with a regime effect, not a constant signal," rather than stopping at the
  statistic.

## 4. Forward-reference the payoff to create pull
**Rule:** when you defer something, name where it pays off, so the deferral feels intentional.
- *Illus. (Grinsztajn, §1 roadmap + "see Sec. X"):* explicit pointers ("Sec. 3 gives the
  methodology; Sec. 5 the empirical study") and "details in appendix" set expectations.
- **Ours:** "we localize this in §8" / "the discount is defined in §3 and applied in §7" — keep
  the reader oriented across our 9 sections.

## 5. Concession -> pivot connective (fairness then turn)
**Rule:** lead a transition with a genuine concession to the rival/limitation, then pivot with
a contrastive connector. Earns trust, then redirects.
- *Illus. (Grinsztajn, §1 / §2):* concede DL's real successes and that some hybrid methods are
  competitive, then pivot ("but their claims have been put into question").
- *Illus. (DLinear, §5.2):* concede that one Transformer is competitive on one dataset, then
  explain it away mechanistically (it borrows a classical inductive bias).
- **Ours:** concede that some intraday edges are reported and that our roster includes strong
  learners (LightGBM), then pivot to what the guarded protocol does to those edges.

## 6. Parallel structure across repeated units
**Rule:** when paragraphs do the same *kind* of work (each ablation, each finding, each guard),
give them the same internal shape: setup -> manipulation -> result -> meaning. Repetition of
*form* makes the section feel coherent even when content varies.
- *Illus. (DLinear, §5.3 ablations / Grinsztajn, §5 findings):* each unit follows an identical
  mini-template, so the reader learns the rhythm once.
- **Ours:** template each guard (§3) and each diagnostic (§8) identically: *what it tests ->
  how -> what we see -> what it rules out / where it localizes.*

## 7. Bridge sentences that name the logical relation
**Rule:** open a paragraph with a connector that states the relation to the prior one —
elaboration, contrast, cause, consequence, exception. Avoid cold restarts and avoid empty
"Moreover/Furthermore" that don't name a relation.
- *Illus. (DLinear, throughout §5):* "to validate this hypothesis ..." (cause->test),
  "another observation ..." (addition with a reason), "this is mainly caused by ..."
  (consequence). The connective always carries logic.
- **Ours:** prefer relation-bearing openers ("Because the split is chronological, ...";
  "Against this floor, the walk-forward edge ...") over decorative transitions.

---

## Connective-phrase palette (reword; relation-bearing only)
- **cause/test:** "to check whether ...", "because of X, we ..."
- **consequence:** "as a result", "this implies", "so the edge is best read as ..."
- **contrast/pivot:** "in contrast", "yet", "even so" (after a real concession)
- **localization:** "resolved by regime, ...", "restricted to calm bars, ..."
- **deferral:** "we return to this in §X", "defined in §3, applied in §7"
- **AVOID as empty filler:** bare "Moreover / Furthermore / Additionally" with no named
  relation; cold restarts that repeat the section title.

## Self-check (run on each section, ties to workflow step 4)
1. Does every paragraph's **first** sentence name its relation to the previous paragraph?
2. Does every paragraph's **last** sentence state a consequence for the spine?
3. Do the **bolded/leading** phrases, read alone, form the section's argument?
4. Is each deferral paid off by a named location?
5. Do repeated units (guards, ablations, findings) share one internal template?

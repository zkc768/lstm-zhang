# Flagged-items disposition (Pass B / Pass C leftovers) — final triage

Closes the "NOT APPLIED — flagged for user" lists in `passB_findings.md` and `passC_findings.md`
so they are not re-litigated every round (the old 60-round failure). Principle (ADR 0001 +
workflow anti-churn): **apply only objective, localized, zero-rhythm-risk fixes; leave subjective
prose-flow/style items with rationale.**

## APPLY (objective; batched after the Codex re-review, then re-gate + recompile)
- **§3 — define "balanced random prior" once** (≈0.498–0.500 even-class). Pass B logic C2: the term
  is used before its only local definition in §8. Objective gap.
- **Standardize the ≈0.498–0.500 label** to one term across abstract/§3/§8. Pass B minor-label
  variation ("even-class value", "random prior", "near-even floor"). Objective consistency.
- **§2→§3 seam — one bridging clause** linking the related-work gap to the protocol. Pass B I4
  "cold restart". The single highest-value transition; addresses the user's #1 concern
  (inter-paragraph logic) with one sentence, not a paragraph rewrite.

## LEAVE (documented — re-editing is net-negative per the reviewers' own judgment)
- **§6 methods digression / §7 internal / §8→§9 transitions** (Pass B I6/I7/I8): the question-chain
  and all five exemplar moves are confirmed present; rewriting risks homogenization (ADR 0001) + churn.
- **Negative-contrast "X, not Y" variety** (~12–15 discretionary; Pass C): most are
  governance-mandated red-line discipline ("not a clean test", "no final model"); mass-editing would
  be ironic homogenization.
- **§1 list-then-list de-stacking** (Pass C): §1 rated not-homogenized.
- **§5 residual medium-length run** (Pass C): further edits = proxy-gaming a 14-sentence section.
- **"estimand" dual-use** (Pass B I9): arguably correct — row-pooled vs equal-weight ARE different estimands.
- **§3 "Stage 00 freeze" jargon** (Pass B): reads as "initial data freeze".
- **Abstract omits calibration** (Pass B): 8-page hard limit; the conclusion covers it.

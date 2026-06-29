# DESIGN_TO_REVIEW — workflow fix (MVP v2, for Mode A round 2)

**For the Judge (Cowork), Mode A.** This is a revision of the round-1 design after your
verdict (`VERDICT.md`). Read only this file + `CONSTRAINT_CARD.md` in this folder. Write
findings to `VERDICT.md` (append a round-2 section).

**This file is Mode-A-only.** It is removed from `handoff/` before any Mode B run, so the
Mode-B rubric is the card alone, not this rationale.

---

## Problem (stated factually)

In the current paper, many positive statements are immediately followed by a self-negation
clause. A multi-step revision loop tends to re-introduce such clauses: one step removes one;
a later logic/style step judges a positive sentence under-qualified and adds one back. The net
effect over several steps is that a deliberate reduction is partly reversed. The target is to
stop that reversal without weakening any caveat the evidence requires.

## What changed from round 1 (your findings accepted in full)

Round 1 found the design's removal mandate unsound. All five required changes are adopted; the
design is narrowed so the unsound part is no longer in scope:

- **Dropped the classification-and-remove mandate.** The card no longer licenses removing or
  repositioning existing hedges (Q1: `¬floored ⇒ strippable` is invalid; Q2: deleting a
  bounding neighbor upgrades a token-identical positive past L5 + lexical gates). Removal is
  out of scope this round.
- **Kept only the anti-addition half** (`record-don't-execute`, R1), which deletes nothing and
  so does not carry the Q1/Q2 failure modes. This is the lever that targets the actual
  mechanism (a later step re-adding a hedge).
- **(a)** `¬floored ⇒ default-keep` (R3), never strip. **(b)** deletion adjacent to a
  ledger-bound positive is a justification event even with no survivor rewording; one floored
  caveat does not license removing an orthogonal bound (R4). Both are dormant until/unless
  removal is ever enabled.
- **(c)** the inject block now carries the per-scope floored set + the bound-co-location
  carve-out, and is shorter (fewer competing "highest-priority" lines).
- **(d)** the card is now operative-rules-only and neutral; all rationale (including this
  section) sits in this Mode-A-only file, out of the Mode-B channel.
- **(e)** this is the MVP you recommended: R1 + a diagnostic count on the existing `gate_L2`
  report + one positional rule. The heavier card/gate machinery is deferred until the metric
  shows it is needed.

## The MVP (mirrors the card; rationale here)

1. **R1 anti-addition** — the main lever. Stops the re-dilution loop at its mechanism without
   removing anything. Suppressed items are logged, batch-reviewed against the ledger by the
   Executor, and surfaced as a count/summary into `WHAT_CHANGED.md` (closing the round-1 Q6
   blind spot where suppressed caveats were invisible to the Judge).
2. **R2 positional** — one structural rule, with the round-1 Q4 carve-out (bound co-located,
   margin not the opening clause) folded into the inject block agents actually see.
3. **R5 diagnostic** — a before/after count (floored caveats per scope; total hedges; delta;
   suppressed-count) so "fixed" is distinguishable from "overshot." Diagnostic, not a gate.

The existing one-time edits (warmer abstract / contribution-first / conclusion reorder) already
reduced the standing excess; the MVP's role is to keep that from regressing, and to measure
whether any genuine excess remains. If R5 shows it does, removal is escalated — then, and only
then, under R3/R4.

## Stated assumptions / residual risks (please pressure-test)

- **Manifest is an allowlist, not a completeness oracle.** R3's default-keep is what
  compensates; if default-keep is itself unsafe somewhere, flag it.
- **R1 has a dual failure mode** (the honest mirror of round-1 Q1): if this round legitimately
  introduces a *new* claim that genuinely needs a *new* bound outside the two zones, R1 would
  suppress that bound. The intended safeguard: R1 **logs** (never silently drops), the count is
  surfaced to you, and the Executor adds any genuinely-required bound deliberately (with ledger
  context) rather than letting a generic agent add it mid-pass. **Is log-plus-batch-review a
  sufficient safeguard, or does a new-claim-needs-new-bound case need an explicit allowed path?**

## Red-team questions for round 2 (answer each in VERDICT.md)

1. **Does the MVP still solve the stated problem?** With removal out of scope, is preventing
   re-addition + the one-time positional pass enough, or is there a realistic case where
   standing excess remains that the MVP cannot touch?
2. **R1 dual failure mode** (above): is log + surfaced-count + Executor batch-review a
   sufficient safeguard against suppressing a legitimately-needed new bound?
3. **Signal sufficiency:** does surfacing a *count/summary* of suppressed items give you enough
   to verify none was load-bearing, or do you need the full suppressed text in `handoff/`?
4. **Abstract carve-out:** does "bound co-located + margin not the opening clause" actually
   prevent the round-1 Q4 center-of-gravity shift, or can impression still strengthen within
   200–220 words?
5. **Dormant guards:** is stating R3/R4 now (dormant) clearer, or does carrying dormant rules
   add confusion that argues for removing them until removal is actually enabled?
6. **Anything a cold reader of the paper would still flag** under this MVP.

## Out of scope
No new experiments / numbers / model selection. No softening of n=2 / scope / no-clean-test /
domain-separation caveats. Presentation only.

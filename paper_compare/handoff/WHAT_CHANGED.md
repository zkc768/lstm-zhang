# WHAT_CHANGED — Mode B run #2 (batch 2: §7 reorder + §07 D16 rebind + B1 thinning)

**Real change batch (NOT the baseline).** `REVIEW_THIS.pdf` was recompiled 2026-06-29 from the
edited source and overwritten in this folder (**8 pages**, 732639 B).

⚠️ **Do NOT judge by file size.** This batch is one sentence-pair *reorder* (§7), one
meaning-preserving 2-word *reword* (§07), and **one removed restatement** (§05). The byte size
barely moves. The change is in the TEXT, not the length. Verify by reading the spots below — not
by size. The full floor accounting for every touched caveat is in **`DEDUP_LOG.md`** (read it
alongside this file — especially the "Gate-behavior note for B1 records" at the top of the
Batch 2 section, which explains why `dedup_ok` is empty for a non-floored removal).

## Verify these exact text changes in the PDF

**1. §7 Guarded Walk-Forward (page ~5–6) — last paragraph now ENDS ON THE SURVIVING SIGN, not "flips."**
(This reorder was committed earlier; it is presented here for the batch-2 cold-read.)
- OLD ending: "…the direction holds weakly on its own segment… A stable pooled sign can still
  hide a direction that **flips** across conditions, and Section 8 resolves the same-row edge by
  activity to find that boundary."
- NEW ending: "…A stable pooled sign can still hide a direction that flips across conditions, and
  Section 8 resolves the same-row edge by activity to find that boundary. **What survives strict
  evaluation here is a predeclared sign, not a strong number: the direction holds weakly on its
  own segment, and only the predeclared candidate keeps a positive period lower bound.**"
- Pure last-two-sentence swap (no deletion, no rewording, no number change). The flip-pointer now
  *leads into* §8 instead of being the last word.

**2. §7 — D16 disclaimer reworded (floor re-bind, meaning identical).**
- OLD: "The observed five-of-seven positive periods … are descriptive context, **neither
  certification nor the bar**."
- NEW: "… are descriptive context, **not certification and not the bar**."
- Why: an earlier R2 reword to "neither…nor" silently broke the manifest tracker for this
  disclaimer (it tracks "not … and not the bar" / "not the bar"), leaving the floor *unbound*.
  The caveat was present and honest the whole time; this restores the tracked form. The 5/7 count
  still explicitly reads as **not a certification and not the bar**. (DEDUP_LOG record **R-3**.)

**3. §5 Experimental Setup (page ~4) — ONE redundant two-seed restatement removed.**
- REMOVED sentence: "Two seeds are too few to quantify seed-to-seed variance."
- KEPT (same paragraph): "…report the official validation outcome in macro-F1 **over n=2 seeds
  (101 and 202)**…" — so §5 still discloses the seed count; only the *limitation restatement* is gone.
- The two-seed limitation still appears, co-located with the actual positive margins, in **§6**
  ("Two seeds yield a descriptive spread rather than a variance estimate") and **§9** ("…rests on
  two seeds, too few for seed-to-seed variance"), and in the abstract. (DEDUP_LOG record **R-4** —
  includes the R4 adjacency check; this is the Q2 "upgrade-by-deletion" risk to verify.)

## NOT changed (so you don't look for what isn't there)
- **B1 applied yield is ONE removal (§5 D18), not the proposal's ~20+.** This is deliberate and
  governance-driven: the count-based estimate was overlap-inflated (one sentence matches many
  variants), and after excluding batch-1 files (abstract + §1, still under your review), the §9
  limitations zone (caveats belong there), figure/table captions + `\Description` (ACM-mandatory),
  factual ticker/interval definitions, and phrases that scope a specific number, the only
  genuinely-safe non-floored restatement left was the §5 two-seed sentence. Everything else was
  default-KEPT (R3) — see the "Considered-but-KEPT" list in `DEDUP_LOG.md`.
- **Abstract + §1: UNCHANGED in batch 2** (they are your batch-1 review scope; not re-touched).
- **§9 conclusion: UNCHANGED.**
- No number, no claim-strength, no domain-fusion change anywhere.

## Gate evidence (Executor side; you still read only the PDF + these .md files)
- §5: L1/L2/L3/L4/L5 all pass. No floored scope touched (D18 floors = abstract/§6/§9; §5 is not a
  floor). `missing_required=[]`, `floor_unbound=[]`, `forbidden_introduced=[]`.
- §7: L1/L2/L3/L4/L5 all pass. D16·5of7_desc·§07 floor now **bound** (orig 0 → 2). No other change.
- Whole paper recompiles to **8 pages**; `check_integrity.py` PASS on both changed sections.

## Focused cold-read asks (your round-2 verification criteria)
For **§7 and §5** (and a glance at the document-level honesty):
1. Does §7 now close on the surviving predeclared sign rather than "flips"? (metric: units closing
   on negation 5 → 2, per the committed §F pass.)
2. Did the §5 removal or the §7 D16 reword **drop or soften any floored caveat**? The gate says
   floors hold (two-seed still in §6/§9/abstract; the 5/7 disclaimer still denies certification and
   the bar); confirm by reading.
3. Did removing the §5 two-seed sentence create an **implicit claim-upgrade** (round-1 Q2)?
   Specifically: with that sentence gone, does §5's "over n=2 seeds" read as *sufficient* rather
   than *thin*? (Executor judgement: no — §5 states no positive margin there, and the limitation
   stays attached to the margins in §6/§9. Please verify independently — DEDUP_LOG R-4.)

Write findings to `VERDICT.md` under "## Mode B — batch 2 (§7 + §5 B1)".

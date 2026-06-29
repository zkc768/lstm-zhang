# WHAT_CHANGED — Mode B run #1 (§F tone pass, batch 1: abstract + §1)

**Real change batch (NOT the baseline).** `REVIEW_THIS.pdf` was recompiled 2026-06-29 from the
edited source and overwritten in this folder (8 pages).

⚠️ **Do NOT judge by file size.** This batch is mostly *reordering* (same words, new order) plus
minor rewording, so the byte size barely moves (732742 B vs baseline 732702 B, +40 B). The change
is in the TEXT, not the length. Verify by reading the two endings below — not by size.

**Scope note (you flagged this, 2026-06-29 — correct):** this batch is *not* purely reordering. It
also includes **two logged removal/reposition edits** — D9 bid-ask fold, and D24·anti_leak 2→1
dedup (a floor-touching edit). Removal is now formally IN SCOPE (user approved B1+F; card updated,
R3/R4 LIVE). Both edits are recorded with their **verbatim gate_L2 floor accounting** in
**`DEDUP_LOG.md`** — read it alongside this file; the D24 one is exactly the Q2 risk to verify.

## Verify these exact text changes in the PDF

**1. Abstract (page 1) — now ENDS ON THE CONTRIBUTION, not a caveat.**
- OLD ending: "…so the protocol's sensitivity to a genuine signal is **untested**."
- NEW ending: "…with no known-signal positive control. This is a worked case for the protocol,
  not yet a test on a signal known to be real. **The transferable contribution is the protocol
  and its diagnostics.**"
- Also: the standalone "We cannot yet separate this pattern…" was folded into the conditional
  sentence (one fewer free-standing negation).

**2. §1 Introduction (page 1–2) — last paragraph now ENDS ON THE CONTRIBUTION.**
- OLD ending: "…is the positive-control **next step**."
- NEW ending: "…a conditional sign that a headline-only readout would hide. **The diagnostics
  map where this edge persists and where it reverses.**"
- Pure sentence-reorder (no deletion / no rewording / no number change). The opening ("…can
  survive scrutiny, or it can be an artifact") was kept on purpose — it states the paper's
  central question, not throat-clearing.

## NOT changed (precise, so you don't look for what isn't there)
- **§9 conclusion: UNCHANGED.** Its closing already ends on the contribution clause ("the
  transferable contribution is the evaluation protocol and the diagnostics…"); the word
  "breaks" sits *inside* that contribution clause. §9 was never a closing-on-negation target.
  If you still read it as half-deflated, flag it and the Executor will revisit.
- **§7 (closes on "flips"): NOT done yet** — next batch.
- No B1 cross-section thinning yet.

## Gate evidence (Executor side; you still read only the PDF)
- Abstract: L1/L3/L4/L5 pass. Only floor touch = D24·anti_leak·main.tex 2→1 (`dedup_ok`,
  floor=1 still met — "no known-signal positive control" retained). All numbers intact; every
  sentence ≤35 words.
- §1: L1/L3/L4/L5 pass; zero floor change (reorder only).

## Focused cold-read asks (your round-2 verification criteria)
For the **abstract and §1 only**:
1. Do they now close on a contribution rather than a caveat? (target metric: units closing on
   negation 5 → 3.)
2. Did the reorder/rewording **drop or soften any floored caveat**? (Abstract: n=2 /
   not-a-clean-test / not-economic-value / no-positive-control.) The gate says floors hold;
   confirm by reading.
3. Did moving a bound create an **implicit claim-upgrade** (round-1 Q2)? Especially: does ending
   the abstract on "the transferable contribution is the protocol and its diagnostics" make the
   empirical edge read as stronger / more validated than the body supports?

Write findings to `VERDICT.md` under "## Mode B — batch 1 (abstract + §1)".

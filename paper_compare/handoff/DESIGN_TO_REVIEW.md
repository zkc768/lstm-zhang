# DESIGN_TO_REVIEW — workflow fix for the "over-hedging" problem

**For the Judge (Cowork), Mode A.** This is the Executor's proposed fix for a problem the
user + a web model diagnosed in the paper. **It has NOT been committed to any governance file.**
Your job: red-team this design *before* it is implemented. Write findings to `VERDICT.md`.

You may read, in this folder only: this file + `CONSTRAINT_CARD.md`. Do **not** pull in the
repo's design docs / agent transcripts — fresh eyes are the point.

---

## The diagnosis (symptom)

The paper reads defensive: nearly every positive statement is immediately followed by a
self-negation. It reads like apologizing, not like a paper with a thesis. A multi-step
revision workflow keeps **re-diluting** any attempt to fix this: step 1 removes a hedge per
the diagnosis; a later "check logic / match journal style" step adds one back because a
positive sentence "looks under-qualified." Three steps later the fix is half-gone.

## Root cause (Executor's claim — please challenge it)

The project's governance is **asymmetric — all ceiling, no floor on hedging:**

- 8 grep gates + red lines catch *overclaiming* (`best/outperforms/profitable/...`) → a
  ceiling that pushes prose **away** from positive.
- The hedge-floors system (`gate_L2`, `floor = min(min_count, orig_hits)`) **protects**
  hedges from deletion → a floor that locks hedges **in**.
- Red lines also mandate "the conditional edge is a limitation, not a selling point."

So **every force pushes toward more hedging; nothing caps it.** The defensive tone is the
system's stable equilibrium, not an agent accident. Adding a hedge is always the "safe"
direction, so any reviewer step drifts that way.

## Proposed fix

1. **A Constraint Card** (see `CONSTRAINT_CARD.md`) that adds the *missing* direction: a
   **ceiling on discretionary hedges** + positional rules (contribution-first, abstract
   ≤220w, Intro excludes §3 mechanics) + a **record-don't-execute** rule. It is injected
   into **every** agent prompt (rides the existing precedence-stack injection), so it cannot
   be diluted by a later step.
2. **The classification is mechanizable, not subjective:** a hedge is *data-required* iff it
   matches a **floored D-lock variant** in that scope (per the existing
   `protection_manifest.json`); everything else is *discretionary*. So the card targets only
   non-floored hedges — it can never (by construction) strip a caveat the manifest requires.
3. **Optionally mechanize it** as a Pass-C "discretionary-hedge ceiling" warn in
   `check_integrity.py` (same machinery as `gate_L2`), so the constraint is enforced by a
   script, not by memory — the proven way to stop dilution.
4. **Safety net (why this is not a claim-upgrade):** the ceiling only removes/repositions
   non-floored hedges; the existing `gate_L2` floors + **L5 monotonicity** (a survivor
   reworded conditional→assertive = ≥MAJOR) + Codex review guarantee no data-required caveat
   is lost and no survivor is strengthened. Ceiling and floor are orthogonal and compose.

## Architecture (two roles, one thin interface)

- **Executor = Claude Code** (local toolchain: gates, compile, git, `codex exec`, subagents).
- **Judge = Cowork** (you): fresh-eyes design review now (Mode A), acceptance review later
  (Mode B). Reads only `handoff/`. The Constraint Card is the shared contract.

---

## Red-team questions (please answer each in VERDICT.md)

1. **Classification soundness.** Is "floored D-lock variant = data-required, else
   discretionary" actually watertight? Find a hedge that is *genuinely required for honesty*
   but is **not** a floored D-lock variant — i.e. a caveat the card would wrongly treat as
   discretionary and let an agent strip. If such cases exist, the card needs a fallback.
2. **Claim-upgrade leak.** Construct a failure path where applying the ceiling makes the
   residual sentence read *more assertive than the ledger permits*, yet slips past L5 +
   Codex. Does the safety net actually hold?
3. **Independence leak.** Does the Constraint Card itself (a shared artifact written by the
   Executor) smuggle Executor framing into your judgment — eroding the independence the
   two-role split is meant to give? If so, what should be removed from the card?
4. **Red-line / spine collision.** Do the positional rules (contribution-first; hedge zones)
   collide anywhere with the red lines or the Option-2 honest-numbers spine — e.g. could
   "contribution leads" pressure the abstract toward an implicit overclaim?
5. **Over-engineering.** Is there a simpler fix that gets ~80% of the benefit without a new
   card + a new gate? (e.g. a single positional rule + reusing an existing gate.)
6. **Anything the Executor missed** that a cold reader of the paper would flag.

## Out of scope (do not propose changing these)

No new experiments / numbers / model selection. No softening of n=2 / scope / no-clean-test /
domain-separation caveats. The fix is presentation-only.

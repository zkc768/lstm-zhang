# R2 Constraint Card — operative contract (MVP v2)

**This file is rules only.** No rationale, no problem-narrative, no project history — those
live in `DESIGN_TO_REVIEW.md` (a Mode-A-only file, removed from this folder before any Mode B
run) so they cannot color the Mode-B rubric. Revised after Mode A round 1 (see VERDICT.md).

**Precedence:** below red lines, above the 30 generic principles + humanizer. **Never**
overrides `AGENTS.md` / claims ledger / red lines / hedge floors (`gate_L2`) / L5 monotonicity.
**Floor wins every conflict** — a floored caveat stays exactly where the manifest pins it.

**Scope this round:** prevent re-dilution + keep the contribution-forward structure standing.
**Active removal/repositioning of EXISTING hedges is OUT OF SCOPE this round** (it is where the
round-1 review found the failure modes). It is enabled only if R5's metric shows dilution
persists after R1+R2, and only under the R3/R4 guards.

---

## R1 — No net-new hedge outside the two zones (the main lever; removes nothing)

- No step may **add** a hedge / caveat / self-negation **outside** the two designated zones:
  the **abstract closing block** and **§9 (limitations)**.
- A step that judges one is "needed" elsewhere does **not** add it. It **logs** it
  (`file:line` + proposed text + reason) and continues. The Executor reviews the log in batch
  against the ledger; a **count + summary** of logged items is surfaced into `WHAT_CHANGED.md`
  so the Judge can see what was suppressed.
- This rule **deletes nothing** — it only blocks net-new additions. (That is why the round-1
  removal failure modes do not apply to it.)

## R2 — Positional (one rule + the abstract carve-out)

- Abstract **opens on the protocol / diagnostic contribution**, active voice.
- The **empirical margin is not the opening clause.** Wherever any conditional / empirical-edge
  claim appears, its **scope bound is co-located** — same or immediately adjacent sentence
  (frozen validation split / not out-of-sample / n=2) — **never deferred** to the closing block.
- Abstract **200–220 words**. Intro names the protocol idea in ~2 sentences; **no §3 mechanics**
  (validation-budget / PBO / bootstrap) in the Intro or abstract.

## R3 — Default-keep for unregistered caveats *(guard; dormant until removal is enabled)*

- A hedge that is **not** a floored D-lock variant is **not** therefore removable.
  `¬floored ⇒ default-KEEP, needs explicit adversarial judgment to touch`. **Never**
  `¬floored ⇒ strip`. The manifest is an allowlist of known-protected caveats, **not** a
  completeness guarantee that everything else is discretionary.

## R4 — Deletion is a justification event *(guard; dormant until removal is enabled)*

- Deleting or relocating any hedge **adjacent to** (same or neighboring sentence) a
  ledger-bound positive is a **≥MINOR event requiring written justification, even if no
  surviving token changes** — this guards against claim-upgrade-by-deletion-of-context, which
  L5 (per-survivor rewording) does not see.
- The presence of **one** floored caveat does **not** license removing a **different,
  orthogonal** bound (n=2 ≠ in-sample-only ≠ macro-F1≠economic-value).

## R5 — Diagnostics (report, do not auto-act)

- Per de-hedge-relevant pass, count and report (piggyback the existing `gate_L2` report):
  floored caveats per scope; total hedge-like phrases; delta vs the prior pass; count of
  suppressed-and-logged would-be additions (R1).
- **Diagnostic only** (ADR 0001 style): it flags "fixed vs pendulum-overshot," it never
  auto-edits. A document-level honesty read ("did de-hedging move the paper from honestly-weak
  to misleadingly-confident?") is the Judge's Mode-B job + Codex, not this counter.

---

## What this card is NOT

Not a claim-strength change. Not a number change. Not permission to drop or relocate a floored
caveat (floor wins). Not "make it positive by weakening the bounds." Every caveat the ledger
requires stays.

## Inject block (verbatim into each agent prompt this round)

> Must be injected **together with the per-scope FLOORED SET** — without it an agent cannot
> apply "floor wins" / R3.

```
PRESENTATION CONSTRAINTS (this round; subordinate to AGENTS.md / ledger / red lines / floors):
1. Do NOT add any hedge/caveat/self-negation outside §9 and the abstract closing block. If one
   seems needed elsewhere, LOG it (file:line + text + why) and continue — do NOT add it.
2. Abstract opens on the protocol/diagnostic contribution (active voice); the empirical margin
   is NOT the opening clause. Any conditional/edge claim carries its scope bound (frozen
   validation split / not out-of-sample / n=2) in the SAME or adjacent sentence — never deferred.
3. Abstract <=220 words. No §3 mechanics (validation-budget/PBO/bootstrap) in Intro or abstract.
4. Do NOT remove or move ANY caveat this round (removal is out of scope). A phrase NOT in the
   FLOORED SET below is still default-KEEP — never treat "unregistered" as "safe to delete."
5. No claim-strength change, no number change. Floor wins every conflict.
FLOORED SET for this scope: <inject the manifest's floored D-lock variants for this section>
```

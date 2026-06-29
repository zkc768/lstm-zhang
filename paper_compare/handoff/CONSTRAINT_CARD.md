# R2 Constraint Card — DRAFT (pending Cowork Mode-A review)

**目的**：把"论文该有主张、不要过度自我否定"这个判断，从一次性 work item 升级成
**每一步都携带、不可被后续步骤稀释**的标准约束（网页版说的"外框"）。这张卡解决的是
**presentation**（hedge 的位置与重复、contribution 的位置），**绝不**碰任何数字或主张强度。

> **Status:** DRAFT. NOT yet wired into governance. Reviewed in Mode A first; only after
> a clean verdict does it get promoted into the precedence stack + (optionally) a Pass-C gate.

## Precedence (插在哪一层)

This card sits **just below the red lines, above the 30 generic principles + humanizer**
(`PAPER_WORKFLOW.md §2`). It therefore **outranks** the generic reviewer principles that
cause hedge-drift, but **never** overrides:

1. `AGENTS.md` (safety / no fabrication)
2. claims ledger + red lines + three-evidence-domain separation
3. **hedge floors (`gate_L2`) + L5 hedge-monotonicity**

> **Conflict rule:** if this card and a hedge floor ever disagree, **the floor wins.** A
> data-required caveat stays exactly where the manifest pins it. This card can never be a
> reason to remove, relocate, or soften a floored caveat.

---

## 1. Two kinds of hedge — and the line is already drawn by the manifest

The classification is **not a new subjective judgment.** It reuses
`paper/scripts/...protection_manifest.json`:

- **Data-required caveat** = a phrase that matches a **floored D-lock variant** in that
  scope (e.g. `D18` n=2 → `main.tex/§06/§09`; `D23` macro-F1≠economic-value; `D24`
  no-positive-control; domain labels; `D6` frozen-band/no-sensitivity).
  → **Keep. Do not move. Do not drop below its floor.** Protected by `gate_L2` + L5.
- **Discretionary hedge** = hedge-like phrasing that is **NOT** a floored D-lock variant in
  that scope. Defensive throat-clearing. Examples: a repeated "though this cannot prove X"
  *after* the bound is already stated; "it is worth noting that" / "we emphasize that"; a
  4th/5th self-negation piled into the abstract; restating "makes no architecture claim"
  more times than the floor requires; generic self-flagellation not tied to a number.
  → **This is the only thing this card governs.**

> Operational test for any hedge: *"Is it a floored D-lock variant in this scope?"*
> Yes → data-required, untouchable. No → discretionary, subject to §2–§3 below.

## 2. Discretionary-hedge ceiling

- Discretionary hedges **may** appear, but must **not** be scattered after every positive
  clause. A positive statement that already carries its floored caveat does **not** get a
  second discretionary self-negation appended.
- Concentrate discretionary hedges in the **designated zones**: the **abstract closing
  block** and **§9 (limitations)**. Each data-required caveat still appears at its floored
  location regardless of these zones.
- Net effect target: **same number of data-required caveats; fewer discretionary
  restatements; reads as "I did this, it has value, here are the bounds" — not "I did this,
  but it might be nothing."**

## 3. Positional rules

- **Contribution leads.** Abstract opens on the contributions (protocol / sign-consistent
  TCN margin over same-row dummy on frozen validation / diagnostics) in confident active
  voice — not on a negation. Intro states the three contributions in the contribution ¶,
  not buried after pages of caveats. (Already achieved in WI-1/WI-2 — this card makes it
  **standing**, so the next pass cannot regress it.)
- **Abstract length:** hold the existing **200–220 word** budget.
- **Intro excludes §3 mechanics.** Introduction names the protocol's idea (frozen splits,
  same-row dummy, validation-budget ledger, three separated domains) in ~2 sentences;
  the *mechanics* live in §3. No validation-budget/PBO/bootstrap detail in the Intro.

## 4. record-don't-execute (这是防"被稀释"的关键)

If, during logic-check / polish / style-conformance / consistency, any step **"wants"** to:
- add a caveat or self-negation **outside** the designated zones, or
- add §3 protocol mechanics into the Intro/abstract, or
- soften a positive framing that is already ledger-bound and red-line-safe,

then **DO NOT do it. Log it** (file:line + what it wanted to add) in the pass notes and move
on. (Same discipline as ADR 0001 burstiness: *diagnostic, not auto-apply.*) The Executor
reviews logged items in batch; none are applied silently.

## 5. What this card is NOT (safety)

- **NOT** a claim-upgrade. It changes hedge *position/repetition*, never claim *strength*.
  No number changes. No `best/outperforms/significant/profitable/well-calibrated/clean-test/
  final-model`. The Option-2 spine (confident method, honest weak numbers) is unchanged.
- **NOT** permission to delete or relocate a floored (data-required) caveat. Floor wins.
- **NOT** "make it positive by weakening the bounds." Every caveat the ledger requires stays.
- The safety net is the existing stack: `gate_L2` floors keep data-required caveats; **L5
  monotonicity** flags any surviving hedge reworded conditional→assertive (≥MAJOR); Codex
  adversarial review checks no overclaim crept in. This card only operates inside that net.

---

### Inject-into-every-agent-prompt block (copy verbatim into each reviewer/polisher prompt)

```
HIGHEST-PRIORITY PRESENTATION CONSTRAINTS (this round, no step may violate):
1. Contribution leads (abstract opening + Intro contribution paragraph); never open on a negation.
2. Discretionary hedges (= hedges NOT pinned by a floored D-lock in this scope) only in the
   abstract closing block and §9. Never append a 2nd self-negation to a positive clause that
   already carries its floored caveat.
3. Abstract ≤220 words. Intro names the protocol idea in ~2 sentences; no §3 mechanics
   (validation-budget/PBO/bootstrap) in Intro or abstract.
4. record-don't-execute: if you find a spot that "needs" a caveat/§3-detail outside the
   allowed zones, DO NOT add it — log file:line + the wanted text, and continue.
5. NEVER override AGENTS.md / ledger / red lines / hedge floors. A data-required (floored)
   caveat stays exactly where it is — the floor wins every conflict. No claim-strength change.
```

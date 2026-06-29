# VERDICT — Mode A (design review)

**Role:** Judge (Cowork), fresh-eyes. Read only `handoff/` (README, DESIGN_TO_REVIEW, CONSTRAINT_CARD). No repo files read. No files modified except this one. No scripts run.

**Bottom line:** **PASS WITH REQUIRED CHANGES — not a clean pass.**
The diagnosis (asymmetric governance: ceiling on overclaim, no ceiling on hedge) is correct and worth fixing, and `record-don't-execute` is the genuinely good idea here. But **two load-bearing claims in the design are unsound as written**, and both map directly onto the two failure classes flagged for this review:

- **"floored D-lock variant = data-required, else discretionary" is NOT watertight** → the card *can*, by construction, let an agent strip a caveat that honesty requires (the "误删必要 caveat" class). See Q1.
- **The safety net (L5 + lexical gates) does NOT catch claim-upgrade-by-deletion** → removing a neighboring hedge can strengthen a ledger-bound sentence's *pragmatic* force while every survivor token stays identical and lexically clean (the "隐性 claim-upgrade" class). See Q2/Q4.

Required changes are listed at the end. Until (a)–(c) are made, do not promote the card into the precedence stack.

---

## Red-team answers

### Q1 — Classification soundness (NOT watertight)

The card equates **"registered in `protection_manifest.json` as a floored D-lock variant"** with **"required for honesty."** These coincide only if the manifest is provably *complete* and covers *every scope the revision can create*. Neither holds. Three concrete gaps:

1. **Floor = min(min_count, orig_hits) gives zero protection in scopes with zero orig_hits.** The floor system protects *pre-existing* caveats at their *original* locations. It does not mint a floor for a caveat that becomes necessary because the revision **introduces or relocates a positive claim into a new scope.** This is not hypothetical — the card itself *pushes claims into new scopes* (§3 "contribution leads," "Intro states the three contributions"). A crisper positive sentence about the TCN margin placed in the Intro contribution paragraph honestly needs "on the single frozen 2018–2019 validation split, not out-of-sample." In the Intro scope that caveat has no orig_hits (mechanics were excluded from Intro by the same card) → not floored → classified **discretionary** → strippable. **The positional rule and the classification gap jointly manufacture the failure, in exactly the zone the card makes more assertive.**

2. **Variant matching is finite; honest phrasing is open-ended.** D-lock matching tests against an enumerated variant set. An honestly-necessary caveat worded outside that set does not match → discretionary. The manifest is a curated allowlist, not a semantic detector.

3. **Orthogonal bounds collapse to one.** A single sentence can need several independent caveats (n=2 **and** in-sample-only **and** macro-F1≠economic-value). If only one of those is a floored variant in scope, the card's rule "a positive statement that already carries its floored caveat does not get a second discretionary self-negation" (§2) licenses stripping the *other, orthogonal* honesty-required bounds. One floored caveat does not bound a multi-dimensional claim.

**Required fallback:** treat "not floored" as **"not auto-protected → default-keep, needs adversarial judgment,"** not as "discretionary → strippable." The dangerous inference is `¬floored ⇒ safe to remove`; that inference is invalid.

### Q2 — Claim-upgrade leak (the safety net does NOT hold)

Failure path that slips past L5 + lexical gates:

- Sentence A (ledger-bound, **tokens unchanged**): *"The TCN shows a sign-consistent margin over the same-row dummy on frozen validation."*
- Sentence B (next clause, classified discretionary): *"We emphasize this cannot establish out-of-sample profitability or generalization."*

The ceiling deletes B as "a 2nd self-negation appended to a positive clause." Now:
- **L5 sees nothing** — it flags a *survivor reworded* conditional→assertive. A was not reworded; it is token-identical. Deletion of a *neighbor* is not a rewording event.
- **Lexical gates see nothing** — A contains no banned token (`best/outperforms/profitable/...`).
- **Codex** *might* catch it only if it reads at discourse level, but the design presents L5 + gates as the *guarantee* and Codex as backup. The guarantee is unsound.

Yet the paper now reads stronger: B was carrying A's out-of-sample/generalization bound; with B gone, the reader infers the margin generalizes. **This is claim-upgrade by deletion of context** — invisible to per-survivor, per-token checks. The card's §2 rule actively *invites* this, and §5's "never a claim-strength change" is true only at the lexical level; pragmatic strength is unguarded.

**Required fix:** deleting/relocating a hedge that shares a sentence or adjacent-sentence scope with a ledger-bound positive must itself be a monotonicity/justification event (≥MINOR, requires explicit justification), **even when no survivor token changes.** And "one floored caveat present" must not license removing caveats that bound a *different* dimension.

### Q3 — Independence leak (yes, material)

The card is not a neutral rubric; it is an **Executor-authored persuasive brief**, and in Mode B the Judge uses it as the rubric. It smuggles framing three ways:

- **Loaded labels** pre-decide the disputed content: "defensive throat-clearing," "generic self-flagellation," "it might be nothing." A fresh-eyes Judge reading these is primed to see hedges as faults rather than as honesty.
- **Contested premises stated as settled:** "The classification is not a new subjective judgment," "it can never (by construction) strip a caveat the manifest requires." Q1/Q2 show these are false, yet they would enter Mode B as ground truth and suppress the very search that matters.
- **Cross-channel credit:** "(Already achieved in WI-1/WI-2)" asks the Judge to accept repo work it is forbidden to see.

Irony worth flagging: independence is "guaranteed by what's *not* in the folder," but the one file that *is* in the folder is a brief arguing the design's own case. The thin-interface discipline guards against transcripts, not against a loaded contract.

**Required removal for Mode B:** split contract from rationale. Keep in `handoff/` only the operative rules (precedence position, floor-wins conflict rule, two-zone ceiling, positional rules, abstract budget, record-don't-execute, the verbatim inject block). Move all argumentation ("symptom/root-cause/why-this-isn't-a-claim-upgrade," the labels, the "by construction/never," WI-1/WI-2 credit) out of the Judge's channel.

### Q4 — Red-line / spine collision (yes, residual)

Direct collision: red line "the conditional edge is a limitation, not a selling point" vs card §3 "Contribution leads. Abstract opens on the contributions … in confident active voice — not on a negation." **If the conditional edge is among the contributions, "lead confidently with contributions" pressures presenting the edge as a selling point.** §3's full text threads this (contributions = protocol/diagnostics; margin framed with its frozen-validation bound), but the **inject block** agents actually see is the blunt version: "Contribution leads … never open on a negation." Agents operationalize the blunt version.

Mechanism of overclaim *without a banned token*: "never open on a negation" + "concentrate discretionary hedges in the abstract closing block" + "≤220 words" jointly **move the bounding material into a smaller, later slot and expand the confident opening.** The abstract's center of gravity shifts toward the claim — within budget, lexically clean, but stronger in impression. The lexical gates are blind to this because it is structural, not lexical.

**Required carve-out:** the abstract's confident opening must **co-locate** (same or immediately adjacent sentence, not deferred to the closing block) the scope bound for any conditional-edge claim. "Contribution leads" applies to the *protocol/diagnostic* contributions; the empirical margin may not be the abstract's opening clause. Put this in the inject block, not only §3.

### Q5 — Over-engineering (yes — an MVP gets ~80%)

The real disease is **re-dilution across steps**; hedge multiplicity is the symptom. The single highest-leverage lever is **`record-don't-execute` alone**, applied to the existing workflow: forbid any step from *adding* hedges outside the limitations/abstract-closing zones, log-only. That kills the "later step adds one back" loop — the exact mechanism the diagnosis blames — **with no new classification taxonomy, no new precedence layer, and no new gate.** Pair it with a *diagnostic-only* hedge-insertion count piggybacked on the existing `gate_L2` report (it already counts hedges), plus one positional rule (abstract opens on protocol contribution, bounds co-located).

The full design's extra cost buys little over this MVP and adds the risk surfaces in Q1/Q2/Q4 (a new precedence layer to conflict with, an unsound classification line, an optional new gate to maintain). **Recommend piloting the MVP first; add the card+gate only if dilution persists.** (Caveat: the one-time positional/contribution-first edits are real value, but "standing" enforcement of position is served by a checklist item, not a whole subsystem.)

### Q6 — What a cold reader would also flag

- **Does the thesis survive de-hedging?** For an n=2, single-frozen-split, no-positive-control finance result, the hedges may be *load-bearing for credibility*, not just tone. The design has no document-level check for "did de-hedging move the paper from honestly-weak to misleadingly-confident?" If the honest residual is "on one split a TCN sign-matches a dummy; can't show it generalizes or pays," a cold reviewer may find the de-hedged version *overclaims relative to evidence*. (Ties to Q2/Q4.)
- **No metric for the problem or for success.** "Nearly every positive statement is followed by a self-negation" is asserted, not counted; "net effect target" is qualitative. Define a before/after count of discretionary vs data-required hedges so you can tell "fixed" from "pendulum overshot."
- **`protection_manifest.json` is a single point of failure.** The whole safety argument rests on its correctness and completeness, which neither role validates in this loop. List "manifest completeness" as an explicit risk/assumption, not an unstated premise.
- **"Inject into every prompt" risks instruction overload.** Five "highest-priority" constraints in every prompt compete with task instructions and with the *actual* top priority (AGENTS.md/ledger); agents may comply lexically while missing intent.
- **The log backlog is invisible to the Judge.** Items "reviewed in batch by the Executor" never reach `handoff/`. The thing most likely to erode honesty — caveats that *wanted* to be added but weren't — lives precisely in the channel the independent check cannot see. Consider surfacing a count/summary of logged items into `handoff/`.

---

## CONSTRAINT_CARD.md audit (clarity / landability / conflicts)

**Clear & checkable:** designated zones (abstract closing + §9); abstract 200–220w; "Intro excludes §3 mechanics"; floor-wins conflict rule; record-don't-execute as a discipline. Good.

**Landability defects:**
- **Nuance lives where agents can't see it.** §1–§3 carry the qualifications that prevent the Q1/Q2/Q4 failures; the **inject block** agents receive is the blunt version. The safety qualifications are not in the operative text. Fix: fold the per-scope guards into the inject block.
- **"Floor wins" is unenforceable at the point of action** unless each agent prompt carries the **per-scope floored set.** The inject block does not include it. An agent cannot tell a floored variant from a discretionary one without the manifest in front of it, so "floor wins every conflict" is aspirational as written. Fix: inject the scope's floored list alongside the rules.

**Red-line conflicts:** structurally the card subordinates itself correctly (precedence section + conflict rule defer to AGENTS.md/ledger/red lines/floors/L5). But the card's own safety claim — "never a claim-strength change" — is guaranteed **only at the lexical level.** Q2/Q4 show a positional/deletion rule can shift pragmatic claim strength with zero token change, and the card has no rule preventing that. So the card's central safety promise is not entailed by the card's rules.

---

## Required changes before promotion

(a) **Invert the default for unregistered caveats:** `¬floored ⇒ default-keep, needs adversarial judgment`, never `⇒ strippable`. (fixes Q1)
(b) **Make hedge-deletion adjacent to a ledger-bound positive a ≥MINOR justification event even with no survivor rewording**, and forbid "one floored caveat" from licensing removal of orthogonal bounds. (fixes Q2)
(c) **Put the safety qualifications + the per-scope floored set into the inject block**, and add the abstract carve-out (co-locate the conditional-edge bound; margin is not the opening clause). (fixes Q4 + landability)
(d) **Strip persuasive framing from the Judge's channel**; keep contract, move rationale out. (fixes Q3)
(e) **Consider piloting record-don't-execute + gate_L2 hedge-count MVP first**; add card/gate only if dilution persists. Define the discretionary-vs-data-required count metric up front. (Q5/Q6)

**Disposition:** conditional pass. Items (a), (b), (c) are blocking. (d) required before any Mode B use of the card as rubric. (e) recommended.

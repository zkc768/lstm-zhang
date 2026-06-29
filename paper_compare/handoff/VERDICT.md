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

---

# Round 2 (MVP v2 review)

**Inputs:** revised `DESIGN_TO_REVIEW.md` + `CONSTRAINT_CARD.md` only. No repo files read. No files modified except this one.

**Bottom line:** **CLEAN PASS as an MVP — with 2 small Mode-B-verifiability additions and 1 scope clarification the user should consciously accept.** All five round-1 required changes are adopted correctly; the unsound half (active removal/repositioning) is removed, not patched, which is the right call. What remains is sound by construction because it deletes nothing. This is a real improvement, not a reframing — and there are no new false-positive risks introduced.

### Q1 — Does the MVP still solve the problem?

It solves the **mechanism** (re-dilution loop) but not necessarily the **standing tone**, and the design slightly overstates by implying both are handled. Two honest gaps:

- **It's a regression-lock, not a tone-fix.** R1 blocks net-new hedges; it removes nothing. So any defensive tone left over after the WI-1/2/3 one-time edits is *frozen in*, not fixed. The design leans on "the one-time edits already reduced standing excess" — that's an assumption R5 will test, not something the MVP acts on. If standing excess remains, only escalation (removal under R3/R4) touches it. **This is a fine staged approach, but the user should accept consciously: this round prevents the paper from getting worse; it does not, by itself, make a still-defensive paper read with a thesis.**
- **Within-zone pooling is uncapped.** R1 exempts §9 and the abstract closing block. The loop can re-concentrate self-negations *inside* those zones without violating R1 — so the abstract close / §9 could still grow apologetic. R5 should *count* it (see below), but nothing prevents it.

Verdict: adequate for the stated mechanism; does not claim to fix standing tone, and shouldn't be read as doing so.

### Q2 — R1 dual failure mode: is log + count + batch-review sufficient?

**Sufficient as a no-silent-loss floor; not sufficient as a correctness guarantee on its own.** Nothing is dropped without a trace (good). But the safeguard's *integrity* rests on the Executor's batch review — the same actor whose generic agents the system distrusts — with no independent check unless the Judge can see the suppressed items. The "explicit allowed path" the design asks about **already exists**: R1 blocks *generic mid-pass* additions, but the Executor adding a genuinely-needed bound *deliberately, with ledger context* is not a mid-pass generic add — so a new-claim-needs-new-bound case has a legitimate route. What's missing is not a path but **Judge-side verifiability** → see Q3.

### Q3 — Signal sufficiency: count/summary vs full text?

**Count/summary alone is insufficient.** It lets the Judge see *volume* ("the loop tried to re-dilute N times") but not *correctness* of any specific suppressed item — and a load-bearing bound that got logged-and-forgotten is exactly the highest-honesty-risk failure. **Required (small):** keep count/summary by default, but surface the **full suppressed text into `handoff/`** whenever (a) the count exceeds a small threshold, or (b) any summary line touches a ledger dimension (n=2 / scope / out-of-sample / domain separation / macro-F1≠economic-value). Conditional escalation keeps the channel thin in the common case while letting the Judge actually audit when it matters. Without this, the Judge signs off blind on the one channel most able to erode honesty.

### Q4 — Abstract carve-out: does it prevent the round-1 center-of-gravity shift?

It closes the **specific** round-1 failure (confident opening + bound deferred to the closing block) — co-location kills deferral. It does **not** fully close impression-strengthening within budget, because position ≠ emphasis:
- Co-location is *local* (same/adjacent sentence); it doesn't govern the *global* ordering of confident vs bounded material across the abstract.
- A bound can be co-located but grammatically demoted (parenthetical / subordinate clause), satisfying the letter while the impression strengthens.

This residual is a **Mode-B human-read judgment** ("does the abstract read stronger than the evidence?"), which the design already correctly assigns to the Judge + Codex. So: **carve-out is adequate for what a positional rule *can* do**; the residual is consciously punted to Mode B, which is acceptable. Not blocking.

### Q5 — Dormant guards (R3/R4): clearer, or confusing?

**Keep them.** The don't-rely-on-memory principle is the whole philosophy here: specifying the removal guards *now*, while removal is out of scope, means they can't be "forgotten" when removal is eventually escalated. The card already fences them as `(guard; dormant…)`, and the operative essence of R3 (default-KEEP for unregistered) is correctly live in inject-block line #4 even while full R3/R4 sleep. Minor confusion risk is outweighed by the benefit. Endorse keeping; just keep the active-this-round set (R1/R2/R5 + default-keep stance) crisp, which it currently is.

### Q6 — What a cold reader would still flag

- **The MVP contains no mechanism that detects the original failure** (defensive tone) — it fully delegates that quality judgment to Mode-B Judge + Codex. Honest, but it means the MVP is plumbing (prevent regression + measure), not a quality bar. (Mirror of Q1.)
- **"Abstract opens on the protocol/diagnostic contribution"** is itself a rhetorical choice: for a paper with weak empirical numbers, a skeptical reviewer could read "leads on protocol, defers the weak result" as burying the lede. This is the mirror of Q4 and lives in Mode-B judgment, not in the rule.
- **R5 must count hedges *inside* the two exempt zones**, per scope including §9 + abstract-closing, or within-zone pooling (Q1) is invisible. (The card says "per scope" + "total" — make explicit that the zones are included.)

### Round-2 required changes

1. **(Q3) Conditional full-text escalation** of R1-suppressed items into `handoff/` (threshold OR ledger-dimension touch), not pure count. *Blocking for Mode-B verifiability.*
2. **(Q1/Q6) R5 counts within the two exempt zones too**, explicitly. *Small; do before relying on R5 to declare "fixed."*

### Round-2 disposition

**Clean pass on the design as an MVP**, conditional on the two small additions above. The round-1 unsoundness is correctly removed (not papered over); independence pollution is fixed (card neutral; rationale in a Mode-A-only file removed before Mode B); the dual failure mode was surfaced honestly and is adequately safeguarded once Q3's escalation is added. **Scope note for the user:** this MVP is a *regression-lock + measurement layer*, not a tone fix — accept it as that. Promotion into governance is reasonable after change #1.

---

# Mode B — baseline (cold-read of REVIEW_THIS.pdf, 8pp)

**Inputs:** `REVIEW_THIS.pdf` + `WHAT_CHANGED.md` (baseline, no card-driven pass yet) + `CONSTRAINT_CARD.md` (MVP v2 rubric). Read only handoff/. No repo files. No files modified except this one. Method: fanned out 5 read-only problem-type subagents (positional / over-hedging / AI-smell / logic+numeric / red-line+citation) over a shared cold-reading pack; findings adjudicated below (a subagent over-call is corrected in §A).

**Bottom line (committal):** The paper is **honest, internally consistent, and red-line-clean** — the WI-1..7 revision did its job on the spine. But the **original disease is still clearly present**, in two distinct forms:
- **(B) Cross-section repetition:** the same load-bearing caveat restated 3–5× across sections (e.g. "no architecture claim / no final model" ~4–6×; §9 piles 7 bounds after one positive sentence).
- **(F) Within-unit negative framing / no sustained positive voice:** the paper's *default sentence shape is positive-clause-then-immediate-undercut*, and several units **end on the negation** (the abstract's last word is "untested"; §6's result paragraph ends "above a near-even floor"; §1 opens on "can survive … or … an artifact"). Even where the work earns a clean positive ("The three predeclared conditions are met"), the very next clause leashes it ("That is a fact about a fixed bar, not a demonstration of effectiveness"). The reader's last impression of most units is deflation. This is the "I did this, but it might be nothing" tone, stated plainly.

So the paper is contribution-first **positionally** (the abstract/intro lead on the protocol — §A confirms it) but **tonally over-conservative**: the confident voice is never allowed to stand for even one full sentence. **Honesty is fine; the problem is that an honest, sound result is written as if it were an apology.**

**Scope reality (state it straight):** the fix for both B and F is *consolidating / reordering / re-voicing existing hedges* — which is exactly **repositioning, ruled OUT of scope this round by MVP v2** (R3/R4 dormant; R1 only blocks net-new). So under the current rules these are **flagged + R5-measured now, fixed later** when removal/repositioning is enabled. I am not soft-pedaling the severity — B and F are the core remaining defect; the constraint is purely that this round's rules don't let anyone act on them yet. Only three things are actionable now without touching a hedge: one numeric typo (§D), the abstract's stray mechanics token + word-budget (§A), and optionally the §1 opener (§A).

## A. R2 positional — SUBSTANTIALLY PASS (subagent over-called "FAIL"; corrected)

I cross-read the actual text and **overrule the positional subagent's MAJOR "FAIL" calls.** The abstract **does** open on the contribution in active voice ("We contribute a pre-registered evaluation protocol…"), the empirical margin is **not** the opening clause, and its scope bound **is** co-located ("On the frozen validation split … 1.69 pp … two-seed mean, 1.63 pp worse seed … 2 seeds cannot quantify variance"). The carve-out the round-1/round-2 design worried about is **satisfied.** The subagent conflated the §1 opener with the abstract opener. Residual R2 items are all **MINOR**:

- `[MINOR] FIX-OK` Abstract carries a §3/diagnostic token — "descriptive CSCV/PBO of 0.514" (Abstract, p1). Card R2 item 3 says no PBO/bootstrap mechanics in the abstract. Positional, not a hedge — Executor may relocate/rename. DISPOSITION: fixable now.
- `[MINOR] FIX-OK` Abstract length appears to exceed the 200–220w budget (est. ~245–260w). Positional. DISPOSITION: trim toward budget — but note trimming = removal-adjacent; keep to non-floored connective tissue, not caveats.
- `[MINOR]` §1 opens on an ambivalence ("A small directional signal … can survive careful scrutiny, or it can be an artifact …") rather than naming the protocol first. The card mandates the *abstract* opener, not the *intro* opener, so this is a soft positional observation, not a card violation. DISPOSITION: optional restructure; not blocking.
- `[MINOR]` §1 names protocol components (validation-look budget, day-block splits, dummy floor). Borderline vs "no §3 mechanics in Intro" — it's high-level naming, no PBO/bootstrap detail. DISPOSITION: acceptable; tighten only if convenient.

## B. Over-hedging — the real gap, but it's REPETITION not unwarranted negation

Decisive finding: **no caveat is discretionary in isolation** — each maps to a floored/data-required dimension (n=2, non-independent WF, PBO≈coin-flip, bid-ask-bounce, macro-F1≠value, survivorship, no positive control). The surplus is **density + restatement**. All items below are `candidate-discretionary (pending Executor floor-check)` — I do NOT assert removable; `¬floored ⇒ default-KEEP`.

**Quantified repetition inventory (hard counts from a full-text pass — corrects an earlier under-count of "~4×"):**

| Repeated idea | Approx. count | Locations |
|---|---|---|
| "no architecture claim / no final model / ranks nothing / not model-selection" | **≈12+** | §1, §2(×2), §3.5, §4(×3), §5(×2), §6(×2), §7(×3), §9(×2) |
| "non-independent / not a clean test / not future-blind / not OOS-proof" | **≈7–8** | Abstract, §3.3, Fig1 cap, §7(×2), Fig2 cap, §9, Fig4 cap |
| "2 seeds too few to quantify variance" | **≈7** | Abstract, §1, §5, §6, §7, §8, §9 |
| "descriptive, not a significance test / not CIs" | **≈5–6** | §6, §7(×3), §8, figure captions |
| "roster exists only to drive/exercise the protocol" | **≈5** | §1, §2(×2), §4(×2) |
| "thin / small / weak / near-even floor / near-null" register | pervasive (10+) | throughout |

**Filler / restatement (information ≈0, restates the adjacent sentence):**
- §6: *"That is a fact about a fixed bar, not a demonstration of effectiveness"* — the same sentence already says "thin edge above a near-even floor."
- §4: *"it cannot prove that a surviving edge is not manufactured by an uncontrolled confound, nor that the protocol would catch a real signal"* — restates "no positive control."
- §3: *"Its power to separate signal from noise rests on construction here, not on a demonstration"* — restates "no positive control" again.
- §8 opener: *"A stable but small pattern could be spurious."* — pure throat-clearing.

**Magnitude estimate:** roughly **10–15% of the prose is restatement** of points already made — high for a tight 8-page conference paper. Concentrated entirely in the caveat machinery, not the technical exposition.

Also: `[MAJOR/density]` §9 opening positive sentence is followed by ~7 restated bounds in one paragraph (inside the §9 zone, so no R1 violation); `[MINOR/density]` §8 bid-ask-bounce caveat elaborated over ~26 lines.

**Root cause:** one honest caveat gets re-stated across body + figure captions + abstract + conclusion; summed, it bloats. The fix is consolidate-say-once — which is repositioning, **out of scope this round** → logged + handed to R5, not cut now.

DISPOSITION for all of B: **this round, measure don't cut.** Feed counts into R5 (per-scope hedge count incl. §9 + abstract-closing per the round-2 required change), and let the Executor decide per item against the manifest. Removal stays out of scope until R5 shows standing excess and R3/R4 guards are active. This is exactly the "regression-lock, not tone-fix" boundary in the round-2 disposition.

## C. Tone / AI-smell — moderately AI-touched, technically clean (flag-only)

Decisive: the draft is **not AI-written, it is AI-revised, and it shows**, but substance is precise and connective-hedge density is low. Top 3 residual tells (FLAG-only, no rewrite): (1) abstract closing caveat stack reads mechanically sequenced; (2) §6 Results subsections all follow an identical *claim→metric→caveat→reframe* rhythm with italic topic-sentence labels — uniform enough to look templated; (3) "What survives strict evaluation here…" / "A stable but small pattern could be spurious" — mild self-explaining/anthropomorphic phrasing. DISPOSITION: diagnostic for the Executor; not card items.

## D. Logic + numeric consistency — PASS, one typo

Claims are evidence-bounded; "survives/confirms/holds" are used cautiously (sign-level, not signal-real); PBO≈0.514 is correctly treated as descriptive and *not* as evidence overfitting is absent; the three evidence domains are kept separate with no number crossing. One real fixable defect:

- `[MINOR] FIX-needed` Selective-classification AURC printed as "about 0.470" in §8 text vs "AURC = 0.471" in the Figure 3 caption. Unify. This is the one clean, non-hedge, fix-now item.

## E. Red lines + citations + AI statement — PASS

No banned token (best/outperforms/profitable/significant/well-calibrated/clean-test/final-model) used affirmatively — every occurrence DENIES a claim. Domain separation explicit and held. Intervals consistently labeled descriptive, never inferential. Reference apparatus internally consistent ([1]–[40] map; no garbled entries). The 2026 cites [24],[38] are contemporaneous with the 2026 submission (VERIFY-externally only — I can't check external truth). Generative-AI statement is honest and appropriately bounded.

## F. Tone — over-conservative framing / no sustained positive voice (called out on its own, by facts)

This is a **distinct** finding from §B. §B is *cross-section redundancy* (the same caveat appearing in 4 sections). §F is the *within-unit rhythm*: a positive clause is voiced and then immediately undercut in the same or next sentence, and units tend to **close on the negative**, so the affirmative voice never carries. Both push the same direction (apologetic tone), but they have different fixes, so they are logged separately. Decisive call: this is a **real, MAJOR tone defect** — not a nitpick. Concrete spots (quoted, by location):

- `[MAJOR/tone]` **Abstract ends on a negation.** Final sentence: *"We measure macro-F1, not economic value, on five large-cap US survivors with no known-signal positive control, so the protocol's sensitivity to a genuine signal is untested."* The reader's last impression of the abstract is the word "untested." (Abstract, p1)
- `[MAJOR/tone]` **§1 opens on ambivalence, not contribution.** *"A small directional signal … can survive careful scrutiny, or it can be an artifact of how the evaluation was run."* The first thing the reader meets is the doubt. (§1, p1)
- `[MAJOR/tone]` **Earned positive immediately leashed.** *"The three predeclared conditions are met. That is a fact about a fixed bar, not a demonstration of effectiveness …"* — the paper met its own pre-registered bar (a legitimate clean positive) and undercuts it in the next clause. (§6, p4)
- `[MAJOR/tone]` **§9 contribution recap: one positive, then a cascade.** *"… holds a small validation margin … positive in all five tickers. The margin is uneven … an evaluation finding, not an architecture claim … We name the magnitudes to be scrutinized rather than sold. The 1.69 pp validation margin is a thin edge above a near-even floor …"* One affirmative sentence, then a paragraph of "thin / slim / near-coin / flips sign." (§9, p7)
- `[MINOR/tone]` **§6/§7 result paragraphs close on deflation** ("a thin validation-domain edge above a near-even floor"; "a predeclared sign, not a strong number"). The section's takeaway lands on the negative each time.

Pattern, stated plainly: the **default sentence shape is `positive → but`**, and the **default unit-ending is the caveat, not the claim.** The work is sound and the result, while weak, is real and bounded — but the writing voices it as something to apologize for. A confident-but-bounded register ("here is the result; here, in one place, are its limits") would carry the same facts without the apology.

**DISPOSITION:** `FLAG + R5-measure; fix deferred.` The remedy is re-voicing/re-ordering existing hedges (e.g. don't end the abstract on "untested"; let an earned positive stand one full sentence before bounding it) — that is **repositioning, out of scope this round** under MVP v2. Suggested R5 metric to add: count "units (abstract / each results section / conclusion) that END on a negation" — a cheap, objective proxy for this tone defect, trackable across passes. Not actioned now; not minimized either.

## Baseline gap-list → worklist for the first card-driven pass

**Actionable now (no hedge touched, removal not required):**
1. Fix AURC 0.470↔0.471 (D).
2. Move/rename the "CSCV/PBO 0.514" mechanics token out of the abstract; trim abstract toward ≤220w using non-caveat words only (A).
3. Optional: restructure the §1 opener to name the protocol before the ambivalence (A).

**Measure-don't-cut this round (R5 + Executor floor-check; removal/repositioning out of scope):**
4. **(B, repetition)** R5 hedge-count per scope incl. §9 + abstract-closing; log the repetition surplus (the ~4–6× "no architecture claim", the §9 7-bound pile, the §7 triple, the §8 26-line elaboration). None removed until R5 justifies and R3/R4 are live.
5. **(F, tone)** Add an R5 counter for "units that END on a negation" (abstract / each results section / conclusion); log the four MAJOR tone spots. Re-voicing is repositioning → deferred to the removal-enabled phase. This is core, not cosmetic — it is just blocked by this round's scope, not by its importance.

**Diagnostic only (no card action):** the AI-smell rhythm items in C.

## Mode B baseline disposition

**Spine: PASS. Presentation: MAJOR defect remaining (deferred by scope, not by severity).** Honesty, red lines, domain separation, numeric integrity, and the positional contribution-first carve-out all hold — no honesty or consistency violation. But the original disease is still clearly present in two MAJOR forms — **§B cross-section repetition and §F over-conservative within-unit framing** — and the paper still reads as an apology for a sound result. I am not grading that as "minor": it is the central remaining defect. The only reason it is not an action item this round is that its fix (consolidate / re-voice / re-order existing hedges) is **repositioning, which MVP v2 puts out of scope** — so B and F are logged and handed to R5 now, and fixed in the removal-enabled phase. Actionable immediately without touching a hedge: §D typo, §A abstract token + word-budget, optional §A §1 opener. Everything in B and F is for the R5 counter + the Executor's manifest call — not for me, and not for deletion this round.

---

# Mode B — batch 1 (abstract + §1)

**Input:** refreshed `REVIEW_THIS.pdf` (recompiled 2026-06-29) + updated `WHAT_CHANGED.md` (run #1, §F tone pass, abstract + §1; §7/§9 not touched). Verified the changes by reading the actual text (not file size — confirmed the two new endings WHAT_CHANGED specified). Read only handoff/. Only this file modified.

**Bottom line (committal):** The two tone edits **landed and are sound on all three verification asks.** Abstract and §1 now close on a contribution, no floored caveat was dropped or softened, and there is no claim-upgrade. **One process flag:** this batch was billed as "reorder," but it also performed a *fold* (repositioning) and a *D24 2→1 dedup* (a floor-reducing removal) — both are operations the card's MVP v2 declares **out of scope this round.** Substantively harmless and even desirable; procedurally it crosses the round's own scope line. Call that out, don't bury it.

### Check 1 — do abstract and §1 now close on contribution, not a caveat? **PASS (both).**
- Abstract now ends: *"This is a worked case for the protocol, not yet a test on a signal known to be real. **The transferable contribution is the protocol and its diagnostics.**"* The old terminal word "untested" is gone; the close is a contribution clause. ✓
- §1 contributions ¶ now ends: *"**The diagnostics map where this edge persists and where it reverses.**"* (the "…positive-control next step" sentence was moved earlier, not deleted). ✓
- Target metric "units closing on negation 5→3": I confirm **2 units flipped** (abstract, §1). Consistent with 5→3 given §7 (still closes on "flips") and §9 unchanged.
- **Conceding my earlier §F call:** keeping the §1 opener ("…can survive scrutiny, or it can be an artifact") is **defensible** — for a paper whose thesis *is* "real edge vs evaluation artifact," that dichotomy is the framing question, not throat-clearing. My baseline flagged it MAJOR; I downgrade that. The load-bearing §F issue was *end-on-negation*, and that is now fixed.

### Check 2 — did the reorder/reword drop or soften any floored caveat? **PASS — all retained, meaning intact.**
Read directly in the new abstract: n=2 ("though 2 seeds cannot quantify variance") ✓; not-a-clean-test ("non-independent walk-forward … not a clean test") ✓; not-economic-value ("We measure macro-F1, not economic value") ✓; no-positive-control ("with no known-signal positive control") ✓; plus PBO 0.514, bid-ask-bounce, survivorship all present. §1: 2-seeds / macro-F1-only / no-positive-control / five-survivors all present (pure reorder). The old "…sensitivity to a genuine signal is **untested**" was not deleted but **reframed** to "not yet a test on a signal known to be real" — same honesty content, different last word. No softening of substance. ✓

### Check 3 — implicit claim-upgrade from ending on "the contribution is the protocol + diagnostics"? **PASS — no upgrade; if anything, de-escalation.**
The new closing sentence redirects the takeaway to the *method*, explicitly **not** the empirical edge ("the transferable contribution is the protocol and its diagnostics"). It does not strengthen the 1.69 pp result — that claim keeps its bound co-located earlier ("…1.69 pp … two-seed mean, 1.63 pp worse seed. The margin is positive in all five tickers, though 2 seeds cannot quantify variance"). The bound that *moved* ("untested"/"worked case") was a global statement about protocol sensitivity, not a leash on the 1.69 pp number, so moving it can't upgrade that number. §1 ending "where this edge persists and where it reverses" keeps the negative half ("reverses"). Round-1 Q2 failure path does **not** trigger here. ✓

### Process flag (decisive, proportionate)
WHAT_CHANGED's own gate notes: "Only floor touch = **D24·anti_leak 2→1** (dedup_ok, floor=1 met)" and "the standalone 'We cannot yet separate…' was **folded** into the conditional sentence." Both are *removal/repositioning of existing hedges* — which `CONSTRAINT_CARD` MVP v2 states verbatim is **OUT OF SCOPE this round** ("Active removal/repositioning of EXISTING hedges is OUT OF SCOPE this round"). So a batch described as a reorder actually crossed into the removal lane, and a **floor reduction (2→1) is exactly the operation R3/R4 were written to guard.** I verified the surviving instance retains the caveat and the gate reports floor=1 still met — so the *risk* is low and the *result* is good (it trims the kind of duplicate §B flagged). But I take the gate's floor accounting **as reported**; I cannot independently audit the manifest. Recommendation: don't let scope drift silently — either (a) formally bring removal in-scope now and log this D24 2→1 + the fold under R3/R4 with justification, or (b) treat them as a sanctioned, recorded exception. Pick one explicitly.

### Batch-1 disposition
**PASS — accept the abstract + §1 tone edits.** All three verification asks clear; the end-on-negation defect is fixed for these two units with caveats intact and no claim-upgrade. The only open item is the scope/process flag above (a floor-touch + a fold done inside a round that declared removal out of scope) — low-risk, but log it under R3/R4 or record it as an exception rather than leaving scope ambiguous. §7 and §9 (the "flips" close and the "breaks" last-word) remain for the next batch.


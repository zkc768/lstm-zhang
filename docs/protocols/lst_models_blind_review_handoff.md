# lst_models Blind-Review Handoff (cross-window Codex-Reviser / Claude-Reviewer harness)

Status: long-term protocol. Reusable fill-in-the-blank harness for running the
paper revision loop across two windows: an external **Codex Reviser** drafts a
candidate, the **orchestrator (you)** runs the deterministic gate and assembles a
rationale-stripped packet, and a fresh **Claude blind reviewer** in a new window
adjudicates the diff. This doc extends and never overrides `AGENTS.md`,
`docs/protocols/lst_models_paper_revision_workflow.md` (§6 roles, §8 adversarial
review, §8.1 three-pass Final-QC), and
`docs/protocols/lst_models_external_codex_reviser_adapter.md`.

## 0. Prime Rule (read first)

This file is a **process skeleton only**. It MUST NOT contain any round-specific
candidate text, reviser rationale, or reviewer finding. All such per-round content
lives in `paper/length_loop/runs/<round_id>/`. Pasting a real round's rationale or
findings into this doc would prime future blind reviewers and is forbidden. Keep
every skeleton template generic.

Exception: ONE clearly-marked **worked-instance appendix** (§9) may carry the
operational W2/W3/W2' prompts and the objective red-line contract (D-locks /
F-terms / numbers / allowlist) for the most recent round, kept so the next round
can be cloned by changing the id and contract. That contract is reviewer-visible
by design — it is exactly what Template B already shows W3 — so it does not leak
rationale. The appendix still carries no candidate prose, no findings, and **no apply /
disposition logic** — the synthesizer's "no P0 -> apply" logic and the round's
purpose live in `paper/length_loop/runs/<round_id>/PROMPTS.md`, never here, so a
stray read cannot prime a verdict. A **W3 blind reviewer reads only §2, §5, and §6
and never the §9 appendix;** even on a stray read, §9 reveals only the contract W3
already holds in Template B.

## 1. Roles And The Boundary That Protects Blindness

```
Codex (Reviser)  ──candidate + ITS rationale/evidence table──▶  You (Orchestrator/Synthesizer)
                                                                     │  run round_diff.py:
                                                                     │   ① authoritative diff (baseline→candidate)
                                                                     │   ② L1–L5 verdict (PERMIT_REVIEW?)
                                                                     ▼
                                       assemble BLIND PACKET = diff + red-line contract + allowlist
                                       ★ strip Codex PLAN.md / evidence table / rationale ★
                                                                     │
                                                                     ▼
                                       New-window Claude (third-party BLIND reviewer)
                                                                     │  findings only: P0/P1/P2 + line evidence + scope-drift
                                                                     ▼
                                       You (Synthesizer) → ACCEPT / REPAIR / ROLLBACK / STOP
                                       ├─ ACCEPT → you apply to paper/sections/* (or main.tex) → pdflatex ×2
                                       └─ REPAIR → relay ONLY objective finding+line+manifest-id back to Codex
```

- The Reviser writes ONLY `runs/<round_id>/candidate_<section>.tex` + `PLAN.md`;
  it never edits live files and never decides ACCEPT/REPAIR/ROLLBACK
  (adapter Scope + Hard Contract).
- The Gatekeeper is not an agent: it is the orchestrator running `round_diff.py`
  (L1–L5 + allowlist + hashes). A deterministic PASS only PERMITS review.
- The blind reviewer adjudicates the **diff**, not the finished candidate, and
  never sees reviser rationale (workflow §8).

## 2. Blindness Contract (what the reviewer MAY and MUST NOT read)

Blindness here means: the reviewer is blind to the **reviser's reasoning**, so it
re-derives soundness independently. It is NOT blind to manuscript truth.

MAY read (authority — strengthens the review):
- `docs/protocols/lst_models_paper_revision_workflow.md` §8 / §8.1 / §8.3.
- `paper/length_loop/protection_manifest.json` (D-locks, F-terms, never_delete,
  caption_locks).
- `paper/outline_and_claims.md` (canonical numbers / claim_ids / evidence domains).
- the frozen baseline of the target section (what the diff is computed against).
- the blind packet itself (diff + contract + allowlist + the PERMIT_REVIEW line).

MUST NOT read (reviser rationale — reading any of these breaks blindness):
- `runs/<round_id>/PLAN.md` (the reviser's intent and self-check).
- `runs/<round_id>/ai_use_log.json`, `similarity_triage_report.md`.
- the candidate's declared metadata / nonexpert evidence table.
- `state.json` "notes" fields that paraphrase a reviser's intent.
- anything from the Codex window, or from the chat where the packet was built.

Repo-aware vs packet-only:
- **Mode 1 (default, repo-aware + fenced):** the new window runs in the
  `lst_models` repo so the reviewer can verify a claimed D-lock against the
  manifest and a number against the ledger — but it obeys the MUST-NOT list
  above. Stronger review; requires the fence.
- **Mode 2 (fallback, packet-only):** the new window has no repo access and
  judges only the pasted packet. Inherently blind; weaker, because it cannot
  re-verify numbers against the ledger. Use when the fence cannot be trusted.

## 3. Template A — Codex Reviser Instruction (send to Codex; fill the `<...>`)

Send as ONE message; have Codex execute in two gated steps (confirm, then write).

```text
You are acting ONLY as External Reviser for the lst_models paper (per
docs/protocols/lst_models_external_codex_reviser_adapter.md). You do NOT decide
ACCEPT/REPAIR/ROLLBACK and you do NOT touch live manuscript files.

ROUND: <round_id, next free rNNN>
TARGET: <one section file, e.g. sections/0X_*.tex — or the abstract block in main.tex ONLY>

READ FIRST (read, do not edit):
 1. AGENTS.md
 2. docs/protocols/lst_models_paper_revision_workflow.md (§8 deletion-first; L5 hedge-monotonicity)
 3. docs/protocols/lst_models_external_codex_reviser_adapter.md
 4. paper/outline_and_claims.md
 5. paper/length_loop/protection_manifest.json
 6. paper/length_loop/state.json
 7. <the target file>

WHY THIS ROUND (presentation only; no new experiments; no number changes):
 <the advisor-feedback intent for this section, in 1–3 lines>

ALLOWLIST (only these regions may change):
 <list the exact sentences/paragraphs/caption the round may touch>

HARD BUDGET: <word/length budget>; the build is at the 8-page limit with zero
headroom — do NOT grow it. If the goal cannot be met without touching a locked
item, STOP and say so.

MUST-PRESERVE HEDGES (manifest D-ids, keep verbatim meaning):
 <Dxx — plain meaning> ...   (pull the exact set whose `currently_in` includes this target)

NECESSARY NUMBERS — do not change/drop/add: <exact tokens from the manifest claims for this section>

FORBIDDEN unless already negated (the rewrite must not introduce any affirmatively):
 clean test, out-of-sample, final model, best, outperforms, superior, SOTA,
 statistically significant, profitable, tradable, (trading) alpha.   (+ any section-specific F-ids)

MODEL-STORY RULE (if relevant): TCN is the single predeclared/frozen primary;
LightGBM is the mechanical fallback that never fires; MS-DLinear+TCN is an
alternative-architecture roster member, never co-primary or "best".

OUTPUT — two SEPARATE files under paper/length_loop/runs/<round_id>/ :
 • candidate_<section>.tex — ONLY the revised region. Clean LaTeX. NO rationale inside it.
 • PLAN.md — allowlist self-check, word count before/after, metadata block
   (declared_parent_sha256, manifest_sha256, touched_claim_ids, evidence domains,
   D-locks preserved, F-terms avoided), and the nonexpert evidence table
   (claim_id / evidence_domain / can_prove / cannot_prove[F-id] / required_hedges[D-id]).
   ALL rationale goes here, NEVER in the .tex.

EXECUTE IN TWO STEPS, PAUSE BETWEEN:
 STEP 1 (confirm, before writing): print declared_parent_sha256 of the target,
   the D-lock list you will preserve, the F-terms you keep negated/absent, the
   numbers you will not touch, and your read of the allowlist + budget. Then STOP.
 STEP 2 (after I say go): write the two files.

STOP and return if: any required hedge would weaken/disappear; any forbidden term
would appear affirmative; any number/citation/label/caption would change; the
live target you read does not match what I authorized; or the goal needs exceeding
the budget / 8 pages.
```

## 4. Template B — Blind Packet (you assemble after the gate; rationale stripped)

Paste this into the new window. It is self-contained. Codex's PLAN/evidence/
rationale are NOT in it.

```text
[BASELINE — frozen <target>]   <round_diff '-' side, or the frozen region>
[CANDIDATE — <target>]         <round_diff '+' side>     ← or paste the unified diff directly
[ALLOWED SCOPE this round]     <the allowlist: which sentences/caption/region were permitted to change>
[RED-LINE CONTRACT]
  • three evidence domains, never mixed in EVIDENCE STRENGTH: frozen validation (n=2) /
    train-inner control / guarded non-independent walk-forward
  • PERMITTED (do NOT flag as domain-mix; ledger-sanctioned — omitting this wastes review rounds,
    empirically 4 false-positives in one full review): the C2.3 canonical control-vs-validation
    CONTRAST when it carries the not-full-family / not-apples-to-apples disclaimer; the C4.5
    cross-window recurrence of the CONDITIONAL pattern when per-domain numbers stay in separate
    sentences
  • required hedges (manifest D-ids) that must survive: <list with plain meaning>
  • forbidden F-terms (affirmative form not allowed): clean test, out-of-sample, final model,
    best, outperforms, superior, SOTA, statistically significant, profitable, tradable, alpha
  • necessary numbers (must be unchanged): <list>
  • never_delete touched? \Description / GenAI statement / dummy rows / macros / \label-\ref / CCS
  • 8-page ACM sigconf hard limit; current pages = <N>
[PRECONDITION] round_diff.py L1–L5 = PERMIT_REVIEW  (permits review only; NOT acceptance)
[STRIPPED] Codex PLAN / rationale / evidence-table are intentionally absent — judge independently.
```

## 5. Template C — Reviewer Kickoff (the new-window opening line; answers "how do I tell it")

With this doc persisted, the kickoff is a short pointer + fence + packet:

```text
Act as the third-party adversarial BLIND REVIEWER defined in
docs/protocols/lst_models_blind_review_handoff.md (§5 + §6). Repo cwd = lst_models.

You MAY read authority only: revision workflow §8/§8.1, protection_manifest.json,
outline_and_claims.md, and the frozen baseline of the target section.
You MUST NOT open the reviser's per-round artifacts under
paper/length_loop/runs/<round_id>/ (PLAN.md, ai_use_log.json, candidate metadata)
or any reviser rationale. Review the DIFF in the packet below ONLY.

Emit FINDINGS ONLY. Do NOT decide submission readiness. A deterministic gate PASS
is a precondition, not acceptance. Silence on a deletion is itself a MAJOR.

[PASTE TEMPLATE B HERE]
```

Open the new window as a fresh session (not /clear of this one), in the repo for
Mode 1. Paste nothing from the Codex window or this chat except Template B.

## 6. What Makes A QUALIFIED Blind Review (the bar the reviewer must meet)

The reviewer adjudicates the diff across three lenses (workflow §8):
1. **claims / evidence-domain / hedge / caption integrity**
2. **stats / estimand / reproducibility-leakage**
3. **ACM layout / `\Description` / figure / 8-page**

Deletion-first checklist — auto-escalate to **≥MAJOR** unless the reviewer
actively justifies safety: any removed caption or `\Description` token; any
removed hedge (to the extent / would / may / if / appears / suggests); any removed
evidence-domain label; any removed number; any removed limitation/caveat.
**Silence on a deletion = MAJOR.** Hedge monotonicity: a conditional→assertive
rewrite is **≥MAJOR** (L5 also blocks weakening a pinned hedge).

Every finding must carry:
```text
section_anchor: <file:line or label>
claim_id: <C*, if applicable>
evidence_domain: validation | train-inner | guarded | protocol | mixed/unclear
manifest_ids: <D* hedges and/or F* terms touched>
severity: P0 | P1 | P2 | experiment_required
line_evidence: <the exact changed text>
recommended_route: ACCEPT | REPAIR | ROLLBACK | STOP
```

Severity vocabulary: **P0** = factual error / evidence-tier drift / missing
mandatory ACM item / misleading-as-submitted; **P1** = likely reviewer-rejection
risk, text-repairable; **P2** = clarity/citation/style; **experiment_required** =
needs new analysis (out of paper-edit scope until the user authorizes it).

A review is **QUALIFIED** only if it:
- ran the deletion-first checklist explicitly (not "looks fine");
- gave every finding line evidence + manifest id + severity + route;
- defaulted skeptical on every deletion / hedge change;
- checked the three evidence domains are not mixed and scope-drift vs the allowlist;
- re-derived against the manifest/ledger instead of trusting the candidate's framing;
- stayed in its lane: emitted findings, did NOT declare the paper submission-ready,
  did NOT read reviser rationale, did NOT invent requirements absent from the contract.

A review is **UNQUALIFIED** (re-run it) if it: rubber-stamps; cites no line
numbers; accepts the candidate's self-justification; tries to decide ACCEPT or
submission-readiness; or opened `runs/<round_id>/` reviser artifacts.

A reviewer-judgment finding can never be promoted to artifact-backed evidence.
Acceptance requires zero unresolved P0 and zero text-fixable P1 AFTER the
deterministic PERMIT_REVIEW — but the **Synthesizer (you)** makes that call, not
the reviewer.

### 6.1 venue-reviewer — acceptance-value lens (full-draft rounds)

The personas above audit COMPLIANCE: hedges, evidence domains, numbers, deletions,
allowlist drift. None of them asks whether the paper is worth accepting. The
**venue-reviewer** owns that question: it reads the FULL current draft (never a
diff — acceptance value is not visible in a diff) as an ICAIF / finance-ML
program-committee member deciding accept vs reject. Same fence as §2: it MAY read
the authority list; it MUST NOT read `runs/<round_id>/` reviser artifacts. It
judges exactly five lenses:

1. **Contribution clarity** — "why accept this?": can a busy PC member restate
   the contribution in two sentences from §1 alone?
2. **Novelty positioning** — what the paper adds beyond assembling known guards
   (pre-score freeze / same-row dummy floor / budget ledger / CSCV discount),
   and whether §1–§2 state it.
3. **Evidence sufficiency for the claims AS FRAMED** — does the evidence carry
   the paper's own scoped claims? Whether a claim overreaches its evidence is
   the other personas' job, not this persona's.
4. **Venue fit** — why this venue; what a finance-ML audience takes away.
5. **"So what for finance practice"** — what a practitioner or empirical
   researcher does differently after reading.

OUT of scope (other personas own these; venue-reviewer findings there are
duplicates, not value): red-line vocabulary compliance, number-to-ledger
binding, evidence-domain fusion checks, the deletion-first checklist.

**No-claim-inflation rule (hard; the Synthesizer enforces it):** the persona may
find the contribution under-argued; it may NOT cure that by strengthening a
claim. Any recommendation that would violate a red line — "claim significance",
"select a model", "drop the guarded / non-independent label", "sell the calm-bar
edge" — is AUTO-REJECTED at adjudication: the Synthesizer records it as rejected
(red-line conflict) and never routes it to REPAIR. Permitted cures: reframe
ledger-bound facts, reposition against literature, or file an
`experiment_required` finding (more seeds, positive control, cost model) that
waits for explicit user authorization.

Pipeline — identical to the other personas: findings only, in the §6 finding
block with the §6 severity vocabulary (P0 | P1 | P2 | experiment_required);
`claim_id` / `manifest_ids` may be `n/a`, but section_anchor + line_evidence +
severity + recommended_route stay mandatory. Findings go to the Synthesizer, who
alone decides ACCEPT / REPAIR / ROLLBACK / STOP. The Template-B (§4)
ledger-sanctioning rule applies unchanged: re-flagging the sanctioned C2.3 /
C4.5 phrasing is a false positive, not a defect. The venue-reviewer never
decides submission readiness, and a missing-evidence complaint maps to
`experiment_required`, never to a text-repair P1.

## 7. Orchestrator Cross-Checks And Loop Close

Before dispatch and before apply, run the adapter's live-state sweep
(`lst_models_external_codex_reviser_adapter.md` Enforcement):
1. `declared_parent_sha256` ≠ the orchestrator-authorized section hash → red flag,
   re-freeze before review.
2. Codex declares "no claim touched" but `round_diff` L1–L3 regresses → red flag.
3. Any live edit outside `runs/<round_id>/` → STOP / re-freeze.

On the reviewer's verdict, map to the §6/§9 synthesizer states: ACCEPT → apply
(atomic, with `tmp/` backup) → `pdflatex` ×2 → re-run `pdf_hygiene.py` →
record in `state.json`. REPAIR → relay to Codex **only** the objective finding +
line + manifest id (never the reviewer's full prose, to keep the next round
blind). ROLLBACK/STOP → record and stop.

## 8. Per-Round Checklist (instantiate the harness)

1. Pick the next free `rNNN` (scan `paper/length_loop/runs/`; do not reuse a number).
2. Fill Template A: target, allowlist, and the exact D-ids/F-ids/numbers whose
   manifest `currently_in` includes this target.
3. Run Codex Step 1 → verify sha + D-lock list → authorize Step 2.
4. Run the §7 cross-checks; run `round_diff.py` for the diff + L1–L5 verdict.
5. Assemble Template B (strip rationale); open a new window with Template C.
6. Collect findings; act as Synthesizer; apply or relay-for-repair; record.
7. Full-draft review rounds (workflow §8.1 / §8.3): also spawn the §6.1
   **venue-reviewer** (acceptance-value lens) over the compiled draft — findings
   into the same Synthesizer adjudication; red-line-violating recommendations
   are auto-rejected (no-claim-inflation rule).

## 9. Worked Instance — r033 (ORCHESTRATOR-SIDE; W3 must NOT read this)

> ⚠️ Reviewer-safe by construction: §9 carries only the **W2 gate/assemble
> contract** (identical to what Template B already shows W3) and the W3 kickoff.
> The round's **apply/disposition logic and purpose live in
> `paper/length_loop/runs/r033_abstract_contribution_framing/PROMPTS.md`, not
> here**, so a stray read cannot prime a verdict. To clone for r034, copy that
> `PROMPTS.md`, change the round id, target, allowlist, and D/F/number contract
> (pull from `protection_manifest.json` `currently_in`). A W3 reviewer still should
> not read §9; if you find yourself here, stop and rely only on your packet.

### 9.1 W2 — Gate & Assemble (window with repo + bash)

```text
You are the orchestrator-side GATEKEEPER + PACKET ASSEMBLER for ONE revision
round of the lst_models paper. Round: r033_abstract_contribution_framing.
Repo cwd = lst_models. You are NOT the reviser and NOT the reviewer. You run
deterministic gates and assemble a rationale-stripped blind-review packet. You do
NOT edit live files, do NOT apply anything, do NOT decide ACCEPT.
Authority: docs/protocols/lst_models_blind_review_handoff.md (§4, §7) +
lst_models_paper_revision_workflow.md (§8, §9) + the external-codex adapter (Enforcement).

INPUTS (in repo):
 • candidate (abstract block only): paper/length_loop/runs/r033_abstract_contribution_framing/candidate_main_abstract.tex
 • reviser sidecar: same dir / PLAN.md   <- you MAY read it for cross-checks; it MUST NOT appear in your output
 • baseline: the \begin{abstract}...\end{abstract} block in paper/main.tex

DO, IN ORDER:
1. If the candidate file is missing -> STOP and report "no candidate; run Codex Step 2 first." Do nothing else.
2. CROSS-CHECKS (adapter Enforcement), report each PASS/FLAG:
   a. sha256 of current paper/main.tex vs PLAN.md declared_parent_sha256 (flag any mismatch / re-freeze).
   b. PLAN.md touched_claim_ids: confirm they are only abstract-relevant claims (C2.1/C4.1/C4.2/C4.3 etc.); flag any it should not touch.
   c. confirm NO live edit outside runs/r033/ (git status; paper/main.tex unchanged vs its committed/frozen sha).
3. SPLICE: copy paper/main.tex, replace ONLY its abstract block with the candidate block, save as
   paper/length_loop/runs/r033_abstract_contribution_framing/candidate_main.tex (full file, only abstract changed).
4. GATE (deterministic): run
   python paper/scripts/round_diff.py --section main.tex \
     --candidate paper/length_loop/runs/r033_abstract_contribution_framing/candidate_main.tex \
     --round-id r033_abstract_contribution_framing --allowlist "#body"
   If round_diff cannot take main.tex as --section, fall back to length_gates.py + latex_inventory.py
   on the spliced file (number-conservation + L1-L5) and SAY which gate actually ran. Read the script
   headers if unsure. Report the verdict.
5. VERDICT:
   • BLOCK (gate fail / changed region outside #body / any necessary number changed) ->
     output the BLOCK reason (which gate / region / number) and STOP. Do NOT assemble the packet.
   • PERMIT_REVIEW -> go to step 6.
6. ASSEMBLE Template B and emit it (see OUTPUT). Fill from the abstract baseline + candidate, the
   contract below, and the gate result. The human-readable diff is just the abstract before/after.

CONTRACT TO EMBED IN THE PACKET (r033 abstract):
 • three evidence domains, never mixed: frozen validation (n=2) / train-inner control / guarded non-independent WF
 • required hedges that must survive (manifest D-ids):
   D1 not-a-clean-test · D2 non-independent · D3 no-final-model/"not a new model" · D6 no-trade-band ·
   D8 calm-bar/below-random-on-active in BOTH windows (a limitation) · D9 cannot-separate-from-bid-ask-bounce ·
   D10 estimand-sensitive, guarded headline row-pooled +0.636 (keep the row-pooled qualifier) ·
   D12 PBO/CSCV labeled "descriptive" · D13 PBO 0.514 two-sided "too coarse to rule overfitting in or out" ·
   D16 "deliberately weak predeclared bar" · D17 "on the frozen validation split" ·
   D18 two-seed mean / too few to quantify variance · D23 "macro-F1, not economic value" ·
   D24 one near-null case, no known-signal positive control (most consequential) · D25 five large-cap US equities
 • forbidden in affirmative form: clean test · out-of-sample · final model · best · outperforms · superior ·
   SOTA · statistically significant · profitable · tradable · (trading) alpha
 • necessary numbers (unchanged): 1.69 · 1.63 · 0.636 · 0.514 · "five" equities · post-2017 · 5-minute
 • contribution(2) wording trap: the margin is over the SAME-ROW STRATIFIED DUMMY, NOT over rival families;
   no family is best/selected (TCN primary; LightGBM fallback never fires; MS-DLinear+TCN is alt-architecture only)
 • never_delete touched? macros \macrofone \pp \numseeds; GenAI statement; CCS/title  (abstract uses \macrofone, \pp)
 • allowlist = #body (abstract block only); within it only framing/synthesis sentences may change
 • 8-page hard limit; pre-change build = 8 pages; abstract budget 200-220 words; must not grow the build

OUTPUT — your ENTIRE reply is exactly these two things, nothing else:
 (1) GATE SUMMARY: 3-6 lines (cross-checks, which gate ran, verdict, current pages, candidate word count).
 (2) one fenced text block labelled "BLIND PACKET (Template B) — paste into W3" containing:
     [BASELINE — frozen abstract] <the current abstract block>
     [CANDIDATE — abstract]       <Codex's candidate block>     (a short before/after diff is welcome)
     [ALLOWED SCOPE] #body abstract; only framing/synthesis sentences
     [RED-LINE CONTRACT] <the bullets above>
     [PRECONDITION] round_diff/L1-L5 = PERMIT_REVIEW (permits review, not acceptance)
     [STRIPPED] Codex PLAN / rationale / metadata intentionally absent.
NOTHING from PLAN.md, no rationale, no Step-1 confirmation, no metadata may appear anywhere in your reply.
```

### 9.2 W3 — Blind review (a fresh window; NOT the W2 window)

```text
Act as the third-party adversarial BLIND REVIEWER defined in
docs/protocols/lst_models_blind_review_handoff.md (§5 + §6). Repo cwd = lst_models.
You MAY read authority only: revision workflow §8/§8.1, protection_manifest.json,
outline_and_claims.md, and the frozen baseline of the abstract in main.tex.
You MUST NOT open paper/length_loop/runs/r033_abstract_contribution_framing/
(PLAN.md, candidate metadata) or any reviser rationale, and never read §9 of the
handoff doc. Review the DIFF below ONLY.
Emit FINDINGS ONLY (section_anchor · claim_id · evidence_domain · manifest_ids(D*/F*) ·
severity P0|P1|P2|experiment_required · line_evidence · route ACCEPT|REPAIR|ROLLBACK|STOP).
Run the deletion-first checklist explicitly; silence on a deletion is itself a MAJOR.
Do NOT decide submission readiness. A gate PASS is a precondition, not acceptance.

[paste the BLIND PACKET (Template B) that W2 emitted]
```

### 9.3 W2' — Synthesize & Apply (moved out of the doc)

> The filled W2' synthesizer/apply prompt — with its ACCEPT/REPAIR and
> "no P0 -> apply" disposition logic — lives in
> `paper/length_loop/runs/r033_abstract_contribution_framing/PROMPTS.md` and follows
> §7. It is kept out of §9 precisely so that disposition logic cannot prime a
> reviewer who strays here. Clone it per round into the round's own `PROMPTS.md`.

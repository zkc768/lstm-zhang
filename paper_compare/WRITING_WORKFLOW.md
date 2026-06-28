# v2 per-section writing workflow

> SUPERSEDED — the authoritative master is `paper_compare/PAPER_WORKFLOW.md`. This file is kept
> as an input (the per-section loop + humanizer scope + exemplar-distillation rationale). If this
> and PAPER_WORKFLOW.md ever disagree, PAPER_WORKFLOW.md wins.

Goal: human-reading, logically coherent, rigorous prose in the Option-2 framing, inside the
red lines. Replaces the old length_loop churn. Must CONVERGE (≤3 passes/section), not spin.

## Root problem this fixes
Grep gates catch vocabulary/structure but NOT (a) AI rhythm (uniform sentence length, template
paragraphs) or (b) weak inter-paragraph logical flow. Those are the two things that still read
"AI" and feel disjointed. This workflow adds explicit passes for both.

## Tools per job
- Draft: `ml-paper-writing` skill + Option-2 spine + claims-ledger numbers (every number bound).
- Local logic check: GitHub `逻辑检查` discipline — flag ONLY fatal logic gaps, term drift,
  unsupported claims. High tolerance, no nitpicking (prevents churn).
- De-AI / naturalness: anti-AI style guide + 8 grep gates, PLUS `humanizer` used SCOPED (below).
- Cross-context flow: `academic-writing-agents:logic-reviewer` — transitions, argument build,
  paragraph-to-paragraph coherence, tie to the paper spine.
- Consistency / numbers / red lines: `consistency-checker` + claims-ledger bind + red-line list.

## Per-section loop
Per paragraph / point:
1. Draft the point (grounded in real numbers).
2. Local logic check (LIGHT): claim supported by a real artifact value? any jump? term consistent?
   Fix fatal issues only.
3. De-AI pass: grep gates + scoped humanizer rhythm.
Repeat 1–3 until the section is drafted.

Then, on the whole section:
4. Cross-context coherence check (the key pass): does each paragraph follow from the previous?
   Is there connective tissue? Does the section build ONE argument toward its claim and connect
   to the paper's spine? Add transitions / reorder / bridge as needed.
5. Final gate: consistency-checker + every number bound to ledger/artifact + red lines hold +
   grep gates pass + humanizer meta-audit ("what still sounds AI?") → revise once.

Stop. Hard cap 3 passes. If a sentence still won't settle, FLAG it for the user — do not
re-hedge in circles (that was the old failure).

## humanizer scope (use SOME, appropriately)
USE:
- Sentence-rhythm variation (break uniform cadence; mix short and long).
- Specific-over-vague phrasing.
- The final meta-audit prompt: "what makes this obviously AI generated?" → fix remaining tells.
- Its pattern list as a detector for tells the grep gates miss.
DO NOT USE:
- Soul / opinion / first-person / feelings / "let some mess in" (breaks academic register + red lines).
- De-hyphenation of compound modifiers (data-driven, long-term) — wrong for formal prose.
- Stripping hedges the DATA requires ("descriptive", "non-independent", "near-null").
After ANY humanizer edit → re-run the red-line + grep gates (humanizer must not introduce a violation).

## Exemplar playbook (retrieval, NOT whole-paper)
Built once the exemplar search returns verified papers.
- `paper_compare/exemplars/pdfs/` — downloaded open-access (arXiv) exemplars.
- `paper_compare/exemplars/playbook/*.md` — distilled, finely-categorized PATTERNS, paraphrased
  (never copied text — plagiarism-safe), each tagged with its source exemplar:
  - `abstract_shapes.md`, `intro_moves.md`, `weak_result_framing.md`,
    `related_work_organization.md`, `transitions_and_flow.md`, `sentence_rhythm.md`,
    `limitations_craft.md`, `caption_style.md`.
- During writing: pull ONLY the 1–2 playbook files relevant to the current section (e.g., §1 →
  intro_moves + transitions_and_flow + weak_result_framing). Never load a whole paper while
  drafting — this prevents attention dilution and removes any copy risk.

## Anti-plagiarism
Exemplars inform STRUCTURE and LOGIC only. No sentence is ever copied. The playbook stores
abstracted patterns, not text. Run the project's existing similarity triage before submission.

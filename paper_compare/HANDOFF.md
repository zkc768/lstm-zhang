# HANDOFF — v2 paper (Option-2): next-phase brief

**To start in a fresh window, paste:**
> Read `paper_compare/HANDOFF.md` and continue from there. Pass A is being finished in the other
> window; your job is Pass B -> C -> citation-validator -> Codex review. Be thorough; I want
> maximum rigor and am fine with cost — do not cut corners.

---

## 0. What you're doing
The v2 paper is being rewritten into the **"Option-2 (finding-forward) but honest"** framing.
**Pass A (per-section inner loop) on §2,§3,§4,§5,§8 is running in the originating window.** Your
job is the WHOLE-PAPER phases that come after: Pass B (cross-section), Pass C (naturalness /
anti-homogenization), the citation-validator, and the Codex adversarial review. First confirm
Pass A actually finished (step 5 below); if any of §2–§5,§8 still fails the gate, finish its
Pass A before Pass B.

## 1. Read first (governance — obey in this precedence)
1. `.claude/CLAUDE.md` (auto-loaded) — paper governance; defers to `AGENTS.md`.
2. `paper_compare/PAPER_WORKFLOW.md` — master workflow; **§8 = the iteration model (Pass A/B/C +
   Codex + quality-stop + anti-homogenization)**.
3. `paper/outline_and_claims.md` — claims ledger; FINAL fact source; three evidence domains NEVER fused.
4. `docs/lst_models_paper_translation_and_anti_ai_style_guide.md` — anti-AI gates.
5. `paper_compare/exemplars/playbook/README.md` (+ files) — structure/logic moves (PARAPHRASE only).
6. `paper_compare/REFERENCE_WORKFLOWS.md` — external references + the PaperOrchestra adoptions.
7. `paper_compare/homogenization_baseline.md` — perplexity/burstiness baseline to compare against.
8. Context: `REDLINE_AUDIT.md`, `EXPERIMENT_ANALYSIS.md`, `EXEMPLAR_PAPERS.md`.

## 2. Current state
- **v1 frozen — DO NOT touch:** `paper_compare/v1_current/`, live `paper/`.
- **v2:** `paper_compare/v2_skill_draft/`. Option-2 done + gate-clean + compiles 8pp:
  **abstract (`main.tex`), §1, §7**. Also gate-passing: §6, §9. **§2,§3,§4,§5,§8: Pass A in
  progress (other window).**
- **Tools:**
  - `python paper_compare/check_integrity.py <file>` — fast gate (red-lines, "two domains",
    Tier-1 vocab, phrase blacklist, >35-word sentences; warns on em-dash, guarded phrases,
    opener chains, low sentence-length-variance burstiness).
  - `python paper_compare/perplexity_burstiness.py <file>` — deep anti-homogenization metric
    (GPT-2 per-sentence perplexity: mean=predictability, sd=burstiness). `transformers` is
    installed. Compare to `homogenization_baseline.md`; a DROP across a pass = homogenization.
  - Compile: `latexmk -pdf -cd -interaction=nonstopmode paper_compare/v2_skill_draft/main.tex`.

## 3. Option-2 spine
"A weak but conditional edge survives strict evaluation; we map where it holds and where it
inverts." Confident about METHOD; honest about weak NUMBERS; never overclaiming.

## 4. Non-negotiables
- No hallucination (numbers from ledger/`artifacts/`; cites from verified `references.bib` or
  marked `[CITATION NEEDED]`).
- Red lines: no best/outperforms/superior/significant/profitable/well-calibrated/clean-test/
  out-of-sample-proof/final-model/SOTA; no model selected; LightGBM only "numerically highest";
  conditional/calm-bar edge = limitation; PBO/LCB/CIs descriptive; "novel" <= 1; activity =
  eligible-row-count proxy, not volume.
- Three domains (validation n=2 +1.69pp / train-inner control 0.66pp / guarded +0.636pp) NEVER
  fused (no "both exclude zero" merge — a real bug caught in §7).
- Keep 8 pages; keep figures/tables/labels/macros/numbers.

## 5. Your steps (iteration model — PAPER_WORKFLOW.md §8; STOP ON QUALITY, not a count)
1. **Verify Pass A is done:** `python paper_compare/check_integrity.py "paper_compare/v2_skill_draft/sections/*.tex"`
   — all should pass. Finish any straggler's Pass A (logic-reviewer + writing-reviewer -> fix -> gate) first.
2. **Pass B (whole paper):** deploy `academic-writing-agents:consistency-checker` +
   `academic-writing-agents:logic-reviewer` across ALL sections — terminology, cross-refs,
   abstract<->intro<->conclusion alignment, cross-section fusion, figure-caption alignment, and
   EXEMPLAR-CONFORMANCE (does each section use the playbook moves?). Fix; gate; compile.
3. **Pass C (whole paper):** naturalness/anti-homogenization — humanizer meta-audit, then re-run
   `perplexity_burstiness.py` on ALL sections and compare to `homogenization_baseline.md`. If any
   section's mean perplexity or burstiness_sd DROPPED materially, that pass homogenized it — revert
   that change. Target = reads like the exemplars, not "smoother".
4. **Citation-validator (build it):** a script that checks every `\cite` key in the compiled draft
   resolves to a real paper via the Semantic Scholar API (existence + title/author/year). Network
   via `curl` works even though WebFetch is down. Report unresolved/placeholder cites. (This is the
   PaperOrchestra-style verification upgrade; `references.bib` has open VERIFY items.)
5. **Codex adversarial review (milestone):** `docs/protocols/lst_models_blind_review_handoff.md`
   with Codex-Reviser (a DIFFERENT model) — audits CLAIMS / overclaiming (esp. that Option-2 has
   not crossed the line). Report the verdict to the user; do not auto-apply claim changes.

## 6. Anti-homogenization (the user's #1 worry)
Never repeat an identical loop; each pass = different focus. Anchor to the human exemplars, not
"smoother" prose. After each whole-paper pass, re-run `perplexity_burstiness.py` vs the baseline
and STOP if numbers drop. Use Codex (different model) for the adversarial review. Diff each pass;
if it's word-shuffling without clear gain, stop.

## 7. Verify (anti-laziness, per section / per pass)
[ ] `check_integrity.py` passes  [ ] compiles, 8 pages, 0 undefined refs  [ ] numbers match the
ledger (checked by hand)  [ ] three domains not fused  [ ] perplexity/burstiness not dropped vs
baseline. Show the user diffs. Don't trust agent self-reports — verify numbers independently.

## 8. Finish
Refresh `paper_compare/NEW_v2_skill_draft.pdf`, report changed sections + gate status + page count
+ perplexity deltas + citation-validator results + the Codex verdict.

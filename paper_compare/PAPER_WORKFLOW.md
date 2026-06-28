# Master paper workflow (v2) — how the whole thing fits together

The single source of truth for how we write/revise the v2 paper. Supersedes the loop in
`WRITING_WORKFLOW.md` (kept as input). Other docs are inputs/evidence:
`V2_PLAN.md` (materials/results/framework), `REDLINE_AUDIT.md` (red-line verification),
`EXPERIMENT_ANALYSIS.md` (mined characteristics), `EXEMPLAR_PAPERS.md` (style targets).

## 1. The stack (what each piece does)
- **Engine — `academic-writing-agents` (`/academic` orchestrator + 12 specialist agents).**
  The polished, third-party review/draft/polish system. Carries 30 writing principles
  (A–F). This is the per-section draft → review → polish machine.
- **Method — `ml-paper-writing` skill.** ML-paper narrative, Farquhar abstract, structure,
  citation-verification discipline.
- **Governance (OVERRIDES everything) — the project's own rigor:** claims ledger
  `paper/outline_and_claims.md`, the red lines, the three evidence domains, the Option-2
  spine, the anti-AI style guide grep gates, the no-hallucination rule.
- **Naturalness lens (optional, scoped) — `humanizer`.** A subset of principle B8; use only
  its rhythm/specificity/meta-audit. Soul/opinion/first-person OFF. De-hyphenation OFF.
- **Style targets — exemplar playbook** (`EXEMPLAR_PAPERS.md` + distilled `exemplars/playbook/`).
  Structure/logic moves only, never copied text. (Download deferred — web outage; see Gaps.)

## 2. Precedence (when two rules conflict, higher wins)
1. AGENTS.md research safety + no fabrication.
2. Claims ledger numbers/claims + red lines + three evidence-domain separation.
3. Anti-AI style guide (8 grep gates).
4. `academic-writing-agents` 30 principles + `ml-paper-writing`.
5. `humanizer` / exemplar moves.

Resolved conflicts (watch for more):
- Principle **B6** ("calibrated confidence") shows assertive verbs like *outperforms* — the
  **red lines override**: never "outperforms/best/significant". Assertive verbs are allowed
  only for ledger-bound facts and only in red-line vocabulary ("exceeds the same-row dummy",
  "meets the predeclared criteria").
- humanizer's "add soul / use I / feelings" — **forbidden** (breaks academic register + red lines).

## 3. The Option-2 spine (the narrative every section serves)
A weak but conditional edge survives strict evaluation; we map where it holds and where it
inverts. Confident about the METHOD; honest about the weak NUMBERS; never overclaiming.

## 4. Per-section loop (the process)
0. **Load context:** governance (this file + ledger + red lines), the Option-2 spine, and the
   1–2 relevant exemplar-playbook files (when available). Never load a whole exemplar paper.
1. **Draft** (`section-drafter` or `ml-paper-writing`), every number bound to the ledger.
   Carry the **3-evidence-domain checklist** (official validation / train-inner control /
   guarded) and the red-line vocab into the draft; confirm all three domains are represented
   and consistently labelled BEFORE review. (Pilot round 1: the drafter silently dropped the
   train-inner domain, creating a "two domains" contradiction the reviewer had to catch.)
2. **Local logic check** (`logic-reviewer`, LIGHT — GitHub `逻辑检查` discipline): fatal gaps,
   term drift, unsupported claims only. High tolerance (prevents churn).
3. **De-AI / style** (`writing-reviewer` → `prose-polisher`) + anti-AI grep gates; optional
   humanizer meta-audit ("what still sounds AI?").
4. **Cross-context coherence** (`logic-reviewer`, principles A2/A4/A6) — paragraph-to-paragraph
   transitions, "close every paragraph", Goal-Problem-Solution rhythm. **This is the fix for the
   #1 problem (disjointed inter-paragraph logic).**
5. **Integrity gate**: run `python paper_compare/check_integrity.py <file>` (automated:
   red-line tokens, "two domains", Tier-1 vocab, phrase blacklist, >35-word sentences; warns
   on em-dash / unnegated guarded phrases / opener chains). This replaces the fragile manual
   greps that broke in pilot round 1. **Also run `python paper_compare/sync_check.py` (ADR 0003):
   the v2 ledger + bib must be byte-identical to the authoritative live `paper/` copies — drift
   fails the gate.** Then MANUAL: every number traces to ledger/artifact;
   the three domains are not fused; 8-page check (compile).
6. **Persist + stop:** write findings to `.review/`; HARD CAP ≤2 review→fix cycles per section.
   If a sentence still won't settle, FLAG it to the user — do not re-hedge in circles (the old
   60-round failure).

## 5. How to invoke
- Per section, parallel review: deploy `logic-reviewer` + `writing-reviewer` +
  `consistency-checker` + `technical-reviewer` (each prompt carries the governance), then
  `prose-polisher` / `section-drafter` to fix; OR run `/academic <task>` (it auto-reads the
  governance via `.claude/CLAUDE.md`).
- **Mandatory after every action-agent edit:** re-run the integrity gate (numbers + red lines +
  grep gates). Generic agents do not know our red lines unless we check.
- I (main loop) verify agent outputs (numbers, red lines) before accepting — agents are generic
  and can drift.

## 6. Known gaps / defects (honest)
1. **Web outage** (this session): exemplar PDF download + new-citation API verification are
   blocked. Mitigation: reuse the verified `references.bib`; defer new citations + exemplar
   distillation until web returns. The 30 principles + `ml-paper-writing` cover structure meanwhile.
2. **Generic action agents can overclaim** (e.g., prose-polisher "improving" a hedge into a
   claim, or stripping a data-required hedge). Mitigation: inject governance into every agent
   prompt + mandatory integrity gate after each edit. This is the biggest live risk.
3. **Number↔ledger binding is still manual.** The style/red-line/length gate is now AUTOMATED
   via `paper_compare/check_integrity.py` (built in pilot round 1, fixing the fragile manual
   greps). What remains manual is confirming each number actually matches the ledger value —
   the checker tests vocabulary/structure, not numeric correctness.
4. **Principle conflicts** beyond B6 may exist; the precedence list resolves them, but each new
   section should be scanned for a generic principle that fights a red line.
5. **Orchestrator expected `.claude/CLAUDE.md`, project uses `AGENTS.md`.** Bridged: a minimal
   `.claude/CLAUDE.md` now defers to AGENTS.md and points at this workflow + ledger.
6. **Churn risk** from multi-agent review (reviewers always find something). Mitigation: the ≤2
   cycle cap + flag-don't-spin rule.
7. **Doc sprawl** (6 planning docs). Mitigation: THIS is the master; the rest are inputs/evidence.
8. **Verification burden** on the main loop (me) is real — skipping it reintroduces hallucination
   risk. It is non-optional.
9. **Token cost**: the orchestrator can deploy many agents + `ultrathink`. Deploy judiciously
   (not all 12 per section); a single section needs ~3–4 reviewers, not the full roster.

## 7. Status (updated)
- Done: governance wired (`.claude/CLAUDE.md`); workflow consolidated (this file); automated
  gate `check_integrity.py` (now incl. a burstiness warn); exemplar playbook built
  (`exemplars/playbook/`); 2 exemplar PDFs downloaded (`exemplars/pdfs/`).
- v2 Option-2 done, gate-clean, compiles 8pp: **abstract (main.tex), §1 (01_intro.tex),
  §7 (07_guarded_walkforward.tex)**. Also gate-passing: §6, §9.
- PENDING Pass A: **§2, §3, §4, §5, §8** (protocol-forward emphasis + minor >35-word sentences;
  §4 has a "final model" warn to verify is negated).
- Queued for web recovery: ICAIF venue-fit exemplar (Chalkidis & Savani) download; any NEW
  citation verification.

## 8. Iteration model (multi-pass, quality-stop, anti-homogenization)
Do NOT run the same loop 2--3 times: repeated identical LLM passes homogenize prose toward an
AI-sounding mean and flatten rhythm. Run DIFFERENTIATED passes and STOP ON QUALITY, not a count.
- **Pass A (per section):** inner loop -- dedicated logic-reviewer + writing-reviewer -> fix ->
  `check_integrity.py` -> compile. Structural / flow / de-AI. (Done: abstract, §1, §7.)
- **Pass B (whole paper):** consistency-checker + logic-reviewer across ALL sections --
  terminology, cross-refs, abstract<->intro<->conclusion alignment, cross-section fusion,
  figure-caption alignment, and EXEMPLAR-CONFORMANCE (does each section use the playbook moves?).
- **Pass C (whole paper):** naturalness / anti-homogenization -- burstiness (sentence-length
  variance via `check_integrity.py`, plus the deeper GPT-2 per-sentence perplexity + burstiness via
  `paper_compare/perplexity_burstiness.py` -- compare each pass to the IMMEDIATELY PRECEDING pass
  (a pass-over-pass log in `homogenization_baseline.md`), not to an absolute bar nor only to the
  first snapshot), humanizer meta-audit ("what still sounds AI?"), measured against the exemplar
  playbook (target = reads like the human exemplars, not "smoother").
  **Burstiness/perplexity is DIAGNOSTIC, not auto-revert (ADR 0001):** a drop attributable to a
  gate-mandated edit (>35-word split, red-line rewrite) is logged as expected; only an UNEXPLAINED
  drop is investigated as homogenization. The HARD >35-word rule always wins a direct conflict with
  the burstiness warning. After each pass, ADD a dated column to the log; never overwrite history.
- **Citation validation (adopted from PaperOrchestra): BUILT + RUN (2026-06-28).**
  `paper_compare/validate_citations.py` (robust \cite+.bib parser; SS batch -> title-search
  fallback; Crossref/arXiv cross-check). Result: 40/40 cites confirmed real, ZERO hallucinations;
  caught + fixed a venue error (sun2017 ICCSE->BIGCOM) and added DOIs to both bibs. Residual = 2
  human VERIFY-before-submit items only: hofman2023preregistration (arXiv-only, no peer venue),
  li2026finsaber (KDD 2026 D&B proceedings metadata once published). Report:
  `v2_skill_draft/.review/citation_findings.md`.
- **Codex adversarial review (milestone):** the blind-review handoff
  (`docs/protocols/lst_models_blind_review_handoff.md`) with Codex-Reviser, a DIFFERENT model --
  re-stress-tests CLAIMS / defensibility / overclaiming (esp. that Option-2 has not crossed into
  overclaiming). Run once on the assembled full draft, or on-demand if a round feels off.

STOP when: gate passes + a fresh review finds nothing Critical/Important + naturalness audit
clean + exemplar moves present. More passes after that make it worse.

Anti-homogenization safeguards (every pass): (1) never repeat an identical loop; (2) anchor to
the human exemplars, not "cleaner prose"; (3) track burstiness as a DIAGNOSTIC in the
pass-over-pass log (ADR 0001) -- investigate unexplained drops, but never auto-revert a
gate-mandated edit; (4) diff each version against the prior -- if changes are word-shuffling
without clear gain, STOP; (5) use a different model (Codex) for the adversarial review; (6) keep
human-ness signals already approved (specific phrasing, varied openings).

# Pass B (whole-paper cross-section) — findings + triage

Run: 3 read-only review agents (consistency-checker, logic-reviewer, technical-reviewer),
each carrying full governance (Option-2 spine, red lines, 3 domains, term table, exemplar moves).
Main-loop verified every agent claim against the live files + ledger before acting.

## Independent number audit (main loop, vs ledger + artifacts) — 0 discrepancies
All load-bearing numbers verified, incl. higher-precision guarded sub-numbers against artifact CSVs:
- guarded multiplicity (`05_row_pooled_multiplicity.csv`): LightGBM mean +0.726pp, LightGBM
  period-LCB -0.030pp, TCN period-LCB +0.047pp, PBO 0.514, TCN row-pooled +0.636pp — all exact.
- validation budget (`05_validation_budget_ledger.csv`): 2 official-validation / 56 guarded events.
- guarded pooled CI [0.24,1.02]pp = [0.2409,1.0153] from `05_fig2_uncertainty/fig2_bootstrap_ci.csv`.
- guarded tercile counts 95,310/111,178/119,479 + deltas +4.08/+0.56/-2.10pp from
  `05_guarded_activity_tercile.csv`; up-rates 0.523/0.515/0.502.

## Headline verdict
- technical-reviewer (red-line + 3-domain): **0 CRITICAL.** No domain fusion (the previously-caught
  §7 bug is verifiably absent), no red-line vocab, full Tier-G compliance, no model selected,
  "novel" appears 0 times, LightGBM only "numerically largest", activity = row-count proxy.
- consistency-checker: 0 number contradictions; all \ref/\label resolve; no orphan floats.
- logic-reviewer: question-chain (validation->guarded->where it lives) IS built; all 5 deflationary
  exemplar moves PRESENT.

## APPLIED (clear, correct, ledger-aligned, low-risk)
1. `01_intro.tex:53` "macro-F1 ECE" -> "equal-mass ten-bin ECE" (category error; ECE is a
   probability metric, not F1; matches §8 + ledger C3.1). [agents over-attributed this to the
   abstract too; verified the abstract has NO ECE — fix is intro-only.]
2. `01_intro.tex:1-3` corrected false header comment ("Does NOT replace 01_intro.tex" — it IS the
   live intro); removed em-dash.
3. `06_results.tex:17,18,51` `\pp` -> `\pp{}` (notation consistency).
4. `07_guarded_walkforward.tex:34` "four roster rows" -> "four families" (term consistency w/ §4,§7).
5. `09_limitations_conclusion.tex:11` added calibration to the diagnostics recap + "the confidence
   scores cannot define an operating rule" — reconciles the intro's "two diagnostics" framing
   (calibration was dropped from the conclusion). Mirrors §1 phrasing.
6. `07_guarded_walkforward.tex:17,36` "inside V2" -> "within the project"; "V2.1 refits" ->
   "walk-forward refits" (remove undefined internal version tags from blind submission).

Gate: all sections PASS. Compile: 8 pages, 0 undefined refs.

## NOT APPLIED — flagged for user / Codex (subjective, or anti-churn / homogenization risk)
- Transitions (logic I4 §2->§3 cold restart; I6 §6 "How the bands are computed" methods digression
  mid-results; I7 §7 internal; I8 §8->§9). Real but subjective prose-flow rewrites; question-chain
  and exemplar moves already confirmed present; rewriting risks homogenization (Pass C) + churn.
- "balanced random prior" not formally defined in §3 (logic C2). Defined locally in §8:62
  (≈0.498 even-class) vs the declared stratified-dummy floor (≈0.500). Abstract usage is
  self-evident; judgment call whether to add a §3 definition.
- Minor label variation for the ≈0.498-0.500 reference ("even-class value/prior", "random prior",
  "balanced random prior", "near-even floor"). Acceptable local usage; §8 anchors it.
- "estimand" used for both target-definition and aggregation-unit (logic I9). Arguably correct
  (row-pooled vs equal-weight ARE different estimands).
- `03_protocol.tex:44` "Stage~00 freeze" — mild internal jargon; reads as "initial data freeze".
- Abstract omits calibration (length-constrained, 8pp hard limit); conclusion now covers it.

## Cross-window items (technical IMP x3) — checked, already adequately hedged, no edit
- `08:71-72` "stable across both windows" preceded by "non-independent re-aggregation, not an
  independent replication" (08:70-71).
- `08:80` table caption "in both domains" — same caption already says "guarded is non-independent"
  (08:78-79).
- `main.tex:61` "recurs across both windows" — hedged by bid-ask caveat; abstract earlier states
  the guarded readout "is not a clean test".
All three cross-window claims are ledger-SANCTIONED (C4.5 / open-item #1 authorize the cross-window
conditional-pattern recurrence). Not fusion (per-domain numbers kept separate).

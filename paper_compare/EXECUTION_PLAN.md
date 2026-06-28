# Execution plan — run both workflows on the paper (autonomous, branch-isolated)

Designed via brainstorm + grill (2026-06-28). Goal: take v2 (at Codex GO, in the sandbox) all the
way to a submission-ready live `paper/`, running **autonomously in a new window** with exactly **one
human gate** (approve the branch merge = the ADR-0003 cutover).

## Why a branch (the grilled conclusion)
ADR 0003 forbids auto-overwriting live `paper/`. Working on a dedicated branch makes the whole
promotion + QC reversible: nothing touches live `main` until you approve the merge. The merge IS the
ADR-0003 approval. Everything before it is autonomous and throwaway-able.

## State going in
- v2 (`paper_compare/v2_skill_draft/`) is at Codex **GO**, 8pp, numbers 3x-verified.
- `python paper_compare/promotion_reconcile.py` = **PASS** (v2 satisfies the live manifest).
- Workflow 1 (writing) is done; this run is **promotion + Workflow 2 (revision/QC)** on the result.

## Phases (the loop runs these in order, logging each)
- **P0 Setup** — `git checkout -b paper-v2-promotion`. Confirm v2 GO + `promotion_reconcile.py` PASS;
  STOP+report if not.
- **P1 Promote (branch only, reversible)** — copy v2's `main.tex`, `sections/`, `references.bib`,
  `figures/` -> `paper/` (NOT `outline_and_claims.md` — the live ledger is already authoritative and
  in sync). Commit on the branch.
- **P2 Gate authority shift** — run the `paper/scripts/` stack (`length_gates` L1-L5, `latex_inventory`,
  `gate_selftest`, anti-AI grep) + compile (8pp, 0 undefined). Fix only mechanical issues; STOP on any
  claim/number issue.
- **P3 QC matrix** — re-run all 17 rows of `lst_models_submission_qc_matrix.md`
  (`table_audit`, `anchor_lint`, `pdf_hygiene`, citation closure); record PASS/FAIL/N-A + evidence into
  a fresh `paper/length_loop/runs/<id>/` report.
- **P4 Adversarial review** — `codex exec -s read-only` whole-draft vs the red-line/three-domain
  contract WITH the C2.3/C4.5 sanctioning (blind-review-handoff §4) -> GO/NO_GO. Adjudicate
  false-positives against the ledger; log only GENUINE findings.
- **P5 Synthesize** — zero genuine P0/P1 -> write a submission-ready report + STOP at
  "ready to merge paper-v2-promotion -> main". Genuine claim findings -> list (file:line +
  recommendation) and STOP; do NOT auto-apply claim changes (governance).

## Human gates (only these)
1. Any GENUINE claim-framing finding from P4 (likely few/none — v2 is at GO).
2. **Approve the branch merge -> main** (the real cutover).

## Deferred — NOT autonomous (need your decisions)
- Hedge-dedup floors execution (ADR 0005 note: re-derive against v2 first; the design has open
  user decisions).
- The 2 bib VERIFY items (`hofman2023`, `li2026finsaber`).

## Efficiency stop rule (PAPER_WORKFLOW §9)
A review round whose findings are ALL false-positive / already-adjudicated = converged: stop, do not
re-loop.

---

## Paste this as the /loop task in the new window
```
/loop Run the full paper pipeline autonomously to produce a submission-ready paper, on a dedicated
branch so nothing irreversible touches live main until I approve the merge. Read first (all tracked):
paper_compare/PAPER_WORKFLOW.md (§10), paper_compare/EXECUTION_PLAN.md, docs/adr/0003 + 0005,
docs/protocols/lst_models_paper_revision_workflow.md + lst_models_submission_qc_matrix.md,
paper/outline_and_claims.md. Obey AGENTS.md + the red lines; never fabricate; never auto-apply a
claim-framing change (flag those). Execute EXECUTION_PLAN.md phases P0-P5 in order, logging each:
branch paper-v2-promotion; confirm v2 GO + promotion_reconcile.py PASS; promote v2 prose -> paper/ on
the branch; run the paper/scripts L1-L5 stack + compile (8pp); re-run the 17-row QC matrix into a
runs/<id>/ report; run codex exec -s read-only adversarial review WITH the C2.3/C4.5 sanctioning and
adjudicate false-positives against the ledger; then if zero genuine P0/P1 STOP at "ready to merge" for
my approval, else list genuine findings and STOP. Defer hedge-dedup + the 2 bib VERIFY (need my
decisions). Use the §9 efficiency stop rule: an all-false-positive round = converged, stop.
```

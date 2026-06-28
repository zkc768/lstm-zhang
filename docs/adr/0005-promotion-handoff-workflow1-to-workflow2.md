# Promotion handoff: Workflow 1 (sandbox writing) -> Workflow 2 (revision/QC)

**Status:** accepted (2026-06-28)

The project has two workflows that did not reference each other: Workflow 1 — the v2 sandbox writing
loop (`paper_compare/PAPER_WORKFLOW.md`, Pass A/B/C + Codex) operating on
`paper_compare/v2_skill_draft/`; and Workflow 2 — the per-round revision + final-QC family
(`docs/protocols/lst_models_paper_revision_workflow.md` + blind-review-handoff + external-codex
adapter + submission-QC matrix) operating on the live `paper/` with the heavy machinery
(`protection_manifest.json`, `round_diff.py` L1-L5, length-loop, the 17-row QC matrix).
`revision_workflow.md` had **zero** awareness of v2, and the only bridge (promotion, ADR 0003) was
wired into neither doc.

**Decision:** Promotion is the explicit handoff, run as a checklist:
1. **Pre-promotion** — v2 at STOP (gate PASS + Codex GO + every number ledger-bound + domains separate).
2. **Manifest reconcile (gate)** — run `paper_compare/promotion_reconcile.py`: v2 must satisfy the
   live `protection_manifest.json` (required_phrases 26/26, caption_locks, never_delete invariants;
   forbidden_terms WARN-only for cite-key/foil false-positives). Today it PASSES, so promotion will
   not break Workflow 2's manifest-based gates.
3. **Promote** — copy `v2_skill_draft/* -> paper/`, presented to the user as a `git diff` for
   approval (ADR 0003); never auto-executed.
4. **Post-promotion gate authority** — the `paper/scripts/` L1-L5 stack + `protection_manifest.json`
   + `round_diff.py` become authoritative; the sandbox gates (`check_integrity.py`, `sync_check.py`)
   retire (they were sandbox-only). This resolves the two-gate-stack redundancy.
5. **QC re-run** — re-run the full 17-row submission-QC matrix on the promoted paper (its current
   PASS statuses are v1 / r026 state and are invalidated by promotion).
6. **Cross-reference** — `PAPER_WORKFLOW.md` and `revision_workflow.md` now point at each other and
   at this handoff.

**Consequences:** the two workflows form one coherent pipeline (write in the sandbox -> reconcile ->
promote -> revise/QC on live), with a repeatable, testable promotion gate instead of an implicit
overwrite. The reconcile script makes "is v2 promotable?" a measured answer, not a hope.

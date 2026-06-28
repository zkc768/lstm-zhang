# v2 sandbox: single source of truth + explicit promotion to live paper/

**Status:** accepted (2026-06-28)

The v2 rewrite lives in `paper_compare/v2_skill_draft/`, isolated from the live `paper/`. But the
claims ledger is forked into 3 copies (`paper/`, `v1_current/`, `v2_skill_draft/`),
`references.bib` is dual-maintained in `paper/` and `v2/` (the citation fix had to be applied to
both by hand), and live `paper/` is untracked in git. All copies are in sync today only by manual
discipline — nothing enforces it — and there is no defined step for turning v2 into the submission.

**Decision:** (1) The LIVE `paper/outline_and_claims.md` is the **single authoritative ledger**;
the `v2_skill_draft/` copy is a **read-only mirror**, never hand-edited. Same rule for
`references.bib`. (2) `paper_compare/sync_check.py` is added to the gate: it asserts
`md5(v2 ledger) == md5(live ledger)` and `md5(v2 bib) == md5(live bib)` before every pass; any
drift FAILS. Canonical edits are made in the authoritative copy and mirrored by a copy command,
never by editing both files. (3) Before promotion, the frozen `v1_current/` snapshot (or `paper/`
itself) must be committed as a rollback point. (4) **Promotion is the terminal stage:** after
Codex-clean + gate-clean + numbers re-bound + `sync_check` pass, promotion copies
`v2_skill_draft/* -> paper/` and is presented to the user as a `git diff` for approval — it is
**never auto-executed**; the user makes the irreversible cutover call.

**Consequences:** drift between sandbox and live becomes impossible to miss; promotion is a
reviewable, reversible diff with a rollback; the human retains the cutover decision.

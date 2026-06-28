# lst_models External Codex Reviser Adapter

Status: extends `AGENTS.md`,
`docs/agent_capabilities_and_skill_routing.md`, and
`docs/protocols/lst_models_paper_revision_workflow.md`; never overrides them.

Purpose: define how an external Codex session may act as a Reviser for
`lst_models` paper prose without bypassing the existing candidate, gate,
adversarial-review, and synthesizer path.

## Scope

External Codex may draft paper-prose candidates only.

External Codex must not edit:

- `paper/sections/*`
- `paper/main.tex`
- `paper/length_loop/state.json`
- `paper/length_loop/protection_manifest.json`

External Codex must not decide `ACCEPT`, `REPAIR`, `ROLLBACK`, or final
submission readiness. Those decisions remain with the existing workflow
orchestrator and synthesizer.

## Hard Contract

External Codex may only write candidate artifacts under:

`paper/length_loop/runs/<round_id>/`

Expected candidate output:

- `candidate_<section>.tex`
- optional `PLAN.md`
- declared metadata block
- nonexpert evidence table

Per the existing paper revision workflow, the candidate must return to the
orchestrator for `round_diff.py`, L1-L5 gates, adversarial review, synthesizer
decision, apply, and post-apply verification. This adapter does not restate
those rules; it only constrains the external Reviser entry point.

## Enforcement

Default requirement: run external Codex with write access limited to the
candidate run directory. `paper/sections/*`, `paper/main.tex`,
`paper/length_loop/state.json`, and
`paper/length_loop/protection_manifest.json` should be read-only to the
external session.

If that sandbox is not available, the orchestrator must treat the live-sha
sweep below as a detection fallback only. It can detect live drift before
apply; it does not prevent the drift from happening.

Before dispatching work to external Codex, the orchestrator must:

1. Recompute every live paper section hash.
2. Compare each section against
   `paper/length_loop/state.json::sections_status[*].post_apply_sha256`.
3. Define the authorized manifest hash for the round.
4. Stop or re-freeze if any live section, state file, or manifest drift is
   found.

Before applying any candidate, the orchestrator must repeat the full live
section hash sweep and manifest/state check.

Rules:

- `declared_parent_sha256` from external Codex is declared-only, not authority.
- If `declared_parent_sha256` differs from the orchestrator-authorized section
  hash, mark a red flag and re-freeze before review.
- `current_matches_frozen_baseline` in `gate_report.json` is not a live-drift
  authority.
- The orchestrator must compare external Codex-declared `touched_claim_ids`
  against L1-L3 gate results. A "no claim touched" declaration plus gate
  regression is a red flag.
- Any live edit outside the candidate path means `STOP / re-freeze`.

## Kickoff Block

Paste this into every external Codex Reviser session:

```text
You are acting only as External Reviser for `lst_models` paper prose.

Do not edit live manuscript files.
Do not edit:
- paper/sections/*
- paper/main.tex
- paper/length_loop/state.json
- paper/length_loop/protection_manifest.json

You may only draft candidate files under:
paper/length_loop/runs/<round_id>/

Read first:
1. AGENTS.md
2. docs/agent_capabilities_and_skill_routing.md
3. docs/protocols/lst_models_paper_revision_workflow.md
4. paper/outline_and_claims.md
5. paper/length_loop/protection_manifest.json
6. paper/length_loop/state.json
7. the target section file

Return only:
- candidate path
- target section
- declared_parent_sha256
- manifest_sha256
- the three evidence-domain names used by the project
- touched_claim_ids
- touched evidence domains
- required D-locks preserved
- forbidden F-terms avoided
- nonexpert evidence table

Do not decide ACCEPT / REPAIR / ROLLBACK.
Hand the candidate back to the orchestrator for round_diff, L1-L5 gates,
adversarial review, and synthesizer decision.
```

## Nonexpert Evidence Output

For each touched claim or reviewer finding, external Codex must report:

```text
claim_id:
evidence_domain:
evidence_level: <official_rule|artifact_backed|tool_gate|citation_backed|text_consistency|reviewer_judgment>
candidate_change_summary:
can_prove:
cannot_prove:
  - F-id:
    reason:
required_hedges:
  - D-id:
    preserved_or_changed:
needs_human_confirmation:
declared_only_fields:
```

Evidence domains must use project ledger terms, such as:

- `protocol`
- `validation`
- `train-inner`
- `guarded`

`cannot_prove` must cite manifest `F*` ids where applicable.

`required_hedges` must cite manifest `D*` ids where applicable.

External Codex explanations are advisory. Artifact-backed claims, manifest
locks, and orchestrator-run gates are authority.

## Stop Conditions

Stop and return to the orchestrator if:

- external Codex would need to edit live manuscript files
- any live section hash does not match `state.json`
- `state.json` changes outside orchestrator control
- `protection_manifest.json` differs from the orchestrator-authorized manifest
  hash
- the candidate changes numbers, citations, refs, labels, tables, captions, or
  claims outside the allowed plan
- required D-locks are weakened or removed
- forbidden F-terms appear in affirmative form
- external Codex-declared touched claims conflict with L1-L3 gate results
- the candidate touches a claim whose evidence boundary is unclear
- human, advisor, venue, or official tool confirmation is needed

## Output Boundary

This adapter does not create a new paper workflow.

It only defines how external Codex may enter the existing workflow without
bypassing candidate isolation, deterministic gates, adversarial review,
synthesizer control, or orchestrator-owned live-state checks.

# 06 Ian Final Progress Record Protocol

Status: pre-registration core, frozen 2026-06-09; operational detail will be
completed in Batch E without changing this section.

Scope: V2 `lst_models` route only. This document freezes the Stage 06
evidence standard (roadmap decision D4) before the Stage 03
official-validation readout executes. Stage 06 closes the route as a progress
record; it is not a test readout and it does not select, rank, or crown a
model.

Decision provenance: D4 was frozen as the recommended default, option (a).
Sign-off quoted from `docs/lst_models_v2_route_roadmap.md` Phase 2:

> SIGN-OFF RECORD: user approved all four recommended defaults ("按推荐"),
> 2026-06-09. The choices below are frozen inputs for Batch B; changing any of
> them after the Stage 03 readout executes is forbidden.

Section freeze map: sections 2-6 are the frozen D4 core and are unchangeable
after the Stage 03 readout executes. Section 7 names the operational surface
that Batch E completes without weakening sections 2-6.

## 1. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- the target notebook, config, module, or test

Before writing code, the implementer MUST record a placement decision with the
AGENTS.md §2 fields. For this protocol edit:

```text
placement_decision:
  target_file_type: protocol
  target_path: docs/protocols/06_ian_final_progress_record_protocol.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; pre-registration protocol text only
  why_not_utils: not applicable; pre-registration protocol text only
  safety_tests: not applicable at core freeze; Batch E adds the Stage 06 test triad
```

Implementation must preserve:

- Colab-first execution; one user-facing Stage 06 notebook.
- `src/lst_models/stages/ian_final_progress_record.py` only if executable
  logic is actually needed (roadmap Phase 7); no framework expansion.
- No holdout/test read, transform, window, score, or summary; no rows at or
  after `2017-01-25`.
- Manifest `holdout_test_contact=false`; durable Drive result save.

## 2. Stage Role And Evidence Standard (frozen D4)

Stage 06 = progress record + reproducibility inventory.

- The closed holdout/test segment (rows at or after `2017-01-25`) stays
  closed. Stage 06 makes zero contact with it.
- Final claims remain validation-only. Stage 06 reports what the route did,
  under which frozen rules, with which validation-only outcomes.
- Stage 06 adds no new scoring of any kind: no validation scoring events, no
  holdout/test scoring events, no model fits.

## 3. Reproducibility Inventory (frozen D4)

For every stage 00-05 frozen run, the record must list:

- exact run ids
- exact git commits (including pinned notebook bootstrap commits)
- artifact sha256 values, sourced from each run's `artifact_inventory.csv`
- Drive folder ids of the durable result folders under
  `My Drive/lst_models/results/<stage_name>/<run_id>/`

## 4. Honesty Section (frozen D4)

The record must state, without softening:

- The V1 route historically contacted the post-2017 segment.
- If that segment is ever opened in the future, it yields only a
  "guarded, historically-contacted test", not a clean test.
- A clean final evaluation would require either future-blind data collected
  after the V2 freeze, or pre-registered external tickers. Both are V2.1
  options requiring their own pre-registered protocols.
- Silently upgrading this progress record into a test claim is forbidden.

## 5. Ian-Requirement Mapping (frozen columns; rows completed in Batch E)

The record must contain one mapping table with exactly these columns. Batch E
fills the rows from the Ian/Lan requirement list without changing the schema:

| requirement | stage | artifact | status |
|---|---|---|---|
| to be completed in Batch E | | | |

## 6. Wording Rules (frozen)

Stage 06 inherits the Stage 03 forbidden list. Forbidden strings:
`final model`, `official validation winner`, `holdout winner`, `test winner`,
`proved best model`, `generalization proven`, `profitable`, `holdout-ready`,
`selected by official validation`, `chosen threshold`.

Allowed wording: `validation-only evidence`, `official validation readout`,
`candidate met/did not meet predeclared validation-readout criteria`.

## 7. Operational Detail (to be completed in Batch E)

Batch E completes the following without changing sections 2-6:

- Exact Stage 06 artifact names, schemas, and run-folder layout.
- `configs/stages/06_ian_final_progress_record.yaml`.
- `notebooks/06_ian_final_progress_record_colab.ipynb`.
- Test triad: config contract, smoke (if a runner exists), notebook static
  gate.
- The filled Ian-requirement mapping rows and the route-closure or explicit
  V2.1 pre-registration statement (roadmap Phase 7 exit gate).

# 05 Thesis Synthesis Protocol

Status: bundle created 2026-06-18 (Batch D, B5). Measure-only synthesis home
for the route. Stage 05 is **packaging and aggregation only**: it reads frozen
Stage 03 / Stage 04 / V2.1 artifacts and emits synthesis tables. It performs
**zero new fits, zero new scoring events, and no reselection**.

Revision record:

- 2026-06-19 (B8): built the FIX-1 minimal analysis package (measure-only, small
  aggregates only). `05_estimand_contrast.csv` — the 2×2 {evidence domain} ×
  {aggregation} headline macro-F1 delta surface: the two guarded estimands READ
  from the frozen V2.1 record (row-pooled binding + equal-weight-over-periods
  companion), the two official-validation estimands READ from the intra-stage
  selective autopsy frame (row-pooled = pooled `all`/seed-mean delta; equal-weight
  = regime-balanced mean over activity terciles), each row naming its `weight_unit`
  because the equal-weight unit differs by domain (period vs tercile — not
  cross-domain comparable). `05_loo_robustness.csv` — EQUAL-WEIGHT leave-one-out
  of the guarded delta on the frozen primary: LOO-period (drop each walk-forward
  period) + LOO-ticker (drop each ticker), with per-sweep `loo_sign_flip`. The
  binding estimand is row-pooled and macro-F1 is non-linear across rows, so a true
  row-pooled LOO needs the raw `v2_1_predictions.csv` (Drive-only); it is recorded
  as a deferred marker row, never silently equated with the equal-weight LOO. New
  inputs gated: `v2_1_period_summary.csv`, `v2_1_per_ticker_readout.csv`.
  Descriptive estimand/robustness surface only — no estimand promoted to "the"
  result. Still deferred: the row-pooled LOO from the raw dump.
- 2026-06-18 (B7): built the selective- and calibration-aware autopsy over the
  frozen Stage 03 validation dump → `05_selective_autopsy.csv`. Per activity
  tercile × seed: model macro-F1 / accuracy, whole-curve AURC / e-AURC / AUGRC
  (wires the 0-call-site `augrc` primitive) on (confidence, correct), and the
  delta-vs-dummy MDE EXTRACTED from the frozen Stage 04 per-trading-day block
  bootstrap (`delta − lcb`; the register mandates reusing the existing bootstrap
  rather than re-deriving the train-prior baseline). Crosses abstention with the
  activity tercile (register F1). Selective metrics are accuracy-based with no
  cost/return — a diagnostic, never an operating point (register F4). Stage 05
  now reads the frozen `03_validation_predictions.csv` (gated/derived via the
  shared `diagnostics.gate_and_derive_dump`). Still deferred: B8 (four-estimand
  + LOO).
- 2026-06-18 (B6 + review hardening): built the descriptive multiplicity
  discount (CSCV PBO + worst-family `min_family_lcb`) over the
  per-(family, period) guarded delta matrix → `05_multiplicity_discount.csv`.
  PBO uses average ranks (ties neutral) and a labeled odd-block floor/ceil CSCV
  adaptation for the 7 periods; it FAILS CLOSED on an incomplete 4×7×2 roster;
  seed aggregation (`mean_over_seeds`) is surfaced. PBO/LCB are descriptive
  discounts only. Also hardened the home from adversarial review: claim→artifact
  gating, an upstream-decision gate, scoring-event ledger-length integrity, and
  accuracy-vs-macro-F1 metric labeling. Still deferred: B7 (AUGRC/MDE/
  abstention) and B8 (four-estimand + LOO).
- 2026-06-18: initial bundle (B5). S5.1 validation-budget ledger, S5.2 claim
  boundary register, S5.3 expectation calibration, S5.5 KB wording guardrails,
  plus the synthesis report and manifest. The heavier measure-only analyses
  that this home unblocks — descriptive PBO/CSCV + `min_family_lcb` over the
  56-event guarded ledger (B6), AUGRC / MDE / abstention×activity cross (B7),
  the four-estimand recompute + LOO-period/LOO-ticker (B8) — are recorded as
  `deferred_synthesis_items` in the report and added as additional synthesis
  functions + artifacts in follow-up tasks, within this same §2 boundary.

Scope: V2 `lst_models` route only. This document freezes the Stage 05
synthesis rules from roadmap §8 (Batch D, S5.1-S5.5). Stage 05 is synthesis,
not selection: it cannot change any upstream outcome and never selects a final
model (`no_final_model_selected=true` is carried into every output).

## 1. Implementation Gate

Before writing or changing code for this stage, the implementer MUST read:

- `docs/lst_models_code_style_and_route_guide.md`
- this protocol document
- the target notebook, config, module, or test

Before writing code, the implementer MUST record a placement decision with the
AGENTS.md §2 fields. For this bundle:

```text
placement_decision:
  target_file_type: protocol | stage_config | python_module | test | notebook
  target_path: docs/protocols/05_thesis_synthesis_protocol.md (+ sidecars)
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: synthesis logic is reusable + testable -> domain module
    (src/lst_models/synthesis.py); the runner orchestrates only
  why_not_utils: no broad utility layer; synthesis is a named domain concept
  safety_tests: tests/contracts/test_stage05_config_contract.py,
    tests/stages/test_stage05_run_stage_smoke.py,
    tests/notebooks/test_stage05_notebook_static.py
```

Implementation must preserve:

- Colab-first execution; one user-facing Stage 05 notebook; one
  `run_stage(config)` entry point.
- Measure-only scope: no new fit, no new predict, no re-threshold, no
  recalibration, no reselection; zero new official-validation scoring events
  and zero new guarded scoring events.
- Synthesis numbers trace to a frozen artifact field — Stage 05 never
  hand-types a measured number; every measured value is resolved from a frozen
  upstream decision record / report by field path, fail-closed if missing.
- Domain logic in `src/lst_models/synthesis.py`; orchestration-only runner in
  `src/lst_models/stages/thesis_synthesis.py` (< 700 lines, no `nn.Module`, no
  `inspect.getsource`); the synthesis-mechanism provenance hash
  (`stage05_synthesis_code_sha256`) lives in `lst_models.artifacts`.
- Manifest fields in §6; durable Drive result save per AGENTS.md §5.

## 2. Stage Role And Input Boundary

Stage 05 reads frozen upstream artifacts only, by exact run id:

- Stage 03 frozen validation readout: `03_decision_record.json` (the
  `official_validation_scoring_events` count + scoring-event ledger + the
  `aggregate` validation metrics).
- Stage 04 diagnostics + ablation: `04_diagnostics_report.json` +
  `run_manifest.json` (the `new_validation_fit_predict_events=0` /
  `official_validation_scoring_events=0` measure-only facts and safety flags).
- V2.1 guarded walk-forward readout: `v2_1_decision_record.json` (the
  `guarded_scoring_events` count, the `pooled_delta` estimands, the decision,
  and the `guarded_historically_contacted` tier).

Stage 05 emits ZERO new scoring events of any kind. It does not refit,
re-predict, re-threshold, recalibrate, re-rank, or re-score any model on any
segment. It reads frozen artifacts and aggregates them. The V2.1 record it
reads describes a guarded historically-contacted contact that ALREADY
happened; Stage 05 itself makes no new contact (its own manifest records
`holdout_test_contact=false`, `new_scoring_events=0`).

Run-id chain (binding invariant = a SHARED frozen Stage 03): the Stage 04
diagnostics report and the V2.1 record must both record the configured Stage 03
run id as their `source_stage03_run_id`; a mismatch fails the entry gate closed.
The Stage 04 diagnostics run Stage 05 reads is the canonical sentinel run; the
Stage 04 run V2.1 sequenced after (its `source_stage04_run_id`, an ordering
reference, e.g. an earlier Stage 04 produced before the sentinel re-run) MAY
differ and is recorded in the report (`v2_1_source_stage04_run_id`) for
provenance, not gated for equality — both still chain to the same Stage 03.

## 3. Three Evidence Domains (never mixed in one sentence)

Every synthesized claim names exactly one of three evidence domains, and the
synthesis artifacts tag every row with its domain:

1. `official_validation` — Stage 03 one-shot official-validation readout
   (n=2 seeds, 2013-09 -> 2017-01 segment).
2. `train_inner_control` — Stage 02 / Stage 04 train-inner control comparison
   (no official-validation contact).
3. `guarded_walkforward` — V2.1 guarded, historically-contacted walk-forward
   (2017-01 -> 2024-04 segment).

The claim boundary register (§S5.2) rejects any claim whose declared
evidence domain is not one of these three. Mixing two domains in a single
quantitative comparison is a wording violation, not a synthesis option.

## S5.1 Validation Budget Ledger (required artifact)

Aggregate every official-validation / guarded scoring event across the route
into one auditable table (`05_validation_budget_ledger.csv`). One row per
scoring stage plus a `total` row. The event count for each stage is RESOLVED
from that stage's frozen decision record / report field — never hand-typed:

- Stage 03: `official_validation_scoring_events` (one-shot per frozen
  seed × candidate; segment `validation_2013_2017`).
- Stage 04: `new_validation_fit_predict_events` (must be 0; segment
  `train_inner`, contact `read_frozen_artifacts_only`).
- V2.1: `guarded_scoring_events` (segment `guarded_holdout_2017_2024`, contact
  `guarded_historically_contacted`).

Method anchors: Dwork et al. 2015 (reusable holdout / adaptive analysis),
Cawley & Talbot 2010 (Stage 00 protocol §16). Every row carries
`for_selection=false`.

## S5.2 Claim Boundary Register (required artifact)

Emit a machine-readable claim register (`05_claim_boundary_register.csv`) of
the validation-only / guarded paper-safe claims and the limitation list.
Each declared claim carries: `claim_id`, `evidence_domain` (one of §3),
`is_limitation`, the paper-safe `statement`, and the supporting frozen run id
(resolved from the wired input by `supporting_run_id_key`). The runner
validates that:

- `evidence_domain` is one of the three §3 domains;
- `supporting_run_id_key` resolves to a wired upstream run id;
- the `statement` contains NONE of the forbidden wording (§S5.5 / config
  `forbidden.wording`).

The limitation list assembles the known design facts (register F1-F11): the
activity-conditional edge as a LIMITATION (not a selling point); ±3bps band;
capped-fold HPO regime (Zadrozny 2004); bounded 4-profile grid; pooled-only
scope; 2-seed thinness; macro-F1 ≠ economic value; the V1 historical contact
with post-2017 data.

## S5.3 Expectation Calibration (required artifact)

Emit `05_expectation_calibration.csv` situating the measured deltas against the
published direction-classification context (~50% naive floor; low-to-mid 50s%
typical reported ceiling — roadmap §12; Gu, Kelly & Xiu 2020). Two row types:

- `config_literature` rows — external-knowledge band anchors (value + context
  from config, with citation in the context string).
- measured rows — `value` RESOLVED from a frozen record field
  (`value_source_key` + dotted `value_field`), fail-closed if the field is
  absent. These surface the Stage 03 validation macro-F1 / delta and the V2.1
  pooled-delta estimands (`pooled_delta`, `pooled_delta_equal_weight`,
  `pooled_delta_row_pooled`).

This supports the honest "weak signal, disciplined comparison" framing, not a
performance claim. A small macro-F1 delta is not evidence of tradeability
(register F4); co-locate the calm-bar microstructure caveat (register F1).

## S5.4 Tables / Figures

Thesis tables come from the frozen artifacts above and the three S5.1-S5.3
synthesis artifacts only — no new search, no new scoring. Figure generation
(`figure-generation` skill) consumes the same frozen CSVs. No figure marks,
recommends, or selects an operating point or a final model.

## S5.5 KB Wording Guardrails (carried into the report)

From the reference index and the limitation register, the synthesis report
carries an explicit DO-NOT list (config `kb_wording_guardrails`):

- Do not call DLinear-classification a "published standard".
- Do not present drop-neutral binary results as full-market deployment
  performance.
- Do not compare V1 labels with V2 no-trade labels as the same task.
- Never frame the low-activity (calm-bar) edge as a feature/innovation; it is a
  limitation / conditional-signal diagnostic.
- Theme 2 reads "complex / neural sequence models do not clearly beat trees",
  NEVER "LightGBM best/selected/superior" (`no_final_model_selected` stays true).
- Theme 5 never asserts "well-calibrated" (low resolution).

The runner additionally fails closed if ANY forbidden string (config
`forbidden.wording`) appears in any emitted statement or in the report.

## 6. Required Artifacts And Manifest

```text
results/05_thesis_synthesis/<run_id>/
  05_validation_budget_ledger.csv     (S5.1)
  05_claim_boundary_register.csv      (S5.2)
  05_expectation_calibration.csv      (S5.3)
  05_multiplicity_discount.csv        (B6: descriptive CSCV PBO + min_family_lcb)
  05_selective_autopsy.csv            (B7: AURC/e-AURC/AUGRC + abstention x
                                       activity-tercile + delta-vs-dummy MDE)
  05_estimand_contrast.csv            (B8: 2x2 {domain} x {aggregation} headline
                                       delta surface; weight_unit named per row)
  05_loo_robustness.csv               (B8: equal-weight LOO-period + LOO-ticker of
                                       the guarded delta; row-pooled LOO deferred)
  05_thesis_synthesis_report.json     (decision summary, estimand surface,
                                       multiplicity + selective + estimand/LOO
                                       summaries, guardrails, deferred items)
  run_manifest.json
  artifact_inventory.csv
```

Execution status (2026-06-19): the B5/B6/B7 bundle WAS executed on Colab — run
`20260619_053750_244288` (code commit `96e91ab`), mirrored in-repo with sha256 at
`artifacts/05_thesis_synthesis/20260619_053750_244288/` (the 7 B5-B7 outputs +
manifests). B8 (`05_estimand_contrast.csv`, `05_loo_robustness.csv`) is committed
as code + tests but its TWO artifacts require a NEW Stage 05 run to be frozen —
the run ...244288 predates B8. The B8 numbers in the smoke tests are SYNTHETIC
fixtures exercising the computation path, NOT a verified result; the real B8
numbers are previewed from the frozen V2.1 small aggregates but become claimable
only once the B8 re-run is frozen and mirrored with sha256.

`run_manifest.json` records: `scope=synthesis_measure_only`,
`holdout_test_contact=false`, `official_validation_contact=read_frozen_artifacts_only`,
`new_scoring_events=0`, `reads_guarded_walkforward_artifacts=true`,
`no_final_model_selected=true`, the exact `source_stage03_run_id` /
`source_stage04_run_id` / `source_v2_1_run_id`, `stage05_synthesis_code_sha256`,
`config_sha256`, and `notebook_sha256`. `drive_backup_manifest.json` is written
and uploaded last by the notebook (route guide §11 keeps it out of the runner
required list).

## 7. Execution Discipline

- Stage 05 reads frozen artifacts and writes synthesis tables. No model object
  is constructed; no torch / LightGBM import is required or made.
- Every measured number resolves from a frozen artifact field (fail-closed).
  No sourceless hand-typed numbers (claim-ledger rule).
- The committed config stays runnable but inert by default (notebook
  `RUN_STAGE05=False`); the notebook injects runtime run-dir paths into the
  config before the contract asserts and before `run_stage(config)`.

## 8. Tests (triad)

- `tests/contracts/test_stage05_config_contract.py`: scope + measure-only
  flags; run-id chain consistency with the Stage 04 / V2.1 configs; required
  output list closes with the runner constant; forbidden wording present;
  budget-ledger / claim / expectation blocks well-formed.
- `tests/stages/test_stage05_run_stage_smoke.py`: fail-closed entry gates
  (missing artifact, run-id chain mismatch, Stage 04 nonzero events, V2.1
  incomplete, forbidden wording in a claim, missing expectation field), and a
  happy path that asserts the four artifacts, the budget-ledger totals resolved
  from the frozen records, the estimand surface, and that no forbidden string
  appears in any output — all on a tiny synthetic frozen chain.
- `tests/notebooks/test_stage05_notebook_static.py`: bootstrap pin, run-id
  constants, runtime injection before asserts, durable-save refusals, forbidden
  patterns absent, guardrail markdown present.

## 9. Risks

| Risk | Protection |
|---|---|
| Hand-typed synthesis number drifts from the artifact | every measured value resolves from a frozen record field, fail-closed (§7) |
| Wording drift / overclaim | forbidden-wording gate over every statement + the report (§S5.5); `no_final_model_selected=true` carried into every output |
| Reading a stale / wrong upstream run | run-id chain gate (§2); `require_artifacts` inventory hash check |
| Mixing evidence domains | every row tagged with one of three domains (§3); register rejects unknown domains |
| Silent omission of the heavier analyses | `deferred_synthesis_items` names every still-deferred analysis explicitly in the report (B6/B7/B8 now built; the row-pooled raw-dump LOO remains listed) |
| Equating equal-weight LOO with the binding row-pooled estimand | B8 LOO is labeled `equal_weight_over_*`; the row-pooled LOO is a `<deferred>` marker row (macro-F1 non-linear across rows → needs raw `v2_1_predictions.csv`) |

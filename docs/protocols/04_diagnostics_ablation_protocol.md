# 04 Diagnostics Ablation Protocol

Status: pre-registration core, frozen 2026-06-09; operational detail will be
completed in Batch C without changing this section.

Scope: V2 `lst_models` route only. This document freezes the Stage 04
diagnostics and ablation decision rules (roadmap decision D3) before the Stage
03 official-validation readout executes. Stage 04 is diagnosis, not selection.
Stage 04 may not begin until `03_decision_record.json` is frozen; it runs
regardless of the Stage 03 outcome.

Decision provenance: D3 was frozen as the recommended default. Sign-off quoted
from `docs/lst_models_v2_route_roadmap.md` Phase 2:

> SIGN-OFF RECORD: user approved all four recommended defaults ("按推荐"),
> 2026-06-09. The choices below are frozen inputs for Batch B; changing any of
> them after the Stage 03 readout executes is forbidden.

Section freeze map: sections 2-8 are the frozen D3 core and are unchangeable
after the Stage 03 readout executes. Sections 9-10 name the operational
surface that Batch C completes without weakening sections 2-8.

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
  target_path: docs/protocols/04_diagnostics_ablation_protocol.md
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: not applicable; pre-registration protocol text only
  why_not_utils: not applicable; pre-registration protocol text only
  safety_tests: not applicable at core freeze; Batch C adds the Stage 04 test triad
```

Implementation must preserve:

- Colab-first execution; one user-facing Stage 04 notebook; one
  `run_stage(config)` entry point when executable logic is used.
- Validation-only scope: no holdout/test read, transform, window, score, or
  summary; no rows at or after `2017-01-25`; zero new official-validation
  fit-predict events (frozen D3, §2).
- Train-only preprocessing and same-row dummy baselines for every train-inner
  ablation fit where model metrics are reported.
- Manifest fields in §7; durable Drive result save; checkpoint plan for
  long-running ablation fits per AGENTS.md §5.

## 2. Stage Role And Input Boundary (frozen D3)

Stage 04 reads frozen Stage 03 artifacts only:

- `03_validation_predictions.csv` (per-row prediction dump)
- the `03_*` readout tables (`03_validation_readout.csv`,
  `03_per_ticker_readout.csv`, `03_seed_summary.csv`,
  `03_same_row_baselines.csv`)
- `03_decision_record.json`

New official-validation fit-predict events = 0. Stage 04 must not refit,
re-predict, re-threshold, recalibrate, or re-score any model on official
validation rows. The roadmap D3 alternative (a bounded validation-scored
ablation budget) was NOT chosen and may not be added after the readout.

## 3. Ablation Scoring Path (frozen D3)

Architectural-control ablations (`dlinear_only`, `tcn_only`, `last_step_mlp`,
`last_step_lightgbm_control`) are new fits — the four controls Stage 02
protocol §7 lists as "tracked architectural controls for future
implementation". They are fit and scored on Stage 02 train-inner folds ONLY,
under the same fold design, eligible-row, and same-row-baseline contracts
Stage 02 used (Stage 02 protocol §9, §10), with zero official-validation
contact. Ablation outcomes are diagnostic context only; they may not promote
a control to a thesis candidate or demote the frozen Stage 03 candidate.

## 4. Calibration — Measure-Only (frozen D3)

- Reliability bins, Brier score, and ECE are computed on the frozen
  `03_validation_predictions.csv` dump. Method anchor: Guo et al. 2017, "On
  Calibration of Modern Neural Networks", ICML (arXiv:1706.04599).
- NO calibrator fitting on official validation (no Platt, isotonic,
  temperature scaling, or any other fitted mapping).
- A calibrated model would require a new pre-registered protocol revision
  with a calibration set carved from the train tail; that revision is a V2.1
  item, not a Stage 04 action.

## 5. Selective / No-Trade Diagnostics (frozen D3)

- Full risk-coverage curves and AURC computed from the frozen prediction
  dump. Anchors: Geifman & El-Yaniv 2017 (arXiv:1705.08500); AURC per
  Geifman et al. 2019 (arXiv:1805.08206).
- Report whole curves. Never mark, recommend, or operationally select an
  operating point; `chosen threshold` is a forbidden string in Stage 04
  outputs, notebooks, and prose.

## 6. Robustness Slices And Failure Analysis (frozen D3)

- Per-ticker, per-seed, and per-period concentration of the pooled deltas is
  computed from the frozen dump only; flag when the pooled result is carried
  by a single ticker, seed, or period.
- Failure analysis (error concentration by ticker, time-of-day, trading day,
  volatility state) comes from the frozen dump only.
- No new validation scoring may be used to refine any slice.

## 7. Hard Boundary And Manifest Contract (frozen D3)

Stage 04 cannot change the Stage 03 outcome. Findings become limitation text
or pre-registered V2.1 items; they never reopen Stage 02/03 selection. The
Stage 04 run manifest must record:

```text
official_validation_contact=read_frozen_artifacts_only
new_validation_fit_predict_events=0
holdout_test_contact=false
```

## 8. Wording Rules (frozen)

Stage 04 inherits the Stage 03 forbidden list. Forbidden strings:
`final model`, `official validation winner`, `holdout winner`, `test winner`,
`proved best model`, `generalization proven`, `profitable`, `holdout-ready`,
`selected by official validation`, `chosen threshold`.

Allowed wording: `validation-only evidence`, `official validation readout`,
`candidate met/did not meet predeclared validation-readout criteria`.

## 9. Operational Detail (to be completed in Batch C)

Batch C completes the following without changing sections 2-8:

- Exact Stage 04 artifact names, schemas, and run-folder layout.
- `configs/stages/04_diagnostics_ablation.yaml`.
- `src/lst_models/stages/diagnostics_ablation.py` (`run_stage`).
- `notebooks/04_diagnostics_ablation_colab.ipynb`.
- Test triad: config contract, run-stage smoke, notebook static gate.
- Ablation builder references, checkpoint cadence, and Drive-save details.

## 10. Pre-Registered Scope And Risks

- Risk: diagnostics silently become reselection. Protection: §2 zero-event
  rule, §7 hard boundary and manifest fields, §8 forbidden strings.
- Risk: a calibrator or operating threshold is fitted on official validation.
  Protection: §4/§5 measure-only rules, frozen before the readout.
- Risk: ablation fits leak official-validation signal. Protection: §3
  train-inner-only path under Stage 02 fold/row/baseline contracts.
- Risk: post-readout edits to this core. Protection: the section freeze map;
  changes after the readout are forbidden and visible in git history.

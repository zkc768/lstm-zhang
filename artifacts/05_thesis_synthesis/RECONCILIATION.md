# Stage 05 evidence reconciliation (run 20260619_090454_562658 + standalone addenda)

This note reconciles the FROZEN Stage 05 synthesis run with the later measure-only
addenda WITHOUT editing any frozen run artifact (hand-editing a run output would
falsify the record). The run dir is a faithful snapshot of run
`20260619_090454_562658`; the addenda are separate, sha256-provenanced,
measure-only re-aggregations that close items the run had marked deferred.

## Deferred item -> closed (review finding F2)

`05_thesis_synthesis_report.json:deferred_synthesis_items` and the `<deferred>`
row in `05_loo_robustness.csv` list the row-pooled leave-one-out as deferred (the
run reads only small per-period/per-ticker aggregates, and macro-F1 is non-linear
across rows, so the row-pooled LOO needs the raw dump). It is now CLOSED:

| deferred in run 090454 | closed by | result |
|---|---|---|
| row-pooled LOO of the binding guarded estimand | `artifacts/05_row_pooled_loo/` | baseline reproduces 0.006362; `loo_sign_flip=False` for both the 7-period and 5-ticker sweeps |

Reading the run's `deferred` markers in isolation is therefore STALE; the binding
row-pooled LOO is closed by the standalone addendum (own manifest + SHA256SUMS).

## Standalone measure-only addenda over the frozen V2.1 dumps

All re-aggregate the frozen V2.1 prediction dumps (V2.1 run
`20260618_063559_889276`; input sha256 `6481f79…` / `cd6925e…`, verified against
that run's `artifact_inventory`). Each packet carries its own manifest
(code + input sha256) + README + `SHA256SUMS.txt` (`sha256sum -c` OK):

| packet | closes (review item) | headline |
|---|---|---|
| `05_row_pooled_loo/` | binding-estimand LOO (deferred above) | sign survives every single-period / single-ticker drop |
| `05_row_pooled_multiplicity/` | #2 multiplicity on the BINDING row-pooled estimand | only TCN-primary period-LCB > 0; PBO 0.514; TCN central reproduces 0.006362 |
| `05_guarded_activity_tercile/` | #1 conditional map on the guarded era (cross-era) | low +4.08pp / mid +0.56pp / high -2.10pp (high macro-F1 0.480 < 0.5) |
| `05_guarded_base_rates/` | #5 per-period regime + per-tercile class balance | only wf_p4 (COVID) / wf_p6 (bear) periods negative; dummy floor near-constant across terciles |
| `05_label_shuffle_sentinel/` | E within-day leakage / artifact negative control | all terciles: observed clears the within-day shuffle null (high stays -0.021 = below random, above its more-negative null) |

## Manifest-universe scopes (review finding F5b) — by design, not falsification

The three manifests in the run dir cover DIFFERENT scopes because of write order:

- `run_manifest.json:output_artifacts` (10): `run_manifest` + `artifact_inventory` + the 8 synthesis outputs.
- `artifact_inventory.csv` (9): the 8 synthesis outputs + `run_manifest` (written before the Drive backup, so it predates `drive_backup_manifest`).
- `SHA256SUMS.txt` (11, mirror packet): the 8 synthesis outputs + `artifact_inventory` + `run_manifest` + `drive_backup_manifest` (excludes `README.md` and itself).

None is falsified; each is a consistent record of its own scope. Future-run
hardening (in `artifacts.py` / the mirror step) should include
`drive_backup_manifest` in the inventory and `README.md` in `SHA256SUMS` so the
universes coincide.

## Other known, non-falsified gaps

- `drive_backup_manifest.json` self-entry carries no Drive file id: it is uploaded
  last and cannot know its own id at write time (AGENTS.md already allows its
  self-size to be null). Fix belongs in the upload code for future runs (F5c).
- `v2_1_baseline_predictions.csv` is produced by the V2.1 run
  (`guarded_walkforward.py`) and consumed by the addenda above; it is now declared
  in `configs/stages/v2_1_guarded_walkforward_readout.yaml:outputs` (F5a).

## Authority

The live reconciliation layer is the claims ledger `paper/outline_and_claims.md`
(v1.10, gitignored / local-only). This file is its in-tree, evidence-side mirror
so a reader of the committed artifacts can trace deferred -> closed without the
ledger.

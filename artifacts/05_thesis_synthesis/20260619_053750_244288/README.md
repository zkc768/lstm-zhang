# Stage 05 thesis-synthesis evidence packet — run `20260619_053750_244288`

Deliberate **in-repo mirror** of the Stage 05 (thesis synthesis) run outputs so
the paper's numbers are independently checkable inside the repository. Google
Drive remains the canonical store; this packet is the small, paper-facing
synthesis OUTPUTS only (force-tracked past `.gitignore: artifacts/**`). The large
row-level prediction dumps (`03_validation_predictions.csv` ~44 MB,
`v2_1_predictions.csv`) are NOT mirrored — they stay Drive-only per route guide
§11; this packet is the aggregated synthesis tables + manifests.

## Provenance
- stage_run_id: `20260619_053750_244288`
- git_commit (code that produced it): `96e91ab013c5669322ad59d556e671cbb3191229`
- scope: `synthesis_measure_only` · `new_scoring_events=0` ·
  `holdout_test_contact=false` · `no_final_model_selected=true`
- Drive: `My Drive/lst_models/results/05_thesis_synthesis/20260619_053750_244288/`
  (folder id `1qzJ52yhOiSG1mR2xyNSA2vAOncypM4O5`)
- Frozen upstream inputs (read-only):
  - Stage 03 official-validation readout: `20260610_133305_716174`
  - Stage 04 diagnostics (sentinel run): `20260618_234011_838683`
  - V2.1 guarded walk-forward readout: `20260618_063559_889276`
    (this run sequenced after an earlier Stage 04 `20260610_232623_326133`;
    both chain to the same Stage 03 — recorded in the report as
    `v2_1_source_stage04_run_id`, not gated for equality)

## Files (9)
| file | what it is |
|---|---|
| `05_validation_budget_ledger.csv` | S5.1 route scoring-event budget (2 + 0 + 56 = 58) |
| `05_claim_boundary_register.csv` | S5.2 paper-safe claims tagged by evidence domain |
| `05_expectation_calibration.csv` | S5.3 measured deltas vs published direction-accuracy band |
| `05_multiplicity_discount.csv` | B6 descriptive CSCV PBO + per-family `min_family_lcb` |
| `05_selective_autopsy.csv` | B7 AURC/e-AURC/AUGRC + abstention × activity tercile + MDE |
| `05_thesis_synthesis_report.json` | run summary (decisions, estimands, B6/B7 summaries, guardrails) |
| `run_manifest.json` | scope/safety flags, source run ids, code/config/notebook sha256 |
| `artifact_inventory.csv` | per-file bytes + sha256 (Stage 05's own inventory) |
| `drive_backup_manifest.json` | Drive upload manifest (folder id, file ids, sizes) |

## Verify
```bash
sha256sum -c SHA256SUMS.txt
```

## Reading discipline (do not overclaim)
- Descriptive diagnostics only. PBO / `min_family_lcb` are overfitting/uncertainty
  discounts, never a significance test. Selective metrics (AURC/e-AURC/AUGRC) are
  accuracy-based with no cost/return — a diagnostic, never an operating point or a
  tradeability claim. `no_final_model_selected=true`.
- Per-tercile MDE is intentionally absent: the frozen Stage 04 bootstraps the
  seed/ticker axes only, so per-activity-tercile MDE needs B4 (activity-tercile
  bootstrap). The pooled MDE and the per-tercile delta + accuracy are present.
- The low-activity (calm-bar) edge is a conditional-signal **limitation**, not an
  innovation; "activity" is a per-day eligible-row-count proxy, not volume/liquidity.

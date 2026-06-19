# Stage 05 thesis-synthesis evidence packet — run `20260619_090454_562658`

Deliberate **in-repo mirror** of the Stage 05 (thesis synthesis) run outputs so
the paper's numbers are independently checkable inside the repository. Google
Drive remains the canonical store; this packet is the small, paper-facing
synthesis OUTPUTS only (force-tracked past `.gitignore: artifacts/**`). The large
row-level prediction dumps Stage 05 READS (`03_validation_predictions.csv` ~44 MB,
`v2_1_predictions.csv` ~543 MB) are NOT mirrored — they stay Drive-only per route
guide §11; this packet is the aggregated synthesis tables + manifests.

**Supersedes `20260619_071800_720100`.** This run reads the **B4 Stage 04 run**
(`20260619_082125_765984`, which adds the per-activity-tercile block-bootstrap),
so the selective autopsy's **per-tercile MDE is now populated** — closing the
C3.4 `delta_clears_mde=null` gap. All other surfaces (B6 multiplicity, B8
estimand contrast + equal-weight LOO) are byte-identical to the superseded
mirror; the budget ledger + claim register differ only in the Stage 04 `run_id`
reference (now the B4 run). The earlier mirror was removed in the same commit
(git history preserves it).

## Provenance
- stage_run_id: `20260619_090454_562658`
- git_commit (code that produced it): `e2bfba4d3f41cac12d006d42992e60eacf18c37a`
- scope: `synthesis_measure_only` · `new_scoring_events=0` ·
  `holdout_test_contact=false` · `no_final_model_selected=true`
- The manifest's `stage05_synthesis_code_sha256` matches what the repo computes at
  that commit: the run was produced by exactly that code.
- Drive: `My Drive/lst_models/results/05_thesis_synthesis/20260619_090454_562658/`
  (folder id `1-M0Nh3Fzmg-6DzEc76ufoodvvJ1n50nk`)
- Frozen upstream inputs (read-only):
  - Stage 03 official-validation readout: `20260610_133305_716174`
  - **Stage 04 diagnostics (B4 run, per-tercile bootstrap): `20260619_082125_765984`**
    (its sentinel is byte-identical to the prior Stage 04 run; the torch ablation
    controls differ ~0.01pp from GPU non-determinism, but Stage 05 does not read
    `04_ablation_summary`)
  - V2.1 guarded walk-forward readout: `20260618_063559_889276`
    (this run sequenced after an earlier Stage 04 `20260610_232623_326133`; all
    chain to the same Stage 03 — the runtime gate binds only that shared Stage 03)

## Files (11)
| file | what it is |
|---|---|
| `05_validation_budget_ledger.csv` | S5.1 route scoring-event budget (2 + 0 + 56 = 58) |
| `05_claim_boundary_register.csv` | S5.2 paper-safe claims tagged by evidence domain |
| `05_expectation_calibration.csv` | S5.3 measured deltas vs published direction-accuracy band |
| `05_multiplicity_discount.csv` | B6 descriptive CSCV PBO + per-family `min_family_lcb` |
| `05_selective_autopsy.csv` | B7 AURC/e-AURC/AUGRC + abstention × tercile + **per-tercile MDE (B4-closed)** |
| `05_estimand_contrast.csv` | B8 2×2 {domain}×{aggregation} headline delta surface |
| `05_loo_robustness.csv` | B8 equal-weight LOO-period + LOO-ticker (row-pooled LOO deferred) |
| `05_thesis_synthesis_report.json` | run summary (decisions, estimands, B6/B7/B8 summaries, guardrails) |
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
- **Per-tercile MDE (B4)**: `mde_vs_dummy = delta − bootstrap_lcb`, with the
  bootstrap LCB now extracted from the B4 Stage 04 per-activity-tercile block
  bootstrap. `delta_clears_mde` ⟺ tercile bootstrap LCB > 0: **low True (LCB
  +4.59pp), mid True (LCB +1.10pp), high False** (its whole CI is below 0 → the
  high-activity tercile is *robustly below random*, not noise). The bootstrap CI
  is a descriptive uncertainty band, not a significance test.
- **B8 estimand contrast / LOO**: the equal-weight unit differs by domain (period
  vs tercile) → compare each only to its own row-pooled. The equal-weight LOO is a
  robustness proxy; the binding row-pooled LOO is deferred (needs the raw dump).
- The low-activity (calm-bar) edge is a conditional-signal **limitation**, not an
  innovation; "activity" is a per-day eligible-row-count proxy, not volume/liquidity.

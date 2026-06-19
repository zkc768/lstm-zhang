# Stage 05 thesis-synthesis evidence packet — run `20260619_071800_720100`

Deliberate **in-repo mirror** of the Stage 05 (thesis synthesis) run outputs so
the paper's numbers are independently checkable inside the repository. Google
Drive remains the canonical store; this packet is the small, paper-facing
synthesis OUTPUTS only (force-tracked past `.gitignore: artifacts/**`). Stage 05
emits only aggregated synthesis tables + manifests, so every output is small —
the large row-level prediction dumps it READS (`03_validation_predictions.csv`
~44 MB, `v2_1_predictions.csv` ~543 MB) are NOT part of this packet; they stay
Drive-only per route guide §11.

**Supersedes `20260619_053750_244288`.** This run is a clean superset of that
earlier mirror: the five shared B5/B6/B7 outputs are byte-identical (same code
path, same frozen inputs), and this run additionally emits the two B8 artifacts.
Produced by a later code commit (`7198df1`, which adds B8) — the earlier mirror
was removed in the same commit (git history still preserves it).

## Provenance
- stage_run_id: `20260619_071800_720100`
- git_commit (code that produced it): `7198df12d76ab339eb5c6531cd2e8f1486a55ab1`
- scope: `synthesis_measure_only` · `new_scoring_events=0` ·
  `holdout_test_contact=false` · `no_final_model_selected=true`
- The manifest's `stage05_synthesis_code_sha256` matches what the repo computes
  at commit `7198df1` (`3bb2abe…`): the run was produced by exactly that code.
- Drive: `My Drive/lst_models/results/05_thesis_synthesis/20260619_071800_720100/`
  (folder id `1xWgpO4ML_ukAuRldb5jBye3CNcOKIAzu`)
- Frozen upstream inputs (read-only):
  - Stage 03 official-validation readout: `20260610_133305_716174`
  - Stage 04 diagnostics (sentinel run): `20260618_234011_838683`
  - V2.1 guarded walk-forward readout: `20260618_063559_889276`
    (this run sequenced after an earlier Stage 04 `20260610_232623_326133`;
    both chain to the same Stage 03 — recorded in the report as
    `v2_1_source_stage04_run_id`, not gated for equality)

## Files (11)
| file | what it is |
|---|---|
| `05_validation_budget_ledger.csv` | S5.1 route scoring-event budget (2 + 0 + 56 = 58) |
| `05_claim_boundary_register.csv` | S5.2 paper-safe claims tagged by evidence domain |
| `05_expectation_calibration.csv` | S5.3 measured deltas vs published direction-accuracy band |
| `05_multiplicity_discount.csv` | B6 descriptive CSCV PBO + per-family `min_family_lcb` |
| `05_selective_autopsy.csv` | B7 AURC/e-AURC/AUGRC + abstention × activity tercile + MDE |
| `05_estimand_contrast.csv` | **B8** 2×2 {domain}×{aggregation} headline delta surface |
| `05_loo_robustness.csv` | **B8** equal-weight LOO-period + LOO-ticker (row-pooled LOO deferred) |
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
- **B8 four-estimand contrast** (`05_estimand_contrast.csv`): the headline macro-F1
  delta under both aggregation choices in both reportable evidence domains. The
  equal-weight unit DIFFERS by domain — guarded = walk-forward period, validation =
  activity tercile — so each column compares only to its OWN row-pooled, never
  cross-domain. No estimand is "the" result.
- **B8 LOO** (`05_loo_robustness.csv`): EQUAL-WEIGHT leave-one-out is descriptive
  robustness, not a significance test. The BINDING estimand is row-pooled, and
  macro-F1 is non-linear across rows, so the true row-pooled LOO needs the raw
  `v2_1_predictions.csv` (Drive-only) — it is a `<deferred>` marker row here, never
  silently equated with the equal-weight LOO. Both equal-weight sweeps survive every
  single-unit drop (`loo_sign_flip=False`); this is robustness of the equal-weight
  companion, not of the binding row-pooled estimand.
- Per-tercile MDE is intentionally absent: the frozen Stage 04 bootstraps the
  seed/ticker axes only, so per-activity-tercile MDE needs B4 (activity-tercile
  bootstrap). The pooled MDE and the per-tercile delta + accuracy are present.
- The low-activity (calm-bar) edge is a conditional-signal **limitation**, not an
  innovation; "activity" is a per-day eligible-row-count proxy, not volume/liquidity.

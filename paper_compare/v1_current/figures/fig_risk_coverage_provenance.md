# fig_risk_coverage provenance

- generated_at_utc: 2026-06-22T09:01:32.601890+00:00
- mode: regenerated_from_validation_prediction_dump
- claim_id: C3.2
- evidence_domain: official_validation
- estimand: accuracy_based_selective_risk_coverage
- forbidden_framing_checked: descriptive only; no cost model; no operating point; not well-calibrated; no statistical significance claim

## Inputs
- dump: G:\我的云端硬盘\lst_models\results\03_frozen_validation_readout\20260610_133305_716174\03_validation_predictions.csv sha256=62aeb0c92c9ad5c25a313e533e10d93d254639ef0d01fef19e824316ead782c5
- scalar_summary_gate: artifacts\ian_email_packet_20260611\tables\09_validation_selective_summary.csv sha256=9a762cb434f4a8413544c33b82d7283ff85ba6036ace1378c92c25968459c912
- figure_source_csv: paper\figures\fig_risk_coverage_source.csv sha256=61d5cb6d0c5779a92c89b14eb1a0e60bec99ff3379e27ff291af9fb4d5957eb3
- figure_scalar_summary_csv: paper\figures\fig_risk_coverage_scalar_summary.csv sha256=b90df62a2f1fad672a2e2d487ac3405cfc9e7bf4997686c430cc64cd06b45568
- seeds: [101, 202]
- rows_per_seed: {101: 151064, 202: 151064}
- score_order: descending top-label probability; ties broken by stable sample_id order
- aurc_calculation: full per-row ranked sequence; display markers are downsampled only
- band_min_coverage: 0.05
- coverage_zero: not included in AURC or displayed bands; selective risk starts at coverage 1/n
- bootstrap_reps: 1000; trading-day cluster (block) bootstrap, whole days resampled with replacement, shared across seeds; rng_seed=314159
- bootstrap_unit: trading_day cluster (block); 846 unique days per seed
- permutation_reps: 1000; random row ordering null; rng_seed=314160
- random_reference: expected risk under random ranking equals full-coverage risk
- descriptive_random_to_score_aurc_delta: -0.010104  95ci=[-0.013674, -0.006315]
- rel_aurc_random_to_oracle_scale: 0.970310  95ci=[0.959697, 0.981500]
- random_to_oracle_gap_closed: 0.029690  95ci=[0.018500, 0.040303]
- partial_aurc_score_high_coverage_bands: 80-100%=0.478337, 90-100%=0.479461, 95-100%=0.480136
- partial_delta_vs_random_pp: 80-100%=0.2482, 90-100%=0.1359, 95-100%=0.0684
- full_coverage_errors_per_seed: 101=72620, 202=72649
- n_covered_at_min_band: 7553 rows at coverage 0.05
- augrc_caption_only: 0.236872; computed from generalized-risk curve, not plotted selective-risk area
- reconciliation_tolerance: 5e-4 unless --no-reconcile

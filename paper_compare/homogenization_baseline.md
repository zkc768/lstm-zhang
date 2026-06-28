# Homogenization log (GPT-2 per-sentence perplexity + burstiness)

Pass-over-pass log (not a single snapshot — see `docs/adr/0001-burstiness-diagnostic-not-autorevert.md`).
Re-run `paper_compare/perplexity_burstiness.py` after each whole-paper pass and ADD a column.
Compare each pass to the **immediately preceding** column, not only to the first.

**Rule (ADR 0001):** a DROP in `mean_perplexity` or `burstiness_sd` is a **flag to investigate,
not an auto-revert**. A drop attributable to a gate-mandated edit (a >35-word sentence split, a
red-line rewrite) is *expected* — log it and move on. Only an **unexplained** drop is treated as
possible homogenization. The HARD >35-word rule always wins a direct conflict with the burstiness
warning. NB: absolute values are inflated by technical terms/numbers, so the heuristic flags
(mean<30, sd<12) never fire on academic prose — the DELTA is the signal.

## mean_perplexity

| Section | pre–Pass-A (2026-06-28) | post–Pass-A (2026-06-28) | Δ | note |
|---|---|---|---|---|
| 01_intro | 381.4 | 390.6 | +2.4% | §1 stable (already looped) |
| 02_related | 583.2 | 563.3 | −3.4% | within noise |
| 03_protocol | 452.2 | 450.4 | −0.4% | stable |
| 04_models | 284.7 | 287.4 | +0.9% | stable |
| 05_setup | 376.6 | 345.2 | −8.3% | EXPECTED — Pass A split long sentences |
| 06_results | 393.1 | 393.1 | 0 | unchanged |
| 07_guarded_walkforward | 488.3 | 486.2 | −0.4% | §7 stable (already looped) |
| 08_diagnostics | 360.6 | 362.6 | +0.6% | stable |
| 09_limitations_conclusion | 660.4 | 607.1 | −8.1% | EXPLAINED (Pass C): Pass-B calibration-reconciliation content fix replaced a high-perplexity sentence; n=25 unchanged; still the most-bursty section — not homogenization |

## burstiness_sd

| Section | pre–Pass-A | post–Pass-A | Δ | note |
|---|---|---|---|---|
| 01_intro | 272.0 | 274.0 | +0.7% | stable |
| 02_related | 440.9 | 450.0 | +2.1% | up (good) |
| 03_protocol | 343.7 | 341.6 | −0.6% | stable |
| 04_models | 170.7 | 154.8 | −9.3% | EXPECTED — Pass A sentence splits |
| 05_setup | 309.8 | 256.0 | −17.4% | EXPECTED — Pass A sentence splits (largest) |
| 06_results | 341.8 | 341.8 | 0 | unchanged |
| 07_guarded_walkforward | 707.7 | 708.4 | +0.1% | stable |
| 08_diagnostics | 374.8 | 342.3 | −8.7% | EXPECTED — Pass A sentence splits |
| 09_limitations_conclusion | 995.1 | 966.8 | −2.8% | minor; pairs with the §9 mean flag |

**Read:** every section still sits at very high perplexity (287–607) and very high burstiness
(155–967) — nowhere near the AI-uniform thresholds. The four material drops (§4, §5, §8 burstiness;
§5, §9 mean) are all in Pass-A sections **except §9**, which was not a Pass-A target and is the one
genuine "investigate" flag. This is the diagnostic rule (ADR 0001) working as intended: mandated
splits are logged as expected; the unexplained §9 movement is surfaced for a look during Pass B.
Pass B/C must ADD their own columns and compare to *post–Pass-A*, not to pre–Pass-A.

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

## R2 presentation pass (2026-06-28) — abstract/intro/conclusion + WI-4 hedge-variety + WI-5 caption + Pass-B/C

Compared to the **post-Pass-A** column above (the immediately-preceding whole-paper snapshot, per
ADR 0001). Only R2-edited sections were re-measured. The abstract lives in `main.tex` (preamble
noise), so it is tracked here by `check_integrity` sentence-length sd, not GPT-2. Unchanged sections
(02/03/04/05/08) carry their post-Pass-A values.

### mean_perplexity (GPT-2, post Pass-C)

| Section | post-Pass-A | R2 (post Pass-C) | delta | note |
|---|---|---|---|---|
| 01_intro | 390.6 | 458.3 | +17.3% | INCREASE (good) - WI-4 variety + Pass-A split raised specificity |
| 06_results | 393.1 | 394.5 | +0.4% | stable - WI-5 trimmed one caption clause (caption is stripped) |
| 07_guarded_walkforward | 486.2 | 492.0 | +1.2% | stable/up - WI-4 + Pass-C de-echo |
| 09_limitations_conclusion | 607.1 | 616.9 | +1.6% | up - Pass-B both-window sentence + Pass-C reword |

### burstiness_sd (GPT-2, post Pass-C)

| Section | post-Pass-A | R2 (post Pass-C) | delta | note |
|---|---|---|---|---|
| 01_intro | 274.0 | 532.2 | +94% | large INCREASE (good) - variety + split de-homogenized section 1 |
| 06_results | 341.8 | 340.9 | -0.3% | within noise (WI-5 caption-only) |
| 07_guarded_walkforward | 708.4 | 717.2 | +1.2% | up - stays 2nd-most-bursty section |
| 09_limitations_conclusion | 966.8 | 913.4 | -5.5% | EXPLAINED (ADR 0001): Pass-B added a short 8-word both-window sentence + Pass-A grammar simplification; n=28; section 9 REMAINS the most-bursty section (sd 913) - not homogenization, NOT reverted (gate/foregrounding-mandated). |

**abstract (main.tex):** `check_integrity` sentence-length sd 5.9 (pre) -> 5.7 (post-R2). The drop is the
Pass-A >35-word split of the 41/49-word guarded sentence (HARD gate) - EXPECTED per ADR 0001 (the
HARD rule wins a direct conflict with the burstiness warning); not reverted. Abstract prose gate PASS.

**Humanizer meta-audit (Pass C):** an independent writing-reviewer with the humanizer tell-list found
R2 introduced ZERO new sentence-level AI-tell (active voice, concrete glosses, zero AI-vocabulary,
zero em-dashes; the splits improved rhythm). The only residual was cross-file PHRASE recurrence
(craft, not AI-writing): "sets the scale" (3x), the holds/persists/inverts couplet (3 paraphrases),
a section-7 header/body small-but/yet-stable self-echo, and a 3rd "recurs in the guarded window". The
four in/near the R2 edits were de-echoed in Pass C (01:38 sets->fixes, scale->size; 01:63
inverts->reverses; 07:65 lead-with-evidence; 09:21 reworded). Required deflationary hedges
(thin/small/weak/near-/descriptive/not-a-clean-test) are governance vocabulary and were left untouched.

**Read:** every R2 section stays at very high perplexity (394-617) and very high burstiness (341-913)
- nowhere near AI-uniform. Net direction is UP (section 1 strongly so): R2 de-homogenized rather than
homogenized. The single sd drop (section 9) is explained by a gate/foregrounding-mandated edit and
section 9 remains the most-bursty section. Per ADR 0001: logged as expected, nothing reverted.

## R2 / WI-7 §2-§8 readability pass (2026-06-28)

Presentation-only readability refinement of §3/§7/§8 (advisor: dense later sections more concise/
readable). Compared to the **post-Pass-A** column for these sections (their immediately-preceding
whole-paper snapshot; WI-7 did not touch them in Phase 1). NO number/claim changed. Triage left
§2/§4 untouched (compact) and §5/§6 as-is (no clear-win defect).

### mean_perplexity (GPT-2, post WI-7 Pass-C)

| Section | post-Pass-A | WI-7 | delta | note |
|---|---|---|---|---|
| 03_protocol | 450.4 | 593.3 | +32% | INCREASE (good) - de-stacking + sentence splits de-homogenized §3 |
| 07_guarded_walkforward | 486.2 | 391.9 | -19% | EXPLAINED - readability/gate splits (38-word definition + dense estimand/multiplicity dumps) |
| 08_diagnostics | 362.6 | 384.2 | +6% | stable/up - AUGRC regroup + 2 splits + filler removal |

### burstiness_sd (GPT-2, post WI-7 Pass-C)

| Section | post-Pass-A | WI-7 | delta | note |
|---|---|---|---|---|
| 03_protocol | 341.6 | 940.7 | +176% | large INCREASE (good) - §3 now among the most-bursty sections |
| 07_guarded_walkforward | 708.4 | 239.3 | -66% | EXPLAINED (ADR 0001): the pass split §7's long dense sentences (the gate-mandated 38-word what-it-is definition + the estimand/multiplicity number-dumps the advisor flagged). Lower variance is the INTENDED readability gain, NOT homogenization; sd 239 is still far from AI-uniform. NOT reverted (readability + HARD-gate edits win per ADR 0001). |
| 08_diagnostics | 342.3 | 342.6 | ~0 | flat - AUGRC move + splits net-neutral |

**Pass B (post-WI-7):** consistency-checker + logic-reviewer whole-paper -> ZERO cross-section
inconsistency, ZERO logic break, ZERO domain fusion, ZERO dropped caveat. AUGRC relocation clean (no
orphaned ref/cite; Fig 3 / Table 3 unaffected). Two P2 notes (§7 0.514 PBO/LOO numeric coincidence;
§8 header<->body 2-out/1-not tally) are PRE-EXISTING, not WI-7 regressions.

**Humanizer meta-audit (WI-7 Pass C):** the splits read more human / less dense; no choppy uniform-short
rhythm introduced (one mild AUGRC staccato re-lengthens immediately); the §8 filler removal ("invites
the question of whether" -> "could be spurious") is a clear gain. Two governance-safe tells fixed:
§7 doubled "X, not Y" antithesis (recast first clause positive: "...adaptation that departs from the
canonical symmetric form"); §3 "-ing" participial trailer (restored finite verb: "...separate and
reports each number only within its own domain"). The residual recurring "X, not Y / X rather than Y"
mold across the paper is REQUIRED deflationary hedging vocabulary (each instance load-bearing) - left intact.

**Read:** §3 strongly UP (de-homogenized), §8 flat, §7 DOWN but fully explained by the advisor-mandated
readability splits (the whole point of WI-7) plus one >35-word gate split; every section stays far from
AI-uniform (perplexity 384-593, sd 239-941). Per ADR 0001: §7's drop logged as expected, nothing reverted.

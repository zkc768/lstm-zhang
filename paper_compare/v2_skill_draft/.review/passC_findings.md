# Pass C (naturalness / anti-homogenization) — findings + decisions

Two signals: (1) mechanical anti-AI grep gates; (2) GPT-2 per-sentence perplexity+burstiness
vs `homogenization_baseline.md`; plus a writing-reviewer "what still sounds AI?" meta-audit
(humanizer's soul/first-person/de-hyphenation moves explicitly OFF per project governance).

## Mechanical grep gates (anti-AI guide §8) — CLEAN
- Gate 1 Tier-1 vocab: clean (via check_integrity, all sections pass).
- Gate 2 Tier-2 inflated verbs (leverage/utilize/showcase/...): clean.
- Gate 3 phrase blacklist: clean.
- Gate 4 commentary openers (Moreover/Furthermore/...): clean.
- Gate 5 -ing tails: 1 hit (`08:135`, a figure caption "indicating weak confidence ordering
  rather than a usable abstention rule") — contentful, not fake depth; left.
- Gate 6 Chinglish: clean.
- Gate 7 >35-word sentences: clean (all pass).
- Gate 8 red-line claims: clean (all negated/absent).
- em-dash in body: only `main.tex:112` "% --- Endmatter" (a comment divider; does not render).

## Perplexity/burstiness — FINAL vs baseline (DELTA is the signal; absolutes stay high = not AI)
| Sec | mean base->final | sd base->final | n | editor | read |
|---|---|---|---|---|---|
| 01 | 381.4->383.4 | 272.0->271.2 | 30=30 | me | flat (no homogenization) |
| 02 | 583.2->563.3 | 440.9->450.0 | 15->20 | other PassA | sd UP, fine |
| 03 | 452.2->450.4 | 343.7->341.6 | 38->42 | other PassA | flat |
| 04 | 284.7->281.4 | 170.7->165.8 | 14->15 | other PassA | flat |
| 05 | 376.6->345.2 | 309.8->256.0 | 12->14 | other PassA + me | DROP (see below) |
| 06 | 393.1->393.1 | 341.8->341.8 | 25=25 | me | identical |
| 07 | 488.3->486.5 | 707.7->708.8 | 34=34 | me | flat |
| 08 | 360.6->363.8 | 374.8->341.5 | 36->43 | other PassA | sd down, but reviewer: bursty/fine |
| 09 | 660.4->606.1 | 995.1->967.3 | 25=25 | me | DROP (see below); still MOST bursty section |

**All sections remain far above the AI-flag thresholds (mean<30 / sd<12).** Paper is NOT homogenized.

### The two drops, explained (neither is AI-homogenization)
- **§9 (mine):** the calibration-reconciliation content fix (Pass B I2) replaced the sentence
  "Feature and regime diagnostics then bound and interpret that margin." — a high-perplexity
  outlier — with a more conventional calibration clause. GPT-2 perplexity is deterministic and
  n is unchanged (25), so the drop is that single sentence. §9 still has the highest burstiness
  (967) and 2nd-highest mean (606) in the paper. Kept: correctness > chasing a proxy the script
  says is "NOT a target to optimize against."
- **§5 (other window's Pass A + me):** the other window's Pass A reduced §5 variety
  (309.8->266.8). I split its 33-word 7-item "binding" dump sentence into two clear sentences
  (a readability/naturalness win the reviewer flagged as the section's worst AI-tell). That
  removed a length outlier, so the proxy sd ticked down further (266.8->256.0) even though the
  prose is better. A second attempt (isolating the manifest code-literal as a short sentence)
  was REVERTED: it spiked the metric to 1905/5894 — a pure artifact of GPT-2 choking on
  `no_final_model_selected=true`, i.e. accidental metric-gaming, not real burstiness.

## Writing-reviewer meta-audit — honest bottom line
"Not broadly homogenized. §3/§6/§8 read like a careful human methods paper; vocab + copula gates
genuinely clean." Two findings:
1. **Negative-contrast ("X, not Y") saturation** (~40 instances). BUT most are governance-mandated
   red-line discipline ("not a clean test", "no final model", "classification evidence, not
   economic value") that MUST stay. Only ~12-15 discretionary instances could vary. Genre-
   appropriate for a deflationary paper; broad rewriting risks ironic homogenization + churn +
   conflict with the other window. **FLAGGED, not churned.**
2. **§5 uniform-rhythm run + 7-item dump** — the dump is FIXED (split); the residual medium-length
   run is left (further edits chase the proxy).

## APPLIED
- `05_setup.tex:47-50` split the 33-word 7-item "binding" dump into two sentences (readability;
  reviewer's top §5 fix). Content/terms/red-lines preserved verbatim. Gate PASS.
- (§9 calibration reword from Pass B retained; it is content, not style.)

## NOT APPLIED — flagged for user / Codex (avoid churn + homogenization on already-bursty prose)
- Broad negative-contrast syntactic variety (the ~12-15 discretionary instances; e.g. §2
  paragraph-final contrasts, §7 two contrastive \paragraph headings). Genre-appropriate; risky to
  mass-edit; the reviewer rated those sections "borderline", not homogenized.
- §1 closing list-then-list de-stacking (reviewer rated §1 "not homogenized").
- §5 residual medium-length run (further tinkering = proxy-gaming on a 14-sentence section).

Gate: all PASS. Compile: 8 pages, 0 undefined refs.

# Burstiness is a diagnostic signal, not an auto-revert trigger

**Status:** accepted (2026-06-28)

The Pass C anti-homogenization rule originally said "any pass that lowers `burstiness_sd`
is homogenizing → revert it." But `check_integrity.py` HARD-fails sentences >35 words,
which *forces* sentence splits, and splitting lowers sentence-length variance — so a
gate-mandated edit looks identical to homogenization under the old rule. The two rules
fought each other with no tiebreak, and the `homogenization_baseline.md` snapshot was
captured *before* Pass A edited §2/§3/§4/§5/§8, so every comparison against it was already
measuring drift from pre-fix text.

**Decision:** (1) Re-baseline after Pass A and keep `homogenization_baseline.md` as a
*pass-over-pass log* (one dated column per pass, old snapshots retained), not a single
snapshot. (2) A burstiness/perplexity drop is a **flag to investigate, not an automatic
revert**: a drop attributable to a gate-mandated edit (sentence split, red-line fix) is
logged as expected; only an *unexplained* drop is investigated as possible homogenization.
(3) Compare each pass to the *immediately preceding* pass (B vs post-A, C vs post-B), not
only to the original baseline, so legitimate one-time drops are not re-flagged every pass
and slow cumulative drift is still caught.

**Consequences:** The metric now relies on judgment (was this drop explained?) rather than
a hard threshold — acceptable because the project rule already forbids treating
perplexity/burstiness as a detector target. The HARD >35-word rule always wins a direct
conflict with the burstiness warning.

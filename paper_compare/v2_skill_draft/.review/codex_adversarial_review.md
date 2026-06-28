# Codex adversarial review (different model) — verdict + main-loop triage

Tool: `codex exec -s read-only` (GPT-class model, independent of the Claude author). Full red-line +
three-domain + Option-2 contract supplied. Full trace: scratchpad/codex_review_output.txt (451KB).

## Codex VERDICT: NO_GO  (4 P0, 5 P1, 1 P2)
Codex rationale: "Option-2 framing is mostly honest-deflationary, but it has crossed the line in
localized, fixable places." It confirmed NO affirmative red-line terms (best/outperforms/profitable/
well-calibrated/tradable/alpha/SOTA/superior) and that load-bearing numbers match the ledger.

Each finding was independently verified by the main loop against the live files + artifacts + ledger
BEFORE any action (per governance: agent outputs are not trusted blindly).

## APPLIED (verified factual/domain/caveat fixes — "safe direction"; no-fabrication override)
1. **[P0] 07:69 time-reversed sentinel = evidence-domain mix.** VERIFIED: the guarded sentinel
   artifact `artifacts/05_label_shuffle_sentinel/05_label_shuffle_sentinel.csv` is **label-shuffle
   ONLY (no time_reverse column)**; the time-reversed sentinel lives in the OFFICIAL_VALIDATION
   domain (`05_claim_boundary_register.csv` C2_sentinel_collapses -> 04_sentinel_summary.csv,
   stage04). §7 (guarded section) attributing "time-reversed sentinels" to the guarded readout mixes
   domains. FIX: "Within-day label-shuffle and time-reversed sentinels collapse" -> "A within-day
   label-shuffle sentinel collapses". (Codex's instinct right; its stated reason "not in ledger" was
   slightly off — the artifact exists, just in the wrong domain for §7.)
2. **[P0->P1] 01:33 bootstrap "excludes zero" w/o local caveat.** Added the red-line-required
   "descriptive": "The pooled margin's descriptive block-bootstrap interval excludes zero".
3. **[P1] 08:72 "stable across both windows".** CONVERGENT (Pass B technical-reviewer + Codex both
   flagged). "stable" overclaims a non-independent re-aggregation. FIX -> "the low-to-high pattern
   is same-signed in both windows" (Codex's "same-signed"; matches ledger C4.5 sanctioned
   recurrence; preceding sentence already states non-independence).

Gate after fixes: 01/07/08 PASS. Compile: 8 pages, 0 undefined refs.

## REJECTED (false positive — verified against artifact)
4. **[P0] 07:56 LightGBM "+0.726pp unsupported precision".** Codex saw only the ledger PROSE
   (+0.70pp, the equal-weight rounding). The paper uses the BINDING ROW-POOLED estimand:
   `artifacts/05_row_pooled_multiplicity/05_row_pooled_multiplicity.csv` lightgbm_family_best
   mean_delta = 0.007263182 = **+0.726pp exactly**. §7 is internally consistent (TCN +0.636pp,
   period-LCB +0.047pp all from the same row-pooled CSV). NOT a defect.
   (Ledger-hygiene note for the user: the ledger prose could add the row-pooled +0.726pp next to the
   equal-weight +0.70pp to prevent this confusion in future reviews.)

## FLAGGED for user (claim-framing judgment / ledger-mandated phrasing — NOT auto-applied per handoff)
5. **[P0] 04:10 "the protocol does not manufacture an edge on a near-null case".** Genuine
   claim-framing concern: with the bid-ask-bounce confound open (§8/§9), "does not manufacture an
   edge" can read as claiming the observed small edge is genuine. Codex fix: "the roster exercises
   the protocol on a near-null case, but cannot prove that a remaining edge is not manufactured."
   RECOMMENDATION: soften toward Codex's version (specificity claim, not genuineness claim). Left to
   the user — it's a claim-strength decision.
6. **[P1] 06:33 / 01:35 train-inner "frames the margin" / "smaller than the 1.69pp".** These use the
   LEDGER-MANDATED canonical C2.3 phrasing ("0.66pp spread, smaller than the +1.69pp
   official-validation margin ... separate domains ... no apples-to-apples pair"). Current text is
   governance-compliant; Codex's softer split is optional. User may consider.
7. **[P1] 07:65 / 07:58** already carry the "descriptive ... not a significance test" caveat;
   Codex's micro-hardening ("entirely positive"; "the only positive descriptive period-LCB") is
   optional polish.
8. **[P2] 09:53 positive-control "flags the absence of these signs".** Used consistently in
   abstract + §1 + §9 (author's intended framing: a real signal should show the pathology signs are
   ABSENT). Codex finds it confusing; defensible as-is. Optional clarity reword.

## What Codex confirmed the paper does WELL
Guarded readout consistently non-independent / not-clean-test / no-final-model; macro-F1 framed as
classification evidence not economic value; activity = eligible-row count not volume/liquidity;
conditional edge treated as a limitation; load-bearing numbers match the ledger.

## Net
The NO_GO is driven by localized, fixable wording — not a structural overclaim. Of 10 findings:
3 applied (verified), 1 rejected (false positive), 6 flagged (claim-framing / ledger-mandated /
optional). The Option-2 spine has NOT structurally crossed into overclaiming; the one true integrity
defect (time-reversed sentinel domain mix) is fixed.

## FINAL DISPOSITION of the 6 flagged items (user delegated "handle optimally")
APPLIED:
- **04:10** softened: "the roster can show that the protocol does not manufacture an edge" ->
  "The roster therefore exercises the protocol on a near-null case: it cannot prove that a surviving
  edge is not manufactured by an uncontrolled confound, nor that the protocol would catch a real
  signal." (removes the protocol-validity overclaim; ties to the open microstructure confound.)
- **07:58** "clears a period lower bound above zero" -> "has a period lower bound above zero"
  (removes the only test-connoting verb; LCB stays descriptive).
- **09:53 + abstract(main.tex:66) + 01:67** "flags the absence of these/such signs" ->
  "shows these/such signs are absent" (fixes the awkward "flags the absence of" across all three
  parallel statements; preserves meaning). NB: Codex's own suggestion "recovers these signs" was
  REJECTED — it inverts the meaning (a real signal should show the near-null signs ABSENT, not
  recover them).
LEFT (optimal = respect the fact source / avoid over-hedging):
- **06:33 / 01:35** train-inner "frames the margin" / "smaller than the 1.69pp" — LEFT: this is the
  ledger's deliberately-fixed C2.3 anti-scope-mixing canonical phrasing; both already carry the
  "separate domains / not a full-family comparison" disclaimer. Deviating would violate the fact source.
- **07:65** pooled CI — LEFT: already says "as a descriptive resampling interval rather than a
  significance test."
Post-fix: gate PASS (01/04/07/09), compile 8 pages, 0 undefined refs, PDF refreshed.

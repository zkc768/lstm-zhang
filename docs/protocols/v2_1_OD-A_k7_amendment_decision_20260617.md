# V2.1 OD-A Period-Count Decision & Amendment A1 (legitimize k=7) — 2026-06-17

Status: **DECISION RECORD + APPLIED protocol amendment.**
Decision: legitimize **k = 7** via a dated, pre-registered revision (Amendment A1)
to `docs/protocols/v2_1_guarded_walkforward_readout_protocol.md`.
Activation: **APPLIED 2026-06-17 (user-authorized; user to notify Ian separately).**
The §5.1 / §7 / §8 / §16 edits + the §17 revision-log entry are now in the protocol
body. (The committed config stays intentionally un-armed — FIX-2 retracted, see
§6.) The pre-registration is frozen before the planned re-run's first scoring event.

Designation (inherited, mandatory): guarded, historically-contacted walk-forward
readout. The full V2.1 forbidden-string list applies to this document. No
clean-test / final-model / tradeability claim is made anywhere here.

## 1. The conformance gap (what was found)

A 5-angle integration review (and the gpt-5.5 devil's-advocate) flagged a
pre-registration conformance gap, verified against the actual files:

- **Frozen protocol** constrains the period count to **k ∈ {2, 3}**:
  - §5.1 line 303: "Period count: k = 3 (OD-A default; k = 2 is the predeclared
    reduction)."
  - §7 lines 509-511 budget formula defines only "k=3 → 24 events; k=2 → 16
    events."
  - §16 sign-off template: "OD-A period_count_k: `<2 | 3>` (default 3)."
  - §5.1 lines 320-324: the k=3 design "covers 2017-2020 and stops before the
    2020 COVID regime … a later regime-stress extension would require its own
    **pre-registered revision**."
- **Executed run** `20260617_051047_321730` used **k = 7** (7 consecutive
  12-month periods, `wf_p1`…`wf_p7`, 2017-01-25 → 2024-04-19), **56 scoring
  events** (7 × 4 model rows × 2 seeds). Config `OD-A_period_count_k: 7`.
- The 2026-06-17 sign-off (advisor confirmation `gmail:19ebe45fd75d7f8b`)
  resolved `OD-A = 7`, but did so against a protocol whose §16 template offered
  only `{2 | 3}` and whose §7 budget formula did not define k=7. The supplementary
  `docs/lst_models_walkforward_validation_plan.md` argued for k=7, but it states
  "the protocol governs all conflicts" — so it cannot, by itself, widen OD-A.

**Why this matters (reviewer kill-shot):** as it stands, a reviewer can argue the
headline "5/7 periods positive" rests on a period design (k=7, spanning the
volatile post-2020 regime) that the project's own frozen protocol did not admit —
an adaptive-analysis / HARKing concern sharper than FIX-1 or FIX-2. This must be
resolved before any re-run.

## 2. The decision (user-selected): legitimize k=7

The user selected **"revise the protocol to legitimize k=7."** The mechanism is
the one the protocol itself names at §5.1 line 323: a regime-stress extension
"would require its own pre-registered revision." **Amendment A1 (this document) is
that revision.** Rationale:

- The holdout spans ~7.2 years (2017-01-25 → 2024-04-19); a k=3 / 2017-2020
  design uses < half of it and is wasteful of legitimately-available coverage.
- k=7 is **not** a favorable-window selection: the carving rule is unchanged
  (consecutive, non-overlapping, gap-free, **earliest-first**, all periods through
  the last fully-covered trading day). The **entire** post-boundary span is used,
  not a chosen sub-window — so the regime mix (COVID, 2022 bear, 2023 rally) is a
  consequence of using all the data, not of cherry-picking.
- It yields explicit regime-stress evidence (COVID P4, 2022 bear P6) that
  strengthens the stability readout the paper reports.

Honest disclosure that MUST accompany this decision wherever the period design is
reported (Stage 05, paper, Stage 06): the original run used k=7 before this
protocol-text revision existed; Amendment A1 formalizes the period design that the
2026-06-17 sign-off had already resolved, and the planned re-run executes under
Amendment A1.

## 3. Amendment A1 — exact text to apply (after sign-off)

Apply as a dated revision; preserve the original §5.1/§7/§16 text and add a
revision-log entry. Suggested edits:

**§5.1 — extend OD-A.** Replace "Period count: k = 3 (OD-A default; k = 2 is the
predeclared reduction)." with:
> Period count: **k = 7 (OD-A, Amendment A1, 2026-06-17)** — the full-coverage
> design: consecutive 12-month periods, earliest-first, spanning 2017-01-25 to the
> last fully-covered trading day (2024-04-19), the final period truncating per the
> rule below (≈15 months). k = 3 (2017-2020) is retained as the pre-Amendment
> default and k = 2 as its reduction; k = 7 is the active design. The earliest-
> first + all-periods-to-data-end rule is unchanged, so no period is selected for
> regime: the whole post-boundary span is used.

**§5.1 regime note — replace lines 320-324** with:
> Honest regime note (Amendment A1): k = 7 intentionally spans the full post-2017
> coverage — normal (P1-P3), COVID crash + recovery (P4), post-COVID rally (P5),
> 2022 bear (P6), 2023 rally + 2024 Q1 (P7). This is regime-stress coverage by
> using ALL available post-boundary rows under the earliest-first rule, NOT a
> favorable-regime selection. Rows beyond 2024-04-19 stay closed.

**§7 — extend the frozen budget formula** to add:
> k = 7 → **56 events** (7 × 4 model rows × 2 seeds); coverage_probe → 1 metadata
> contact; official_validation_scoring_events → 0. (k=3 → 24, k=2 → 16 retained.)

**§8 — criteria scope note (no change to the criteria themselves):** the criteria
still bind ONLY `tcn_frozen_primary`. With k = 7, `positive_period_count >= 2`
means "at least 2 of 7." `pooled_delta` uses the protocol §8 row-union (row-pooled)
estimand (FIX-1); the criterion-2 estimand binding is decided in this pre-
registration, before the re-run's first scoring event.

**§16 / revision log — add:**
> Amendment A1 (2026-06-17): OD-A extended to admit k = 7 (full-coverage design,
> 56 events); §5.1 period count + regime note and §7 budget formula revised
> accordingly. Pre-registered before the planned re-run's first scoring event.
> User + Ian sign-off: <reference>. Original k=7 run 20260617_051047_321730
> predated this protocol-text revision and is disclosed as such.

## 4. Integrity guards (bind the re-run)

- **Freeze before contact:** Amendment A1 + the criterion-2 estimand (FIX-1
  row-pooled) are frozen BEFORE the re-run's first scoring event. No period-count
  or estimand shopping after seeing results.
- **Second consumption:** the post-2017 segment is already historically contacted
  AND already scored once (run 20260617_051047). The re-run is a **second
  consumption of a spent guarded holdout** (Dwork 2015 adaptive-analysis hazard).
  It runs under a NEW run id and Stage 05 S5.1 must list BOTH consumptions in the
  guarded `readout_tier`, never merged with the official-validation tier.
- **No reselection / no new HPO** on the holdout; the V2 frozen selection is
  unchanged; `no_final_model_selected` stays true; LightGBM numerically highest is
  never "best/selected."
- Preserve the adversarial caveats (F1 calm-bar row-count proxy ≠ liquidity; F2
  ~2.25× not 3×; F5 only dropout absent; F8 df=1 LCB cosmetic).

## 5. Status of required actions

- **Applied (2026-06-17, user-authorized):** the §5.1 / §7 / §8 / §16 edits + the
  §17 revision-log entry are in the protocol body. The committed config is left
  intentionally un-armed (FIX-2 retracted — see §6). The pre-registration is
  frozen before the re-run's first scoring event.
- **Remaining (user):** notify Ian of Amendment A1. The user elected to proceed
  without a blocking pre-confirmation, judging the k=3 → k=7 gap minor. If Ian
  later requests a change, record it as a further dated amendment (do not silently
  rewrite A1).
- After this, the planned re-run (new run id) is conformant under Amendment A1.

## 6. Provenance

- Conformance gap: 5-angle integration review (workflow run `wf_e41cd3e2-c9c`) +
  gpt-5.5 devil's-advocate; verified directly against
  `docs/protocols/v2_1_guarded_walkforward_readout_protocol.md` §5.1/§7/§16 and
  `configs/stages/v2_1_guarded_walkforward_readout.yaml`.
- Real sign-off / coverage values: notebook `V2_1_SIGN_OFF` / `V2_1_COVERAGE_PROBE`
  (used by run 20260617_051047_321730). FIX-2 (filling these into the committed
  config) was RETRACTED: a contract test requires the committed config to stay
  un-armed (pending/null); provenance lives in the notebook + Drive decision
  record. The committed config is unchanged apart from an explanatory comment.
- Related: `docs/v2_1_limitation_claim_register_20260617.md` (FIX-1, FIX-2),
  `docs/lst_models_walkforward_validation_plan.md` (the k=7 argument).

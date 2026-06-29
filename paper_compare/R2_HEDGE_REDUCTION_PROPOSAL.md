# R2 Hedge-Reduction Proposal — for user approval

**Status: PROPOSAL. Touches no prose. Approve before any edit.** Presentation-only:
no number, no claim-strength, no domain-fusion change. Built from Cowork's Mode-B
cold-read (`handoff/VERDICT.md` §B/§F) + `paper/length_loop/protection_manifest.json`
floors + the r071 floor-coverage audit + a live unit-ending scan (2026-06-29).

Two diagnoses → two tracks:
- **Track B** — same caveat repeated across sections (cross-section repetition).
- **Track F** — positive statements buried under negative framing (within-unit tone).

---

## 1. The reframe (this is safer + cheaper than first thought)

r071 reported hedge-dedup "CONVERGED / no safe headroom." That audit measured **only
within floored scopes**. The real headroom is the gap between where a caveat **actually
appears** (`currently_in`) and where it is **required** (`floors`): a concept sitting in a
scope that has **no floor** is removable and `gate_L2` still passes (that scope's floor = 0).
r071 never tabulated this out-of-floor footprint, so "converged" hid it.

**Consequence: ~20+ repeated instances are removable WITHOUT any floor change.** Only a
small residual needs a user-approved floor reduction.

## 2. Track B — repetition (cluster → D-lock → headroom)

Counts are the manifest's recorded footprint (may be slightly stale post-R2 — a live recount
pins exact file:line **before** any edit).

| Cowork cluster | D-locks | appears in | floor-required | **gate-safe to thin (no floor change)** | needs your sign-off? |
|---|---|---|---|---|---|
| ① "no model selection / no architecture / no ranking" | D3 (7), D11 (4), D15 (3) | ~14 | 5 | **~9** | no (B1) |
| ② "not clean test / non-independent / not out-of-sample" | D1 (8, floor 5), D2 (8, **floor 2**) | ~16 | 7 | **~9** | no (B1) |
| ③ "two seeds insufficient" | D18 (8, floor 3) | 8 | 3 | **~5** | no (B1) |
| ④ "descriptive, not significance" | D12 (3, floor 3) | 3 | 3 | **0** | **yes (B2)** — all 3 scopes floored |
| ⑤ "roster only drives the protocol" | untracked (≈D15-adjacent) | ~5 | 0 | judgment | no — R3 default-keep + judgment |
| ⑥ "thin / weak / near-null" verbal tic | untracked + D24 (near-null) | dozen+ | — | → Track F | no — reword, not delete |

Smaller additional gate-safe headroom in D17 (frozen-split, 6→floor 1), D25 (scope, 5→floor 1),
D23 (not-economic-value, 5→floor 3), D24 (no-positive-control, 4→floor 2).

**Two sub-classes:**
- **B1 — gate-safe thinning (NO floor change).** Remove instances in non-floored scopes.
  ~23 candidates. `gate_L2` passes by construction.
- **B2 — floor reduction (NEEDS YOUR SIGN-OFF).** Only where every appearance is floored
  (cluster ④ D12) or to cut below a floor. Itemized for approval; floors were your call
  (2026-06-26), so lowering them is yours too.

**Safety on B1 (gate-safe ≠ auto-delete):** each removal is still cross-checked against the
D-lock's `_note` (some notes ask to keep instances beyond the floor — e.g. D1 wants the
guarded-vs-validation pairing in intro/abstract; D18 wants abstract + §09), against **R4**
(never delete a hedge adjacent to a ledger-bound positive without justification — guards Q2
upgrade-by-deletion), **L5** (survivors not strengthened), and a Cowork re-read.

## 3. Track F — negative framing (reorder/reword, NOT delete)

Live unit-ending scan (file:line are current):

| Unit | Defect | Target |
|---|---|---|
| Abstract | **ends on "untested"** (main.tex:63–65); 3 positive→but | end on the contribution; keep D24 no-positive-control bound but co-located earlier, not the last word |
| §1 intro | **opens** "or it can be an artifact" (01:8–9) **and closes** on "next step" (01:69–70) | open on the question/contribution; close on what was established |
| §3 protocol | closes "No reported number crosses domains" (03:91–95) | fine to keep (domain-separation is a method strength) — low priority |
| §6 results | last substantive para ends "**inverts below the random prior**" (06:56); textbook "three conditions met → that is a fact about a fixed bar, not a demonstration" (06:20–22) | reorder so the met-conditions read as a finding bounded in-line, not a finding then a deflation |
| §7 guarded | closes on "**flips**" (07:74–76) | close on what the predeclared sign established; the flip-pointer can lead into §8 without being the last word |
| §8 diagnostics | **opens AND closes on negation** (09–11; 120–121) | §8 is a limits section by design — lowest-priority; at most soften the opener |
| §9 conclusion | closing "half-deflated": reasserts contribution but ends on "**breaks**" (09:55–57) | end on the transferable contribution; "holds and breaks" → "holds, and maps where it breaks" keeps the limitation but ends on the map (a contribution) |

Pattern to break (all 8 units): the default sentence shape "positive → though/yet/but-not."
22 instances logged. Fix is **co-location + reorder**, never removing the bound.

**Safety on F:** R4 (relocation adjacent to a ledger-bound positive = justification event,
even with no token change) + floors (the caveat still appears, just repositioned) + L5 +
Cowork re-read confirming it did not cross into overclaim.

## 4. Metric (adopt Cowork's — baseline recorded now)

Track in R5 each round:
- **Units closing on negation: 5/8** (strict last-body-sentence) — 6/8 if "last substantive
  sentence" (§6 counts).
- **Units opening on negation: 2/8** (§1, §8).
- **Positive→but instances: 22** across all 8 units.

Success = closings-on-negation falls **and** Cowork confirms no required caveat lost (floor +
`_note` intact) **and** Codex finds no overclaim. Overshoot guard: if it crosses into
honestly-weak→misleadingly-confident, that is a regression (Cowork's Q6 document-level read).

## 5. What needs your decision

1. **Approve B1** (gate-safe thinning, no floor change) — low risk, ~20+ instances, biggest
   effect on the "drumbeat."
2. **Approve B2** (floor reductions) — itemized; mainly cluster ④ (D12 descriptive-not-
   significance) if you want it thinned below 3 scopes. Optional.
3. **Approve F reorder targets** (abstract / §1 / §6 / §7 / §9 prioritized; §3 / §8 low).
4. **Scope flip:** this ACTIVATES the removal/reposition phase — R3/R4 move from dormant to
   live, governed by the safety layer above.

## 6. Proposed sequencing

1. **Live recount** (machine count of the B1 candidates → exact file:line; refresh stale
   manifest footprints).
2. **Track F reorders** first (biggest perceived-tone win, changes no counts) — per unit,
   guarded by R4/L5.
3. **B1 gate-safe thinning** — remove non-floored repeats; `gate_L2` + integrity gate per edit.
4. **B2 floor reductions** only if §B still reads repetitive after B1 (and only what you approve).
5. **Recompile** → refresh `handoff/REVIEW_THIS.pdf` + `WHAT_CHANGED.md` (incl. the suppressed/
   removed-caveat log + the metric delta) → **Cowork Mode-B re-read** → metric check → stop per
   ADR-0002.

## 7. Out of scope
No new experiments / numbers / model selection / claim-upgrade. No softening of n=2 / scope /
no-clean-test / domain-separation **at their floored locations**. The floors + L5 + Codex remain
the safety net throughout.

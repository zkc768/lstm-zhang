# DEDUP_LOG — removal / reposition records (R3/R4 discipline)

Per the 2026-06-29 scope update: removal/repositioning is IN SCOPE; R3/R4 LIVE. Every removal or
reposition of an existing hedge is logged here with its **gate L2 report**, so the Judge sees the
gate's actual floor accounting (not just Executor prose). The Judge still reads only this folder.

Flagged into existence by the Judge (round-2 process flag, 2026-06-29): batch 1 was mislabeled
"reorder only" but contained these two edits. Recorded now, not as an exception but because B1+F
approval already put removal in scope.

---

## Batch 1 (abstract / `main.tex`) — 2 records

### R-1  D9 (bid-ask-bounce caveat) — REPOSITION (not a removal)
- **Action:** folded the free-standing sentence "We cannot yet separate this pattern from a
  bid-ask-bounce artifact." into the preceding conditional sentence ("…on the most active ones,
  a pattern we cannot yet separate from a bid-ask-bounce artifact.").
- **Floors:** D9 floors = `section:08`, `section:09`. **`main.tex` is NOT a D9 floor** → no floor
  touched; the caveat is still present in the abstract (repositioned, not deleted).
- **R4 adjacency check:** the bid-ask caveat is not adjacent to a ledger-bound positive; folding
  it strengthens no survivor. `monotonicity_preserved: true`.

### R-2  D24·anti_leak (no-positive-control / untested) — DEDUP 2→1
- **Action:** the abstract carried D24 twice — "no known-signal positive control" AND "sensitivity
  to a genuine signal is untested". Kept the first; the "untested" meaning is retained in plain
  words ("not yet a test on a signal known to be real").
- **gate_L2 report (orig = baseline `main.tex` vs cand = edited), verbatim:**
  ```json
  "dedup_ok": [{"id": "D24", "group": "anti_leak", "scope": "main.tex", "orig_hits": 2, "cand_hits": 1}],
  "missing_required": [], "forbidden_introduced": [], "floor_unbound": [ ... §07 D16, pre-existing, unrelated ... ]
  ```
  floor(`main.tex`) = 1 → **met** → classified `dedup_ok` (≤MINOR), **not** `floor_breach`.
- **canonical_kept:** "no known-signal positive control" (abstract, `main.tex`).
- **R4 adjacency check (this is the round-1 Q2 risk — the most important line).** The removed
  instance sat next to the new contribution close ("The transferable contribution is the protocol
  and its diagnostics"). Does dropping "untested" + closing on the contribution upgrade the edge?
  - The retained bound ("no known-signal positive control" + "not yet a test on a signal known to
    be real") is co-located **immediately before** the contribution close (R2 carve-out satisfied).
  - The contribution close asserts the PROTOCOL/DIAGNOSTICS are the contribution — it makes no
    claim the empirical edge generalizes or is validated.
  - **Executor judgement: no claim-upgrade.** This is exactly `WHAT_CHANGED.md` ask #3 — **please
    verify it independently in your read; do not take this judgement on faith.**
- **L5 (monotonicity):** pass — no survivor reworded conditional→assertive.
- D24·anti_leak·`section:09` (the other floored scope) untouched.

---

## Convention for the coming batches (§7 reorder, B1 cross-section thinning)
Each removed or repositioned hedge gets a record above with: id · scope · floors · the verbatim
`gate_L2` dedup_ok/floor lines · canonical_kept · R4 adjacency check · L5 result. A removal with
`floor_breach` or a failed L5 is NOT applied — it is flagged and stopped.

---

## Batch 2 (§7 reorder [already in source] + §07 D16 floor-rebind + B1 thinning) — 2026-06-29

### Gate-behavior note for B1 records (READ FIRST — corrects the handoff accept line)
B1 removes caveat restatements from scopes that carry **no floor** for that D-lock. The L2
gate measures a D-lock **only in its declared floor scopes**, so a non-floored removal produces
an **empty `dedup_ok` by construction** — there is no floored-scope count to decrement. (Verified
empirically: trial removal of a §05 D18 instance returned `dedup_ok: []` with `missing_required: []`.)
The safety signal for these records is therefore: `missing_required=[]` (every floored scope's
count unchanged → floor preserved), `floor_unbound=[]`, `forbidden_introduced=[]`, and L1/L3/L4/L5
pass — with **L3** independently confirming the concept still covers its claim paper-wide. The
informational section-scope orig→cand count (computed via `length_gates` normalization) is given
per record for transparency. The handoff's "L2 `dedup_ok` non-empty" accept line only holds for
`paper`-floored locks (e.g. D11) or above-floor removals **inside** a floored scope — not for the
cross-section/non-floored thinning B1 actually targets.

### R-3  D16·5of7_desc (§07) — FLOOR-REBIND REWORD (governance hygiene; not a dedup)
- **Action:** §07 `…are descriptive context, neither certification nor the bar.` →
  `…are descriptive context, not certification and not the bar.` The D16·5of7_desc manifest
  variants already track `not certification and not the bar` / `not the bar`; an R2 reword to
  "neither…nor" silently broke the match (design-doc §9.3-B), leaving `D16·5of7_desc·section:07`
  **floor_unbound** (orig_hits=0). The caveat was present and honest throughout; only the tracker
  lost it.
- **Why prose, not a manifest `match_any` addition:** the manifest lives only in gitignored
  `paper/length_loop/` (NO tracked copy — `git check-ignore` confirms) and is "regenerated fresh
  from the .tex files". A `match_any` addition would be local-only, lost on regeneration, and
  invisible to the Judge. Restoring the prose to the already-tracked form is durable (committed in
  the mirror) and meaning-identical (still denies certification, still denies being the bar).
- **gate (cand==applied disk):** `D16·5of7_desc·section:07` orig_hits 0 → **cand_hits 2** (bound);
  overall `pass=True`; `floor_unbound=[]`; `missing_required=[]`; `forbidden_introduced=[]`;
  L1/L3/L4/L5 pass.
- **R4 adjacency / L5:** the 5/7 disclaimer is itself the survivor; the reword preserves its
  strength (neither/nor → not/and-not), upgrades no adjacent positive. `monotonicity_preserved: true`.

### R-4  D18 (two-seed) — §05 setup — REMOVE 1 restatement
- **Action:** removed the standalone limitation sentence `Two seeds are too few to quantify
  seed-to-seed variance.` The preceding clause `…over $n{=}\numseeds{}$ seeds (101 and 202)…` is
  KEPT, so §05 still discloses the seed count; only the *limitation restatement* is dropped.
- **Floors:** D18 floors = `main.tex:1`, `section:06:1`, `section:09:1`. **`section:05` is NOT a
  D18 floor** → no floored scope touched.
- **gate (verbatim, cand vs on-disk baseline):**
  ```json
  "dedup_ok": [], "missing_required": [], "floor_unbound": [], "forbidden_introduced": []
  ```
  L1/L3/L4/L5 all pass, overall `pass=True`. `dedup_ok` empty by construction (§05 non-floored for
  D18 — see note); floored scopes main/06/09 unchanged so floor preserved; L3 confirms D18 still
  covers C2.1 paper-wide.
- **Section-scope count (informational, `length_gates` normalization):** §05 D18 **5 → 0**. The
  "5" was a single sentence matching five overlapping variants (`two seed`/`two seeds`/`two seeds
  are too few`/`too few to quantify`/`too few to quantify seed to seed variance`) — design-doc
  §9.3-F overlap inflation. The `n=2 seeds (101 and 202)` descriptor does **not** match D18 (digit,
  not "two") and remains in §05.
- **canonical_kept:** §06 `Two seeds yield a descriptive spread rather than a variance estimate.`
  (section:06 floor) + §09 `…rests on \numseeds{} seeds, too few for seed-to-seed variance`
  (section:09 floor) + abstract `main.tex` (main floor). Paper-wide D18 footprint unchanged except §05.
- **R4 adjacency check (the round-1 Q2 risk — the important line):** the removed sentence followed
  `…report the official validation outcome in \macrofone{} over $n{=}\numseeds{}$ seeds (101 and
  202)…`, which states **no positive margin** (no 0.5170, no +1.69pp). The dropped caveat was
  therefore **not adjacent to a ledger-bound positive**, and the two-seed limitation stays
  co-located with the positive margins where they actually appear (§06 1.69pp; §09). No survivor
  reworded. **Executor judgement: no claim-upgrade — please verify independently.**
- **L5 (monotonicity):** pass — no survivor strengthened conditional→assertive.

### Considered-but-KEPT (R3 default-keep; flagged for transparency, NOT applied)
- **D3 (no final model) — §05 flag clause** `; the route manifest sets
  \nolinkurl{no_final_model_selected=true}`. A genuine within-sentence doubling (prose `is not a
  model-selection event` + the flag). **KEPT:** red-line [1]-adjacent, and the flag is concrete
  machine-checkable provenance (same style as §03 `for_selection set to false` / §07
  `for_selection=false`). Genuinely unsure → R3 default-keep. The §05 no-selection drumbeat was
  therefore NOT thinned.
- **D2 (non-independent) — §03 (3) / §07 (above-floor) / §08 (above-floor):** load-bearing —
  domain-naming in the budget-ledger paragraph (D22 home), figure/table captions that must stand
  alone, and the §08 cross-era floor sentence (D2 `_note` requires it). KEEP.
- **D17 / D18 / D25 in §03·§06·§08:** scope-bind a specific number (R2/R4 carve-out), are factual
  ticker/interval definitions, or live in `\Description`/caption surfaces. KEEP.
- **§09 (limitations) instances:** §09 is a designated hedge zone (R1) — caveats belong there. Not thinned.
- **batch-1 files (abstract `main.tex`, §01):** under live Judge review; not touched in batch 2 to
  avoid colliding with that review. The largest non-floored count-headroom lives here and is
  deferred to a post-review pass.

### Why B1's APPLIED yield is 1 removal (not the proposal's ~20+)
The proposal's count (`currently_in − floors`) was overlap-inflated (design-doc §9.3-F): one
sentence matches many variants. Working from the prose (r050 discipline), the genuinely-safe,
non-floored, non-zone, non-batch-1 restatement set reduced to the §05 D18 sentence. The rest is
load-bearing, caption/`\Description`, factual, already-thinned by r050, or deferred (batch-1).
`flag-don't-spin` + R3 default-keep were applied throughout; no `floor_breach` and no failed L5
anywhere.

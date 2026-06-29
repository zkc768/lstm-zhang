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

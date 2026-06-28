# lst_models Hedge De-duplication Floors — Design / Decision Draft

Status: **DRAFT v4 — read-only. User decisions resolved (2026-06-26); ready for execution.**
2 `floor_unbound` items → prereq manuscript edits (§9.4 RESOLVED); §9.3 deltas accepted.
Pending: user GO on execution granularity, THEN prereq edits → §8.4 + Step-4
governance patch → repair Rounds 1–2 → final re-review.
Nothing here modifies any manuscript, manifest, gate, or `state.json` file.

Composes with, never overrides: `AGENTS.md`, claims ledger, Doc A/B, anti-AI
style guide, `lst_models_paper_revision_workflow.md`,
`lst_models_external_codex_reviser_adapter.md`.

## 0. Why this exists (the precise problem)

§6–§9 "density" is dominated by the same hedge restated 3–8×. Two facts:
1. **The deterministic gate already permits removing duplicates** —
   `gate_L2` uses `floor = min(min_count, original_scope_hits)` and blocks only on
   candidate hits `< floor` (`paper/scripts/length_gates.py:146`).
2. **The block is the *manual* §8 deletion-first checklist**
   (`lst_models_paper_revision_workflow.md:106`), and the manifest's
   `safe_to_thin_to_one` flag is **never read by any gate** (dead field).

Fix: gate emits explicit `dedup_ok` / `floor_breach` / `floor_unbound` grounded in
**per-scope floors**; §8 reviewer reads that classification.

Scope: **only** hedge dedup. Separate edit classes, NOT in this patch:
caption-lock governance (r040/r042); §6/§8 long-sentence split.

## 1. Definitions

- **floor(D, scope)** — minimum surviving instances of `D` (any normalized
  `match_any` variant) that must remain in `scope` after an edit. A phrase may
  declare floors in several scopes at once.
- **dedup_ok** — `after_hits ≥ floor` in every declared scope, and `after < before`
  somewhere. Redundant restatement removed, caveat still covered. **≤MINOR.**
- **floor_breach** — `after_hits < floor` in some scope (last required instance
  removed). **≥MAJOR/STOP.**
- **floor_unbound** *(NEW, per review MAJOR-1)* — a *declared* floor whose scope has
  `orig_hits = 0` in the **live** text. The floor cannot be enforced (nothing to
  preserve). **Must NOT silently pass.** Resolution before Step 4: either (a) the
  caveat is genuinely absent and must be **added** to that scope first (a separate
  authorized edit), or (b) the floor is mis-placed and should move. Never (c)
  leave it at `floor = min(min_count,0) = 0`.
- **canonical_kept(D)** — the surviving instance the reviser declares load-bearing
  in `D`'s home scope (quote + `file:line`).
- **required_groups(D)** *(NEW, per review MAJOR-2)* — when a caveat needs **two or
  more distinct clauses to BOTH survive**, a single `match_any` count cannot
  express it. `required_groups` lists sub-groups, each with its own `match_any`
  subset and its own floor; the gate enforces **every** group independently.

Orthogonal, unchanged: L5 hedge-monotonicity (a *surviving* instance reworded
conditional→assertive is ≥MAJOR), forbidden F-term negation, L1
numbers/cites/labels, `never_delete`. Dedup removes whole redundant restatements
only; it never softens a survivor.

## 2. Manifest schema change (additive, back-compatible)

```jsonc
{
  "id": "D18",
  "match_any": ["two seeds", "too few to quantify", "thin for seed to seed variance"],
  "scope": "paper",                 // kept (back-compat)
  "min_count": 1,                   // kept (back-compat)
  "safe_to_thin_to_one": true,      // DEPRECATED/IGNORED once floors lands (see §8.3)
  "floors": {                       // NEW — authoritative per-scope minimums
    "main.tex": 1,
    "section:06": 1,
    "section:09": 1
  }
}
```

`required_groups` form (D16 example):
```jsonc
{
  "id": "D16",
  "floors": { "section:07": 1 },              // back-stop
  "required_groups": [
    { "name": "weak_bar",        "match_any": ["at least two of the seven periods","two of seven","intentionally weak floor","deliberately weak predeclared bar","about 94","94 percent of the time"], "floors": {"section:07": 1} },
    { "name": "5of7_descriptive","match_any": ["5/7 positive periods","five of seven positive periods","are descriptive, not the bar","an observed count, not a stronger pass"], "floors": {"section:07": 1} }
  ]
}
```
When `required_groups` is present it **supersedes** the flat `match_any` for floor
purposes (each group must independently meet its floor).

Scope spelling (per review Schema): `section:NN` and `main.tex` only. **No bare `07`.**

## 3. Gate change — `gate_L2` extension (sketch)

```python
for rp in manifest['required_phrases']:
    groups = rp.get('required_groups') or [{'match_any': rp['match_any'],
              'floors': rp.get('floors') or {rp.get('scope','paper'): rp.get('min_count',1)}}]
    for g in groups:
        variants = [normalize_for_match(v).strip() for v in g['match_any']]
        for scope, min_inst in g['floors'].items():
            oh = count_variants(variants, scope_text(cur,  scope))
            ch = count_variants(variants, scope_text(cand, scope))
            if oh == 0:
                floor_unbound.append({'id': rp['id'], 'group': g.get('name'), 'scope': scope})
                continue                                    # NEVER silent-pass (review MAJOR-1)
            floor = min(int(min_inst), oh)
            if ch < floor:
                floor_breach.append({'id': rp['id'], 'group': g.get('name'), 'scope': scope, 'orig': oh, 'cand': ch})
            elif ch < oh:
                dedup_ok.append({'id': rp['id'], 'group': g.get('name'), 'scope': scope, 'orig': oh, 'cand': ch})
# L2 PASS requires floor_breach == [] AND floor_unbound == []. dedup_ok is reported, not a block.
```
`scope_text` needs a small extension to accept `section:NN` + `main.tex` keys.

## 4. gate_selftest cases (ship with the Step-4 patch) — 6 total

1. **allowed dedup** — floors `{paper:1}`, before=3 → cand=1 ⇒ `dedup_ok`, PASS.
2. **blocked last-instance deletion** — same, cand=0 ⇒ `floor_breach`, BLOCK.
3. **L5 survivor-strengthening** — `hedge_locks` `"to the extent"` (08:42) removed/strengthened ⇒ L5 `stripped`, BLOCK.
4. *(NEW)* **`main.tex` floor** — floors `{main.tex:1}`, abstract instance removed ⇒ `floor_breach`, BLOCK.
5. *(NEW)* **multi-section floor / required_groups** — D16-shaped: drop the `5of7_descriptive` group while keeping `weak_bar` ⇒ `floor_breach` on that group, BLOCK.
6. *(NEW)* **`orig_hits=0` unbound-floor warning** — declare a floor on a scope with no live hit ⇒ `floor_unbound`, NON-silent flag (blocks Step-4 sign-off until resolved).
7. *(NEW, per W2)* **`main.tex` scope fidelity** — a `main.tex` floor must measure the abstract ONLY. Pin a regression test on `D24·anti_leak·main.tex == 0` and `D18·main.tex == 3`; if `scope_text` regresses to returning `paper_norm`, these flip (to 3 and 21) and the test fails closed.

## 5. §8.4 rule text (to add to revision_workflow.md, Step 3)

> **§8.4 Hedge de-duplication is not deletion.** When the deterministic L2 gate
> reports `dedup_ok` for a phrase `D*` (every declared floor and `required_group`
> still met), removing the redundant restatement(s) is **permitted, ≤MINOR** — the
> "removed hedge → ≥MAJOR" escalation does **not** fire. Escalation (≥MAJOR/STOP)
> is reserved for: (i) `floor_breach`; (ii) `floor_unbound`; (iii) an L5
> monotonicity strip; (iv) a forbidden F-term turned affirmative. The reviewer's
> residual check is `canonical_kept`. The reviser declares `hedge_dedup` (id,
> floors, before/after by scope, canonical_kept, monotonicity_preserved) in
> `PLAN.md` for every touched `D*`.

## 6. Per-D-lock floor mapping — user-reviewed (2026-06-26)

`now` is **manifest `currently_in`** and may be STALE — Step 2.5 replaces it with
live `orig_hits`. Bold = changed/confirmed by user review.

| ID | floors (user-approved) | notes |
|----|------------------------|-------|
| **D1** | `main.tex, section:06, section:07, section:08, section:09` | user: §6 Panel B fig + §8 cross-era are skimmer-visible guarded-vs-validation |
| D2 | `section:07, section:08` | |
| **D3** | `section:06, section:07, section:09` | **fix live §7 to actually match D3 first; `main` is NOT a floor unless abstract first gets a "no final model selected" sentence (separate authorized edit)** |
| D4 | `section:06` | |
| D5 | `section:03` | |
| D5b | `section:08` | |
| **D6** | `section:03, section:09` | **§9 "3.0 bps / nine bars / no sensitivity scan" is a mandatory limitation, not just a method number (Doc B + 09:23). Alt: split a band/horizon-no-sensitivity D-lock — see §6.2** |
| D7 | `section:03` | |
| D8 | `section:08` | |
| D9 | `section:08, section:09` | |
| D10 | `section:07` | |
| D11 | `paper` | genuine thin-to-one |
| **D12** | `section:06, section:07, section:08` | **§6 block-bootstrap intervals must keep descriptive/not-inferential too** |
| D13 | `section:07` | |
| D14 | `section:08` | |
| D15 | `section:07` | |
| **D16** | `required_groups` (weak_bar + 5of7_descriptive), both `section:07:1` | **split per MAJOR-2** |
| D17 | `section:06` | |
| **D18** | `main.tex, section:06, section:09` | **§6 validation readout must keep n=2; main+09 alone is insufficient** |
| D19 | `section:08` | |
| D20 | `section:08` | |
| D21 | `section:08` | |
| D22 | `section:03` | |
| **D23** | `main.tex, section:03, section:09` | **+ anti-leak group (§6.2): bare `return free`/`drop neutral` must NOT alone satisfy "not economic value"** |
| **D24** | `main.tex, section:09` | **+ anti-leak group: bare `known signal positive control` (no negation) must NOT alone satisfy "no positive control"** |
| D25 | `section:09` | |

### 6.2 Multi-clause & anti-leak (`required_groups`)
- **D16** — split: `weak_bar` (≥2/7 bar / ~94% coin-flip) AND `5of7_descriptive`
  (5/7 is descriptive, not the bar) must each survive in §07.
- **D23** — require ≥1 *substantive* economic-boundary phrase ("not economic
  value" / "not a measure of economic value" / "no margin … is a trading claim")
  per floored scope; a bare methodology descriptor (`drop neutral`, `return free`,
  `classification only`) does **not** satisfy the floor alone.
- **D24** — require ≥1 *negated* form ("no known signal positive control" /
  "sensitivity to a genuine signal is untested"); bare "known signal positive
  control" (the next-step framing) does **not** satisfy the floor alone.
- **D6** *(open choice)* — add `section:09` to D6, **or** create a new D-lock
  `D6b: band/horizon-no-sensitivity-scan` floored at §09. Recommend the latter
  (cleaner separation of "frozen value" from "no-sensitivity limitation").

## 7. Execution order

1. (this doc) read-only floor design draft. ✅
2. User review of floors. ✅ (major revision applied above)
2.5. **Live floor coverage audit (NEW, independent window).** For every
   user-approved floor scope, compute normalized `orig_hits` via
   `length_gates.scope_text` + `count_variants` against the LIVE manuscript.
   Output: `{id, group, scope, orig_hits, status: bound|floor_unbound}`. Every
   `orig_hits=0` is flagged `floor_unbound` with a remediation note (add caveat /
   move floor). **Then** a fresh adversarial panel reviews the audit.
3. (after final sign-off) add §8.4 rule text to `revision_workflow.md`.
4. Orchestrator/governance round: patch `protection_manifest.json` (floors +
   required_groups) + `gate_L2` + 6 `gate_selftest` cases; DECISION + hashes; run
   selftest; 1 independent verifier confirms existing-D-lock semantics unchanged.
5. §6/§8 text repair, two rounds (each FREEZE→PLAN→CANDIDATE→round_diff[L1-L5]→
   adversarial review→SYNTH→APPLY→COMPILE→VERIFY):
   - Round 1 long-sentence split (must clear L5; no dedup-rule dependency).
   - Round 2 hedge dedup to approved floors (reviewers read dedup_ok/floor_breach/floor_unbound).
6. Fresh adversarial re-review panel on §6–§9.

### Agent/window topology (independence)
- Reviser ≠ Reviewers ≠ Synthesizer (orchestrator). Reviser/executor write only to
  `runs/<round_id>/`; only the orchestrator applies.
- Step 2.5: **1 executor** (live audit) + **3-agent adversarial panel** (correctness/
  fidelity, completeness/unbound-detection, adversarial-leak), all independent of
  each other and of the orchestrator.
- Step 4: 1 verifier. Each repair round: 1 Reviser + 2 diff-only reviewers.
- Final: 4-agent panel, fresh window.
- Peak concurrency ≤ 4; reviewers wait for the round's candidate/audit.

## 8. Open items
1. **floor_unbound list** — produced by Step 2.5; each needs an add-caveat-or-
   move-floor decision before Step 4. (D3/§7 already known.)
2. D6: add `section:09` to D6 vs new `D6b` (recommend D6b).
3. Schema: `safe_to_thin_to_one` → marked **deprecated/ignored** (NOT a live
   "derived hint" — recomputing it risks contradicting `floors`, e.g. D18).

## 9. Step-2.5 audit + adversarial review findings (2026-06-26)

Artifacts: `paper/length_loop/runs/r046_floor_coverage_audit/coverage_report.md`
(W1 executor) + W2/W3/W4 panel. All read-only; nothing under `paper/` modified.

### 9.1 Audit (W1)
48 floors measured against live text via the real `length_gates` normalization.
**2 `floor_unbound`** (orig_hits=0): **D3·section:07** and **D24·anti_leak·main.tex**.

### 9.2 Panel verdicts
- **W2 (fidelity): counts TRUSTWORTHY** (reproduced byte-for-byte) — but found a
  gate-implementation hazard (§9.3-A).
- **W3 (completeness): COVERAGE COMPLETE** — 9 floors are at `orig_hits==1`
  (zero dedup headroom; §9.3-E). High-count rows are inflated by overlap
  summation (counts overstate headroom; §9.3-F).
- **W4 (caveat-leak): one floor is a DEMONSTRATED soft pass** (§9.3-B) — counting
  was the wrong question; a floor can be "bound" by a token that is not the caveat.

### 9.3 Required Step-4 deltas (NOT optional — fix variant lists + gate, not gate logic)
- **A — `scope_text` must natively resolve `main.tex` / literal-relpath scopes.**
  Today `scope_text(state,'main.tex')` falls through to `paper_norm` (whole paper),
  so a naive `main.tex` floor would measure the whole paper, not the abstract —
  silently "binding" D24·anti_leak·main.tex (would read 3, not 0) and masking the
  gap. Patch: return `state['sec_norm'][scope]` for any known relpath key. Add
  selftest case 7 (§4).
- **B — D16·5of7_desc variant list is SOFT (proven by W4 simulation).** Its only
  live-matching variant is the *count* phrase `five of seven positive periods`;
  the substantive-disclaimer variants (`are descriptive, not the bar`,
  `an observed count, not a stronger pass`) are **dead** (live text is "descriptive
  context, not certification and not the bar"). Deleting the disclaimer while
  keeping the count → gate PASSES. Fix: add live-hitting substantive variants
  (`not certification and not the bar`, `not the bar`) so the floor pins the
  disclaimer, not the count.
- **C — D8·§08 weakly carried.** Held by the locator token `calm bar`; the
  substantive variant (`below random on the most active`) is dead (live:
  `drops below the balanced random prior in the most active ones`). Fix: add the
  live substantive phrasing as a variant.
- **D — D23 anti_leak dead variant.** `"no margin ... is a trading claim"` has a
  literal `...` → never matches. Repair to `no margin here` / `is a trading claim`
  (both hit §09) — gives §09 a 2nd carrier; changes no current verdict.
- **E — pin 9 `orig_hits==1` fragile floors as `canonical_kept`** (Round-2 must NOT
  thin these; one reword breaches): D1·main.tex, D1·§06, D1·§08, D1·§09, D3·§09,
  **D16·5of7_desc·§07** (also soft — fix B first), D18·§09, D23·anti_leak·§03,
  D23·anti_leak·§09.
- **F — reviser caution:** high counts (D10·§07=10, D19·§08=11, D18·§06=8,
  D24·§09=8) are overlap-inflated; deleting one sentence can drop the count by >1.
  Do not read the integer as dedup headroom.

### 9.4 RESOLVED — 2 user decisions (2026-06-26)
- **D3·§07 → fix §7 prose by REPLACEMENT (user: replace, not add).** Change the
  existing "…and no family is selected" to "…and no final model is selected" (or
  "…the guarded readout is not a model-selection event"). Net ≈0–1 words. The
  family-no-ranking concept survives via `07:16` "never ranked or selected"; "no
  family is selected" is NOT itself a tracked required-phrase, so the swap drops no
  tracked caveat while making D3 (no-final-model) literally present in §7 prose.
  Runs as a small manuscript round (FREEZE→CANDIDATE→L1–L5→review→APPLY→COMPILE,
  confirm ≤8pp). After apply, D3·§07 is bound. D3 floors = §06,§07,§09 (`main` is
  NOT a D3 floor — would require a separate abstract "no final model" sentence).
- **D24·anti_leak·main.tex → add a negated substantive form to the abstract.**
  Extend the abstract's "…not yet validated on a known-signal control" to carry a
  negated form (e.g. "with no known-signal positive control, so its sensitivity to
  a genuine signal is untested"). Manuscript round on `main.tex` (high-protection:
  hold 200–220w + ≤8pp). After apply, D24·anti_leak·main.tex is bound.
- Both edits are **PREREQ to Step 4** (so its post-edit re-audit shows all floors
  bound). They are caveat additions/replacements, not dedup, so they clear the
  existing L1–L5 without the new rule.

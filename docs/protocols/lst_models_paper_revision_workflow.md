# lst_models Paper Revision Workflow (final QC + integrity)

Status: long-term protocol. Governs every automated/agent revision round on `paper/`.
**Handoff note (ADR 0005):** the live `paper/` may be the PROMOTED v2 rewrite produced by Workflow 1
(`paper_compare/PAPER_WORKFLOW.md`, the sandbox writing loop). Promotion runs through
`paper_compare/promotion_reconcile.py` (v2 must satisfy this manifest first), then this workflow
takes over for round-based revision + the submission-QC matrix. See ADR 0005 for the full handoff.
Runtime companions: `paper/length_loop/state.json` (machine truth) + per-round
`paper/length_loop/runs/<round_id>/`. This protocol composes with, and never
overrides, `AGENTS.md`, the claims ledger (`paper/outline_and_claims.md`),
Doc A/B, the anti-AI style guide, and `docs/agent_capabilities_and_skill_routing.md`.

## 1. Purpose And Non-Goals
Goal: make narrow manuscript progress while preserving the paper's scientific
contract. There are two modes:

- **Length mode**: active only while the compiled paper is over the hard
  8-page ACM limit.
- **Final-QC mode**: active once the compiled paper is at or below 8 pages.
  The goal shifts to adversarial quality review, claim/evidence alignment,
  citation integrity, and camera-ready hygiene. Further deletion is forbidden
  unless a later build regresses above 8 pages.

Non-goals: no new experiments without explicit user authorization; no
number/result changes; no scope/claim expansion; no new MCP or tooling unless a
concrete gap is proven.
Prime directive: **when page pressure conflicts with claim integrity, integrity
wins.** A shorter manuscript that changes the evidence tier is a FAILED revision.
In Final-QC mode, quality wins over further compression.

## 2. Authority Stack (highest first)
1. `AGENTS.md` research-safety + no-fabrication rules.
2. Claims ledger `paper/outline_and_claims.md` (numbers/claims/domains/estimands).
3. Doc A (format/8pp/floats), Doc B (narrative/tiers), anti-AI style guide.
4. `paper/length_loop/protection_manifest.json` (machine-enforced claims /
   required / forbidden / caption_locks / hedge_locks / never_delete /
   `table_sources`).
5. Deterministic gates `length_gates.py` (L1-L5) + `round_diff.py` (allowlist).
6. This workflow + `state.json` / `PLAN.md` (runtime).
A deterministic PASS only PERMITS review; **it is never acceptance.**

## 3. Paper Theme Invariant (hard)
This is a guarded chronological **evaluation-discipline** paper on weak
intraday stock direction classification. It is NOT a trading-alpha paper, NOT a
final-model paper, NOT a clean-test / out-of-sample paper, NOT a
model-architecture paper.
Three evidence domains stay separate and named in every empirical sentence:
frozen validation (n=2 seeds) / train-inner control / guarded non-independent walk-forward.

## 4. Live Section Registry
Each round MUST scan `paper/sections/*.tex` (never hardcode a count). Current
live set = 9 section files (`01_intro` … `09_limitations_conclusion`) + the
abstract in `main.tex`. §8 Diagnostics and §9 Limitations are the
highest-protection module: limitations may be compressed only by tightening
prose, never by deleting a caveat.

## 5. Section Contract Matrix
| Section | Task | Forbidden drift | Sim-risk |
|---|---|---|---|
| main abstract | 200-220w calibrated claim | new claim; drop n=2 / near-null / not-clean-test | H |
| §1 Intro | contributions, scope, weak-signal theme | alpha / final-model / clean-test framing | H |
| §2 Related | position literature + difference | new citation without provenance | H |
| §3 Protocol | preserve reproducible method chain | delete split/window/label/criteria detail | L\* |
| §4 Models | model roles + fallback role | fallback as metric-trigger / best-model story | M |
| §5 Setup | bind artifact/run/source | "latest" scan or vague provenance | L |
| §6 Results | frozen validation readout | upgrade to out-of-sample / clean-test | L |
| §7 Guarded | non-independent guarded readout | independent-replication framing | L |
| §8 Diagnostics | boundaries, failure modes, captions | delete limitation / activity-proxy / caption self-containment | L |
| §9 Limitations/Concl. | highest protection | delete any caveat (tighten prose only) | L |

Sim-risk = one-time similarity/template-risk label for the §8.2 Originality lens
(H = template / standard-phrasing concentrates here; spend Triage budget here
first). H = abstract, §1, §2. `L\*` (§3) and M (§4): project-specific overall, but
their standard-method *background sentences* (purge/embargo recital; generic
TCN/DLinear/LightGBM description) are the local H pocket. `anchor_lint.py`
mechanizes the per-paragraph anchor check for the H sections.

## 6. Agent Roles And Isolation (flat; subagents cannot nest)
The MAIN session IS the orchestrator. Per round it spawns role-agents as a flat
sequence and carries state via `runs/<round_id>/`:
- **Reviser** — writes ONLY `runs/<round_id>/candidate_<section>.tex`; never edits
  `paper/sections/*`; never self-certifies. Isolation is **path-convention**, not
  git-worktree (`paper/` is gitignored, so a worktree would not carry it).
  External Codex sessions acting as Revisers MUST follow
  `docs/protocols/lst_models_external_codex_reviser_adapter.md`.
- **Gatekeeper** = the orchestrator running `round_diff.py` (deterministic
  L1-L5 + allowlist + hashes). Not an agent; no semantic judgment.
- **Adversarial reviewers** (read-only) — blind-compare baseline vs candidate via
  the DIFF; do not see reviser rationale; emit blocking/major/minor + line evidence.
- **Synthesizer** (read-only) — ACCEPT / REPAIR / ROLLBACK / STOP.
- **Orchestrator** — the ONLY actor that applies a patch (atomic, with `tmp/`
  backup) and MUST report any out-of-allowlist diff.

## 7. Reviser Resource Routing
- Reviser writing skills: `academic-paper` / `ml-paper-writing` / `nature-polishing`
  — expression only, obey the ledger, may not invent facts or numbers.
- Reviewers: `academic-paper-reviewer` / `ara-rigor-reviewer` / statistical +
  time-series lenses.
- Local tools (tracked under `paper/scripts/` via the `.gitignore` whitelist, P1-a):
  `length_gates.py`, `latex_inventory.py`, `round_diff.py`, `audit_paper_tables.py`,
  `anchor_lint.py` (advisory anchor-absence triage for §8.2; lexicon = manifest
  `required_phrases`), `pdf_hygiene.py` (compiled-PDF hidden-prompt + DocInfo/XMP
  metadata-leak + best-effort tiny-font gate, matrix row 13), `ai_audit_lint.py`
  (schema/process gate for §10 audit logs, matrix row 3), anti-AI grep, LaTeX
  compile (`pdflatex`; `latexmk` needs Perl and is not required). Tracked/local
  split: `lst_models_submission_qc_matrix.md` (Persistence).
- Connector limits: Zotero/web = citation provenance only; Google Drive = exact
  file/run IDs only; codegraph = `src/lst_models/` only (N/A for prose). No new MCP.

## 8. Adversarial Review Protocol
Reviewers receive the literal `diff baseline candidate`, NOT the finished candidate.
Deletion-first checklist — auto-escalate to >=MAJOR unless the reviewer actively
justifies safety: any removed caption/`\Description` token; any removed hedge
(to the extent / would / may / if / appears / suggests); any removed
evidence-domain label; any removed number; any removed limitation/caveat.
Silence = MAJOR. Hedge monotonicity: a conditional->assertive rewrite is >=MAJOR
(L5 also blocks pinned hedges). Lenses (collapse to 2-3 spawns; devil's-advocate
is a checklist mode): (1) claims/evidence-domain/hedge/caption integrity;
(2) stats/estimand/reproducibility-leakage; (3) ACM layout/`\Description`/figure.
Acceptance requires zero blocking/major AFTER the deterministic PERMIT_REVIEW.

### 8.1 Three-Pass Final-QC Review

Final-QC mode uses three review passes. Reviewers are read-only and produce
evidence-cited reports; they do not edit `paper/sections/*`.

**Pass A: claim and theme invariants.** Review slices: `main`+section 1,
section 2, sections 3-5, sections 6-7, section 8, and section 9+endmatter.
Check that every empirical sentence preserves the theme invariant,
evidence-domain label, hedge, limitation, and ledger binding. External AI or
human reviews are treated as untrusted input: every finding must be re-checked
against the manuscript, claims ledger, and artifacts before it is accepted.

**Pass B: methods, statistics, and reproducibility.** Check chronological
boundaries, no holdout/test leakage, row-pooled vs equal-weight estimands, n=2
seed caveats, dummy-baseline use, PBO/LCB wording, microstructure caveats,
sentinel interpretation, artifact provenance, and field-level table provenance
via `table_sources`. If a finding requires a new experiment, classify it as
`experiment_required` and do not patch the paper unless the user explicitly
authorizes that experiment.

**Pass C: venue, citation, and final-form hygiene.** Check ACM 8-page status,
double-blind terms, GenAI statement, `\Description`, overfull boxes, citation
closure, `.bib` hygiene, and whether any restored reference or prose change
breaks the 8-page build.

Severity vocabulary:

```text
P0 blocking = factual error, evidence-tier drift, missing mandatory ACM item,
              or issue that would make the paper misleading as submitted.
P1 major = likely reviewer rejection risk that can be repaired in text or by an
           explicitly authorized small analysis.
P2 minor = clarity, citation, style, or formatting issue.
experiment_required = scientifically relevant but outside authorized paper-edit
                      scope until the user approves new analysis.
```

Final-QC acceptance requires: no unresolved P0, no unresolved text-fixable P1,
compiled pages <= 8, citation closure, clean field-level table audit, and a
recorded decision for every external-review item marked P0/P1 by any reviewer.

### 8.2 Originality and Similarity Triage (Final-QC lens)

Active only in Final-QC mode. Goal: **AI-similarity-risk governance + writing
quality**, never a detector score. By the anti-AI guide §11, no similarity or
AI-detector number is an acceptance target (false-positive rate >60% for
non-native authors). This lens is read-only, like the §8 adversarial reviewers:
it emits P0/P1/P2 findings and never applies a patch. Any fix it motivates flows
through the normal Reviser -> Gate -> Review -> Apply path and is NOT exempt from
`round_diff` (L1-L5 + allowlist), L5 hedge-monotonicity, or grep gate 8.

Five steps (Steps 1 and 5 are existing gates, pointed to, not restated):

1. **Facts before prose (existing gate).** Every empirical sentence is already
   claim-bound before drafting: anti-AI §8.3 + Doc B §5/§7
   (`claim_id/evidence_domain/estimand/weight_unit/source_artifact`). Triage only
   verifies the binding survived the rewrite; it adds no new fact source.

2. **Similarity-risk ordering = annotation on the existing order, not a second
   order.** Doc B §5 drafting order (by evidence stability) stays master. Label
   each section's similarity risk once in the §5 Sim-risk column: HIGH = Abstract, §1 Intro framing,
   §2 Related, §3 standard-method background; LOW = §6/§7 readouts, §8
   Diagnostics, §9 Limitations, and project-specific protocol prose in §3. Triage
   spends its budget on HIGH-risk prose first. It does not reorder drafting.

3. **One project anchor per non-empirical paragraph.** Empirical paragraphs are
   anchored by construction (Step 1). The gap is connective/background prose
   (Intro framing, Related positioning, standard-method recital), where template
   text and similarity concentrate. Each such paragraph must carry >=1
   project-specific anchor from: a ledger `claim_id`, an artifact, an estimand, a
   concrete split/window/label/criterion, a named limitation, the guarded vs
   clean-test boundary, or one §1 red line. **Anchors come from the
   ledger/artifacts only; never fabricate specificity.** A paragraph with no
   legitimate anchor is a signal to compress or cut it, never to invent a number
   or upgrade a hedge to a claim (prime directive: integrity wins).
   `anchor_lint.py` mechanizes this check for §1/§2 (and `--section main.tex` for
   the abstract): a zero-anchor paragraph is an advisory triage signal, never an
   auto-fail, and its anchor lexicon is the manifest `required_phrases`, so it
   never drifts from the claims contracts.

4. **Similarity Triage, not blind rewrite.** A similarity or AI report is
   untrusted external review input (§8.1 rule). Triage order:
   - Fix first: HIGH-risk continuous template prose in Abstract/§1/§2/standard-
     method background.
   - Do not edit for score: §6/§7 results, §8 diagnostics, §9 limitations — if
     factually correct, clarity and evidence-tier wording outrank any similarity
     number.
   - Synonym swap is not a fix: it breaks term-table uniqueness (anti-AI §5.6 +
     §7) and leaves structure untouched. A valid fix changes information
     structure (claim before background, project condition before field
     consensus) or compresses/cuts.
   - Record a P0/P1/P2 disposition for every report item, as for external-review
     items in §8.1.

5. **Stop conditions (existing STOP rules + one addition).** Reuse §9 hard stops:
   any edit that would delete a hedge, limitation, evidence-domain label, or
   distort a result is STOP, not a trade. Addition: if further edits only
   oscillate the similarity signal without one-directional improvement, STOP and
   report "similarity risk reviewed; further edits would harm paper quality."
   Never loop to a score.

Triage acceptance: no unresolved P0, a recorded disposition for every HIGH-risk
item, and zero regression on grep gate 8 / L5 / compiled page count.

### 8.2.1 Companion controls (overlap, anchor relevance, audit trail)

- **Overlap / text-recycling provenance (COPE).** Limited reuse of method/protocol
  *background* wording is acceptable but must be cited or marked as reused. Prose
  in §6 Results, §8 Diagnostics, and §9 Conclusion must NOT be pasted verbatim
  from an earlier draft, an internal doc (ledger, register, protocols), or a prior
  manuscript. Any reused passage records its source in the round's
  `similarity_triage_report.md`. Undisclosed self-overlap is a P1.
- **Anchor relevance (read-only lens).** `anchor_lint.py` proves anchor PRESENCE,
  not relevance; presence is necessary, not sufficient. For each H-risk section
  (§5 Sim-risk = H), a read-only reviewer samples paragraphs the linter passed and
  judges whether the present anchor is load-bearing (a real project claim/condition)
  or decorative (a citation hung on otherwise template prose). Advisory: it emits
  P2 notes, never a mechanical fail, and never forces fabricating a stronger anchor.
- **Audit trail (ICMJE process, not only a statement).** Every Triage round writes
  `runs/<round_id>/ai_use_log.json`, and -- when any similarity/AI report was
  consulted -- `similarity_triage_report.md` (schemas in §10). The GenAI Usage
  Statement in main.tex is the public disclosure; these per-round logs are the
  auditable process behind it.
- **Final consolidation.** Before declaring a build submission-ready, run
  `lst_models_submission_qc_matrix.md` once; every mandatory row must carry a
  recorded PASS/N/A with an evidence pointer.

### 8.3 Whole-Paper Merit / Logic Pass (Final-QC lens)

Active only in Final-QC mode after deterministic gates have permitted review.
This pass asks whether the paper is persuasive and scoped as a paper; it does
not re-prove candidate integrity, bypass §6, or decide submission readiness.

Use `academic-paper-reviewer` and `ara-rigor-reviewer` as independent read-only
lenses when available. If a tool is unavailable, the reviewer must answer the
same checklist explicitly. Each finding must include:

```text
section_anchor:
claim_id:
evidence_domain: official-validation | train-inner | guarded | mixed/unclear
evidence_level: artifact-backed | citation-backed | manuscript-consistency |
                reviewer-judgment | needs-human-confirmation
interpretation_strength: proven_by_artifact | supported_but_interpretive |
                         reviewer_judgment_only | needs_human_confirmation
manifest_ids: D* required hedge ids and/or F* cannot-prove ids, when relevant
severity: P0 | P1 | P2 | experiment_required
recommended_route: ACCEPT | REPAIR | ROLLBACK | STOP | HUMAN_CONFIRMATION
```

Checklist:

1. Does the whole-paper through-line make the contribution clear without
   overstating guarded non-independent evidence?
2. Does each central claim stay within artifact and citation support, with no
   clean-test, out-of-sample, final-model, profitability, or SOTA implication?
3. Are official-validation, train-inner, and guarded evidence domains separated
   in the abstract, results, diagnostics, limitations, and conclusion?
4. What would a skeptical finance/ML reviewer attack first, and is the answer
   already in the manuscript, or should the claim be softened?
5. Which issues are text-repairable under existing evidence, which require new
   analysis, and which require human/advisor judgment?

The pass emits findings only. The §6 Synthesizer maps them to the existing
ACCEPT / REPAIR / ROLLBACK / STOP states. A reviewer-judgment finding cannot be
treated as artifact-backed evidence, and this pass cannot declare the paper
submission-ready.

### 8.4 Hedge De-duplication (thin-to-floor) — dedup is not deletion

Active once the r048 governance patch (per-scope `floors` / `required_groups` in
`protection_manifest.json` + `gate_L2` classification) has landed. Resolves the
conflict between the §8 deletion-first checklist and legitimate redundancy
removal.

The deterministic L2 gate now classifies every required-phrase change per
declared scope as `dedup_ok` (a redundant restatement removed, every declared
floor still met), `floor_breach` (the last required instance in a scope removed),
or `floor_unbound` (a declared floor whose phrase has no live hit — a config
error, not a candidate error). The §8 adversarial reviewer **reads this
classification**:

- When L2 reports **`dedup_ok`** for a phrase `D*` (and no `floor_breach` /
  `floor_unbound`), removing the redundant restatement(s) is **permitted and at
  most MINOR** — the "removed hedge → ≥MAJOR" escalation does NOT fire and no
  per-instance safety justification is required. The reviewer's only residual
  check is that the surviving instance is the load-bearing one (the reviser's
  declared `canonical_kept`).
- Escalation to **≥MAJOR/STOP** is reserved for: (i) `floor_breach`;
  (ii) `floor_unbound`; (iii) an L5 hedge-monotonicity strip (a *surviving*
  instance reworded conditional→assertive); or (iv) a forbidden F-term turned
  affirmative.

The reviser MUST declare, in `PLAN.md`, a `hedge_dedup` block per touched `D*`
(id, floors, before/after hits by scope, `canonical_kept` quote+`file:line`,
`monotonicity_preserved`). Floors are per-scope and may pin several scopes at
once (e.g. D1 = main.tex + §6 + §7 + §8 + §9); `required_groups` pin multiple
clauses that must each survive (e.g. D16 weak-bar AND 5/7-descriptive). A
`floor_unbound` result blocks the round until the caveat is added to that scope
or the floor is corrected — it is never silently passed. The full per-D-lock
floor map and its audit live in
`docs/protocols/lst_models_hedge_dedup_floors_design.md`.

## 9. Length-Loop State Machine + Stop Rules
One round = one section = one atomic apply:
`FREEZE -> PLAN(allowlist) -> CANDIDATE(reviser->runs/) -> GATE(round_diff:
L1-L5 + allowlist + hashes) -> [BLOCK? REPAIR <=2] -> L4_REVIEW(diff panel) ->
SYNTH -> APPLY(atomic + tmp backup) -> COMPILE(pdflatex; fresh PDF page-object
count) -> VERIFY(post-apply sha + page delta) -> record in state.json.`
Phase enum per section: `pending | frozen | candidate | gated | reviewed |
applied | verified | reverted`.
Resume: recompute live sha vs `state.json`; if `applied` and sha matches -> skip
re-apply; if `gated` and not applied -> reuse `gate_report.json`.
Macro passes (<=3): Pass1 high-redundancy sections (§8/§3/§6/§1); Pass2 repair
L4 majors + global tighten; Pass3 layout-only + whole-paper re-review.
Hard stops: <=2 repairs/section; <=10 candidates total; same MAJOR twice -> STOP;
reaching 8pp would require deleting a limitation/hedge/domain-label/core claim ->
STOP; safe cuts exhausted but still >8pp -> report residual page gap, do not
sacrifice the scientific boundary.

In Final-QC mode, one review round may cover multiple slices but one apply still
uses one patch plan. Text changes follow the same candidate/gate/review/apply
discipline when they touch manuscript content. Pure review reports may be
written directly to `runs/<round_id>/review_report.md`; they cannot modify the
manuscript.

## 10. Reports & Evidence
Each round writes `runs/<round_id>/`: `PLAN.md` (intent + allowlist),
`candidate_<section>.tex`, `gate_report.json` (hashes + L1-L5 + allowlist +
verdict), `review_report.md` (L4), and a decision line. The final report MUST
include a scope-drift check (what changed outside the allowed region) and the
fresh PDF page count by BOTH methods (latexmk/pdflatex log + PDF page-object count).

In Final-QC Originality / Similarity Triage rounds (§8.2), the round also writes
`ai_use_log.json` and, when a similarity/AI report was consulted,
`similarity_triage_report.md`. These make AI use auditable behind the public
GenAI Usage Statement (ICMJE process requirement); `lst_models_submission_qc_matrix.md`
confirms the accepted round carries a complete log. Run `paper/scripts/ai_audit_lint.py`
on the accepted round before filling matrix row 3; the lint is a schema/process
gate and never records a detector score as an acceptance target.

`ai_use_log.json` schema (one object per round):

```json
{
  "round_id": "r0NN",
  "mode": "final_qc_similarity_triage",
  "tools": ["anchor_lint.py", "<similarity/AI tool, or none>"],
  "input_scope": ["sections/01_intro.tex", "main.tex"],
  "edits": [
    {"region": "#body", "motivation": "template/overlap reduction | clarity | ...",
     "from_external_report": true, "human_disposition": "accept|reject|modify",
     "severity": "P0|P1|P2|none", "applied": true}
  ],
  "anchor_lint": {"anchor_absent_count": 0, "sections": ["sections/01_intro.tex"]},
  "overlap_provenance": [{"passage": "<short id>", "source": "<cite|doc|none>"}],
  "hashes": {"candidate_sha256": "...", "manifest_sha256": "..."},
  "note": "similarity score is NOT an acceptance target (anti-AI §11)."
}
```

`similarity_triage_report.md` is the short human-readable companion: which report
was consulted, which high-risk passages it flagged, the disposition of each (fixed
by restructuring / cut / kept-as-correct), and any P0/P1 raised. No detector score
is recorded as a target.

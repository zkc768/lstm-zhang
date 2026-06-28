# lst_models Submission QC Matrix (final pre-submission gate)
<!-- DOC_VERSION: v1.2 / 2026-06-23 -->

Status: long-term protocol. One consolidated, checklist-style gate run ONCE before
an ICAIF build is declared submission-ready. It does NOT replace the per-round
controls in `lst_models_paper_revision_workflow.md` (§8 review, §8.2 Originality /
Similarity Triage, L1-L5 gates); it is the final matrix confirming that every
requirement scattered across Doc A / Doc B / the anti-AI guide / the revision
workflow has a recorded status. Subordinate to AGENTS.md, the claims ledger, and
the three paper contracts (authority stack: revision workflow §2).

Standards mapped (external, ADVISORY -- they inform items, they are never
acceptance authorities above the project contracts): ICMJE (AI use by authors;
reporting), ACM (authorship / GenAI disclosure), COPE (text recycling),
NeurIPS-style reproducibility / limitations / data-availability checklist culture,
and the 2025 hidden-prompt peer-review-integrity findings (arXiv:2507.06185;
ICML'25 accepted-paper cases). An external checklist item never overrides a
project red line or forces a claim the ledger cannot support (revision §8.1: such
input is untrusted).

How to use: every row gets a status -- PASS / FAIL / N/A / TODO -- with a one-line
evidence pointer (artifact path, gate output, file:line, or run id). A FAIL, or an
unrecorded mandatory row, blocks "submission-ready." This is NOT a detector-score
gate: by anti-AI §11 no similarity / AI-detector number is an acceptance target.

## Matrix

| # | Item | Standard | Gate / evidence | Status |
|---|---|---|---|---|
| 1 | GenAI Usage Statement present + accurate | ACM, ICMJE | `paper/main.tex:118`--124; manifest never-delete binding | PASS |
| 2 | AI is not an author; named humans accountable for accuracy / integrity / originality | ICMJE, ACM, COPE | Anonymous build omits authors (`paper/main.tex:43`) and keeps the GenAI accountability statement (`paper/main.tex:118`--124); this matrix records process sign-off | PASS |
| 3 | Per-round AI-use + similarity-triage audit log | ICMJE (process, not only a statement) | `ai_audit_lint.py` CLEAN on `r011_abstract_posthoc_closure`, `r012_abstract_largecap_repair`, and accepted AI-process round `r013_sec01_final_qc_similarity`; r014--r025 were ordinary reviewer-response/prose/layout rounds with no external similarity/AI report consulted | PASS |
| 4 | Citation provenance: every `\cite` in references.bib with provenance; no AI-generated cites | anti-AI §3 | `paper/length_loop/runs/r026_submission_package_qc/citation_closure.json`: 40 cited keys, `cited_not_in_bib=[]`; `references.bib` carries provenance comments | PASS |
| 5 | Text-recycling / overlap provenance | COPE | `r013_sec01_final_qc_similarity/ai_use_log.json` + `similarity_triage_report.md`; no detector/similarity score used as an acceptance target; no Results/Discussion/Conclusion paste accepted | PASS |
| 6 | Anchor triage (absence + relevance) | revision §8.2 | `paper/length_loop/runs/r026_submission_package_qc/anchor_lint_report.json`: 0 anchor-absent paragraphs over §1/§2; final whole-paper lens recorded in `r026_submission_package_qc/review_report.md` | PASS |
| 7 | Numeric consistency (no fabricated / lost numbers) | -- | `paper/length_loop/runs/r026_submission_package_qc/table_audit.json`: 34/34 PASS; `gate_selftest.py`: 11/11; current `latex_inventory.py --paper`: 419 numeric tokens | PASS |
| 8 | Abstract <-> body claim consistency | claims ledger | Final whole-paper lens recorded in `r026_submission_package_qc/review_report.md`; current `latex_inventory.py --paper` shows live body state used for the sign-off | PASS |
| 9 | Three evidence domains never mixed | Doc B / manifest D22 | Manifest D22 present; final whole-paper lens in `r026_submission_package_qc/review_report.md`; current prose keeps validation, train-inner control, and guarded non-independent domains separate | PASS |
| 10 | Table field-level provenance audit clean | -- | `paper/length_loop/runs/r026_submission_package_qc/table_audit.json`: 34/34 PASS | PASS |
| 11 | 8-page ACM sigconf compile (no appendix) | Doc A | Current `paper/main.pdf`: 8 pages by r026 `pdflatex` x2 and PDFInfo (`r026_submission_package_qc/pdf_page_count.json`); blocking `main.log` grep clean after r026 compile | PASS |
| 12 | Double-blind: no author identity in body / acks / refs | Doc A, ACM | Doc A identity-token grep (`zkc768|lstm-zhang|kevinzhang|gmail|154SlcH3nViUcvPXFBM|google drive|colab`) over `main.tex`, sections, and `references.bib`: no hits; acknowledgments removed in anonymous build | PASS |
| 13 | PDF hygiene: no hidden / white / tiny-font text; no injection trigger phrases; metadata scrubbed | arXiv:2507.06185, ICML'25 | `pdf_hygiene.py`: text-layer trigger scan + DocInfo/XMP leak + best-effort tiny-font (`pypdf` visitor or Poppler bbox fallback) | PASS on current build; re-run after every compile |
| 14 | Data / code availability statement with access constraints | NeurIPS, ICMJE | Anonymous review build disposition: deferred to camera-ready because raw-data Drive/access details and artifact host details can identify the project; if the submission portal requires a statement, use an anonymized availability statement outside the PDF | N/A (anonymous review build; deferred to camera-ready) |
| 15 | Limitations completeness (mandatory list) | NeurIPS, register | §9 records n=2 seeds, single-market / five-large-cap-survivor scope, frozen band+horizon without sensitivity scan, macro-F1 not economic value, Roll(1984) microstructure risk, and guarded not-clean-test boundary (`paper/sections/09_limitations_conclusion.tex`) | PASS |
| 16 | Pre-registration <-> prose alignment | pre-reg (project) | `configs/stages/v2_1_guarded_walkforward_readout.yaml::predeclared_criteria`, `docs/protocols/v2_1_conditional_predictability_preregistration.md`, and §§3/7/8 prose align with predeclared validation/guarded claims | PASS |
| 17 | Conflict-of-interest / funding disclosure | ICMJE | Anonymous review build disposition: deferred to camera-ready; rendering COI/funding/none statements in the blind PDF risks deanonymization and is therefore intentionally absent at review stage | N/A (anonymous review build; deferred to camera-ready) |

Known current state (status source = the matrix row above; details only):
- Row 3: `ai_audit_lint.py` now mechanizes the revision §10 schema. The accepted
  AI-process / similarity-triage round is `r013_sec01_final_qc_similarity`;
  `r011`, `r012`, and `r013` lint CLEAN. Rounds `r014`--`r025` are ordinary
  reviewer-response/prose/layout rounds, not similarity-report rounds.
- Row 6: `anchor_lint.py` clean on §1/§2 (0 anchor-absent, lexicon 214);
  relevance sign-off is recorded in `r026_submission_package_qc/review_report.md`.
- Row 13: `pdf_hygiene.py` runs under the project Python with a `pypdf` backend
  when installed, otherwise Poppler `pdftotext`/`pdfinfo` + bbox tiny-font
  estimate. Current `paper/main.pdf` was CLEAN with backend=`poppler-cli`
  (0 triggers, 0 metadata leaks, 0 identity-token hits, 0 tiny-font spans).
  Re-scan after every recompile.
- Rows 14 / 17: intentionally absent from the anonymous review PDF and explicitly
  deferred to camera-ready. Do not render identifying data-availability, COI, or
  funding details in the blind build unless the venue supplies an anonymous
  statement field.

## Persistence and reproducibility (P1-a)

Tracked vs local-only is deliberate but must be stated, not assumed:
- TRACKED (`docs/`): the three paper contracts, this matrix, and
  `lst_models_paper_revision_workflow.md`. The revision workflow is currently
  UNTRACKED (`??`); it must be `git add`-ed to persist for other clones / agents.
- LOCAL-ONLY (gitignored under `paper/`): `paper/length_loop/*`,
  `paper/sections/*`, `paper/main.tex`, `paper/references.bib`, drafts, and runs.
  (The gate toolchain `paper/scripts/*.py` is now TRACKED -- see RESOLVED below.)
- RESOLVED (P1-a, user decision): option (a). `.gitignore` now whitelists the
  gate toolchain (`paper/*` + `!paper/scripts/` + `paper/scripts/*` +
  `!paper/scripts/*.py`), so the 13 `paper/scripts/*.py` tools are tracked-eligible
  while drafts, sections, length_loop runs, and references stay local-only
  (verified: `git add -n paper/` exposes only `paper/scripts/*.py`, no draft/run
  content). Staging/committing the scripts -- and this matrix and the revision
  workflow, both still `??` -- is the user's `git add` to make.

## Audit-log binding (P1-b)

Row 3 is satisfied by the per-round audit artifacts whose schema lives in revision
workflow §10. This matrix is the final confirmation that at least the accepted
round wrote a complete `ai_use_log.json` (tool, input scope, edit motivation,
human disposition, severity, applied?) and, if any similarity / AI report was
consulted, a `similarity_triage_report.md`. No detector score is recorded as a
target.

## Maintenance

Subordinate to the three paper contracts; bump DOC_VERSION +0.1 per substantive
change. New rows must name a standard or project contract and a concrete gate /
evidence pointer -- never a vague aspiration.

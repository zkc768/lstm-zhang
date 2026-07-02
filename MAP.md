# MAP.md — lst_models navigation index

> **What this is.** A one-hop index: find the *current-truth* file for any topic, and stay out
> of stale or generated noise. **This file carries no authoritative facts, numbers, or
> decisions — it only points.** Truth lives in the files it links to. Precedence is always
> `AGENTS.md` first; if this map ever disagrees with `AGENTS.md`, `AGENTS.md` wins. Keep every
> entry a pointer; never copy a number or a claim into this file (that is how duplicates drift).

## 0. Start here — governance precedence

Read top-to-bottom; each level overrides the ones below it on any conflict.

1. **[AGENTS.md](AGENTS.md)** — the authoritative contract: research safety, no fabrication,
   route + structural rules. Its **§2 Required Reading** and **§3 Route Contract** are the real
   navigation spec; this map only mirrors them. (§12 is the codegraph audit rule.)
2. **Claims ledger — [paper/outline_and_claims.md](paper/outline_and_claims.md)** — the single
   fact source for every paper number/claim. The three evidence domains (official validation
   n=2, train-inner control, guarded non-independent walk-forward) are never fused in one claim.
3. **Red lines** — banned vocabulary + no-model-selected rules: [.claude/CLAUDE.md](.claude/CLAUDE.md) §3 and AGENTS §6.
4. **Anti-AI style guide (8 grep gates)** — [docs/lst_models_paper_translation_and_anti_ai_style_guide.md](docs/lst_models_paper_translation_and_anti_ai_style_guide.md).

## 1. Canonical vs working — the important distinction

The repo mixes **canonical** docs (current truth, git-tracked, whitelisted in `.gitignore`) with
**working** docs (dated handoffs, superseded plans, local drafts — gitignored). When exploring,
**trust canonical first**; treat working docs as history unless you verify them against canonical.

**Canonical docs** (the `.gitignore` whitelist — everything else under `docs/` is working/ad-hoc):

- [docs/lst_models_code_style_and_route_guide.md](docs/lst_models_code_style_and_route_guide.md) — where code goes (file-placement source of truth)
- [docs/agent_capabilities_and_skill_routing.md](docs/agent_capabilities_and_skill_routing.md) — skills / MCP routing layer
- [docs/lst_models_paper_narrative_and_template_papers_guide.md](docs/lst_models_paper_narrative_and_template_papers_guide.md) — paper narrative
- [docs/lst_models_paper_format_and_figures_contract.md](docs/lst_models_paper_format_and_figures_contract.md) — figures / format contract
- [docs/lst_models_paper_translation_and_anti_ai_style_guide.md](docs/lst_models_paper_translation_and_anti_ai_style_guide.md) — anti-AI gates
- [docs/lst_models_google_drive_raw_data_guide.md](docs/lst_models_google_drive_raw_data_guide.md) — raw-data access
- [docs/adr/](docs/adr) — accepted decisions (esp. [0003 v2 source-of-truth & promotion](docs/adr/0003-v2-source-of-truth-and-promotion.md))
- [docs/protocols/](docs/protocols) — per-stage protocols (00–06 + v2.1 sidecars)

**Working / not canonical** (gitignored; may be superseded — verify before relying):
`docs/*_implementation_plan.md`, `docs/*_plan.md`, `docs/lst_models_v2_route_roadmap.md`,
`docs/v2_1_*_2026*.md` (dated review/handoff), root `tmp_*.txt`, `paper_compare/*baseline*`.

## 2. The pipeline at a glance

Route contract: **[AGENTS.md §3](AGENTS.md)**. Each executable stage aligns **by number** across
four surfaces: protocol (`docs/protocols/NN_*`), config (`configs/stages/`), code entry
(`src/lst_models/stages/`), and one user-facing notebook (`notebooks/`).

| Stage | Protocol (`docs/protocols/`) | Code entry (`src/lst_models/stages/`) |
|---|---|---|
| 00 data_split_label_freeze | `00_data_split_label_freeze_protocol.md` | `data_split_label_freeze.py` |
| 01 feature_window_search | `01_feature_window_search_protocol.md` | `feature_window_search.py` |
| 02 model_hpo_train_inner | `02_model_hpo_train_inner_protocol.md` | `model_hpo_train_inner.py` |
| 03 frozen_validation_readout | `03_frozen_validation_readout_protocol.md` | `frozen_validation_readout.py` |
| 04 diagnostics_ablation | `04_diagnostics_ablation_protocol.md` | `diagnostics_ablation.py` |
| 05 thesis_synthesis | `05_thesis_synthesis_protocol.md` | `thesis_synthesis.py` |
| 06 ian_final_progress_record | `06_ian_final_progress_record_protocol.md` | `ian_final_progress_record.py` |
| **V2.1 guarded walk-forward** (measure-only branch off Stage 04) | `v2_1_guarded_walkforward_readout_protocol.md` | `guarded_walkforward_readout.py` + [`guarded_walkforward.py`](src/lst_models/guarded_walkforward.py) |

Each stage also has a config in `configs/stages/` (AGENTS §3 contract). V2.1 config: `configs/stages/v2_1_guarded_walkforward_readout.yaml`.

## 3. Code map — [src/lst_models/](src/lst_models)

- **Core modules** (reusable logic; never inline in notebooks): `config` `data` `features`
  `labels` `windows` `splits` `fitting` `metrics` `diagnostics` `synthesis`
  `guarded_walkforward` `artifacts` `device`.
- **Models** — [models/](src/lst_models/models): `last_step_mlp` `standard_dlinear`
  `ms_dlinear_only` `ms_dlinear_tcn` `tcn`.
- HPO search ranges → `configs/models/<model>/search_space.yaml`; frozen params →
  `configs/frozen_params/<stage>/`. Public entry per stage: `run_stage(config)`.
- Tests → [tests/](tests) (contracts · data · stages · notebooks).

## 4. Paper map — [paper/](paper)  (local-only; gitignored except `paper/scripts/`)

- **Fact source**: [paper/outline_and_claims.md](paper/outline_and_claims.md) (claims ledger — every number binds here)
- Body: [paper/main.tex](paper/main.tex) + [paper/sections/](paper/sections) (`01_intro` … `09_limitations_conclusion`)
- Refs: [paper/references.bib](paper/references.bib) · Build output: `paper/main.pdf`
- **Master workflow**: [paper_compare/PAPER_WORKFLOW.md](paper_compare/PAPER_WORKFLOW.md) — start here to draft/revise
- **Style playbook**: [paper_compare/exemplars/playbook/README.md](paper_compare/exemplars/playbook/README.md) — pull only 1–2 relevant files; imitate structure/logic, never copy text
- QC gates: `paper/scripts/*.py`, `paper_compare/check_integrity.py`, `paper_compare/validate_citations.py`
- **Rebuttal prep**: [paper/rebuttal_prep.md](paper/rebuttal_prep.md) — reviewer-rebuttal preparation (prepared answers + evidence paths)

## 5. Where NOT to look — search hygiene

Generated / bundled / local noise. Exclude from Grep/Glob unless a task specifically needs it:

`tmp/` · `artifacts/` (~77M outputs) · `results/` · `.claude/skills/` (373 bundled skill-reference
`.md`, not this project) · `__pycache__/` `*.pyc` · `paper/main.{pdf,docx,log,aux,fls,bbl}` ·
`*.zip` · LaTeX build byproducts (`*.aux *.blg *.fls *.fdb_latexmk *.out`).

## 6. Sibling working directories

- `E:\codex_workspace\projects\hf_stock_ml_references2\papers` — reference library (currently a README only).
- `E:\claude-workspace\projects\lstm_model` — **an older (May) structure with its own `CLAUDE.md`
  and ~849M `data/`; NOT the current project.** Do not treat as canonical, and do not split
  governance into it — the single-fact-source rule keeps AGENTS.md, the ledger, and the paper in
  this one repo.

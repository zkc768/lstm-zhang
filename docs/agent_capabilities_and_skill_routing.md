# Agent Capabilities And Skill Routing

Status: project routing guide.

Scope: `lst_models` agent behavior only. This document records the useful
local skills, plugins, and MCP-style tools observed for this workspace and how
agents should select them. It does not install skills, copy skill source into
this repository, change notebook execution, or authorize heavy training.

Snapshot date: 2026-06-09.

## 1. Operating Rule

Skills and MCP tools are global or connector-level capabilities. They are not
project source files. Do not vendor their implementation into this repository.
Instead, use this file as the project-local routing layer:

1. Read `AGENTS.md` and `docs/lst_models_code_style_and_route_guide.md`.
2. If the user request touches skills, MCP, agent workflow, research review,
   literature search, paper writing, external connectors, or multi-perspective
   review, read this file.
3. Select the smallest useful set of skills or tools for the task.
4. Project safety rules override every skill or tool suggestion.
5. Do not use external connectors as evidence without exact file IDs, URLs,
   message IDs, document IDs, or local paths.

## 2. High-Value Skills For This Project

These are the skills that are most useful for the `lst_models` route.

| Task type | Prefer these skills | Use when |
|---|---|---|
| Multi-step implementation planning | `writing-plans`, `brainstorming` | Designing a new stage, changing route behavior, adding model or artifact logic. |
| Bug or test failure diagnosis | `systematic-debugging` | Any failing test, notebook error, runtime traceback, or unexpected behavior. |
| Completion checks | `verification-before-completion` | Before claiming a code, notebook, config, or doc change is complete. |
| Python code quality | `python-expert-best-practices-code-review` | Writing or reviewing Python under `src/lst_models/` or tests. |
| Pytest work | `python-testing`, `pytest-testing` | Adding, repairing, or explaining tests. |
| Notebook safety review | `notebook-code-reviewer` | Reviewing `.ipynb` structure, leakage risk, hidden state, or static gates. |
| Time-series ML | `time-series-analysis`, `aeon` | Chronological split, windowing, forecasting-style validation, time-series model comparison. |
| Deep learning | `deep-learning-pytorch` | PyTorch model code, CUDA/CPU resolution, sequence models, tensor/device behavior. |
| Statistics and metrics | `statistical-analysis` | Metric interpretation, confidence intervals, ablation comparisons, significance checks. |
| Data inspection | `exploratory-data-analysis` | Inspecting data files or artifact tables without running heavy training. |
| Figures | `figure-generation`, `nature-figure` | Creating or auditing research figures and thesis-ready plots. |
| Spreadsheet artifacts | `xlsx`, `spreadsheets:Spreadsheets` | `.xlsx`, `.csv`, `.tsv`, table cleanup, validation tables, Google Sheets-ready workbooks. |
| Literature search | `arxiv`, `deep-research`, `firecrawl-research-papers`, `nature-academic-search` | Finding, screening, and citing papers. |
| Academic writing | `academic-paper`, `academic-paper-reviewer`, `academic-pipeline`, `ml-paper-writing` | Drafting, reviewing, or revising thesis/paper sections from authorized evidence. |
| Nature-style outputs | `nature-writing`, `nature-polishing`, `nature-reviewer`, `nature-citation`, `nature-data`, `nature-response`, `nature-reader`, `nature-paper2ppt` | High-impact journal style drafting, review, citation, data statements, responses, or slide decks. |
| Research rigor | `ara-rigor-reviewer`, `ara-research-manager` | Epistemic review, provenance notes, claim calibration, end-of-session research memory. |
| External repo inspection | `github-repo-miner` | Mining another GitHub ML repo for architecture, trainer, dataset, or metrics patterns. |
| Project retrospectives | `codex-error-retrospective` | Repeated Codex/tool failures or user-requested error retrospectives. |

## 3. Available Skill Inventory

Observed local or plugin skills include:

- System and project workflow: `imagegen`, `openai-docs`, `plugin-creator`,
  `skill-creator`, `skill-installer`, `find-skills`, `writing-plans`,
  `executing-plans`, `verification-before-completion`, `systematic-debugging`,
  `codex-error-retrospective`, `cli-anything`.
- Python, tests, notebooks, data, and ML: `python-testing`, `pytest-testing`,
  `python-expert-best-practices-code-review`, `notebook-code-reviewer`,
  `documenting-python-libraries`, `exploratory-data-analysis`,
  `statistical-analysis`, `time-series-analysis`, `aeon`,
  `deep-learning-pytorch`, `pytorch-ml-utils-builder`, `figure-generation`,
  `xlsx`, `spreadsheets:Spreadsheets`.
- Research and academic writing: `academic-paper`,
  `academic-paper-reviewer`, `academic-pipeline`, `deep-research`,
  `brainstorming-research-ideas`, `arxiv`, `firecrawl-research-papers`,
  `ml-paper-writing`, `nature-academic-search`, `nature-citation`,
  `nature-data`, `nature-figure`, `nature-paper2ppt`, `nature-polishing`,
  `nature-reader`, `nature-response`, `nature-reviewer`, `nature-writing`,
  `quality-editor`, `ara-research-manager`, `ara-rigor-reviewer`,
  `autoresearch`.
- UI, browser, and frontend: `browser:control-in-app-browser`,
  `chrome:control-chrome`, `computer-use:computer-use`, `impeccable`,
  `playwright-skill`, `playwright-trace`.
- Connected apps and repositories: `github:github`,
  `github:gh-address-comments`, `github:gh-fix-ci`, `github:yeet`,
  `gmail:gmail`, `gmail:gmail-inbox-triage`, `google-drive:google-drive`,
  `google-drive:google-docs`, `google-drive:google-sheets`,
  `google-drive:google-slides`, `google-drive:google-drive-comments`,
  `zotero:Zotero`.
- Hugging Face: `hugging-face:hf-cli`, `hugging-face:huggingface-datasets`,
  `hugging-face:huggingface-papers`,
  `hugging-face:huggingface-paper-publisher`,
  `hugging-face:huggingface-community-evals`,
  `hugging-face:huggingface-gradio`, `hugging-face:huggingface-jobs`,
  `hugging-face:huggingface-llm-trainer`,
  `hugging-face:huggingface-vision-trainer`,
  `hugging-face:huggingface-trackio`, `hugging-face:transformers-js`.
- Prompting and optimization: `arize-prompt-optimization`.
- Presentations and documents: `documents:documents`,
  `presentations:Presentations`.

This inventory is a routing snapshot, not a promise that every skill is relevant
to every task. Prefer the high-value shortlist above.

## 4. MCP And Connector Routing

Available tool families that can help this project:

| Tool family | Use for | Project rule |
|---|---|---|
| `mcp__codegraph` | Code structure, dependency, complexity, impact, and dataflow queries when a graph is built. | If no graph exists or results are stale, fall back to `rg`, file reads, and targeted tests. |
| `mcp__codex_apps__google_drive` | Google Drive, Docs, Sheets, and Slides search/read/edit/export. | Use exact Drive file IDs or URLs where possible. For raw data tasks, also read `docs/lst_models_google_drive_raw_data_guide.md` and `configs/lst_models_data.yaml`. |
| `mcp__codex_apps__gmail` | Gmail search, triage, summaries, drafts, replies, labels, and forwarding. | Use only when the user asks for email/mailbox work. |
| `codex_app` deferred tools | Automations, reminders, thread creation, thread reading, handoff, pin/archive/title updates. | Use only when the user asks for automations or thread management. |
| `tool_search` | Discover deferred tools before saying a capability is unavailable. | Prefer this for plugin/MCP discovery instead of guessing. |
| `web` | Current external facts, changing docs, news, laws, prices, model/API documentation, and source citations. | Browse when facts may have changed or when the user asks for sources; do not use web search to replace local repo inspection. |

Non-MCP but useful capabilities:

- `image_gen`: create or edit raster visuals when a figure, mockup, or image is
  explicitly needed.
- Browser and Chrome plugin skills: use for local web targets or logged-in
  browser state only when relevant.

## 4.1 Codegraph Structural Audit Gate

`mcp__codegraph` is for code-structure review. Use it to keep `src/lst_models/`
small, acyclic, and easy to reason about. It should influence placement and
refactor decisions, but it must not override `AGENTS.md`, protocol docs,
chronology rules, artifact contracts, or tests.

Run codegraph for non-trivial Python work:

- three or more touched Python modules under `src/lst_models/`
- new or moved reusable helper modules
- `run_stage(config)` or stage entry point changes
- shared data, split, label, feature, window, metric, artifact, checkpoint, or
  GPU/device logic
- import-boundary changes, module movement, or refactors before push

Recommended queries:

| Need | Tool |
|---|---|
| Detect circular imports/dependencies | `find_cycles` |
| Avoid duplicate helper creation | `semantic_search` |
| Understand callers/callees before editing | `context` |
| Check whether two modules are coupled | `path` |
| Summarize structural impact across refs | `branch_compare` |

If codegraph cannot run because no database exists, the graph is stale, or the
tool errors, report the exact failure. Then use fallback inspection: `rg`,
direct file reads, `py_compile`, targeted pytest, notebook static gates, and
artifact-contract tests. Do not claim codegraph was run if it failed.

## 5. Stage-Specific Routing

| Stage or workstream | Recommended skills/tools |
|---|---|
| Stage 00 data split and label freeze | `time-series-analysis`, `statistical-analysis`, `notebook-code-reviewer`, `google-drive:google-drive`, `mcp__codex_apps__google_drive`. |
| Stage 01 feature and window search | `time-series-analysis`, `aeon`, `statistical-analysis`, `notebook-code-reviewer`, `python-testing`. |
| Stage 02 model HPO and train-inner | `deep-learning-pytorch`, `aeon`, `statistical-analysis`, `python-expert-best-practices-code-review`, `python-testing`, `verification-before-completion`. |
| Stage 03 frozen validation readout | `statistical-analysis`, `notebook-code-reviewer`, `figure-generation`, `ara-rigor-reviewer`. |
| Stage 04 diagnostics and ablation | `statistical-analysis`, `figure-generation`, `nature-figure`, `ara-rigor-reviewer`. |
| Stage 05 thesis synthesis | `ml-paper-writing`, `academic-paper`, `nature-writing`, `nature-polishing`, `nature-citation`, `figure-generation`. |
| Stage 06 final progress record | `academic-paper-reviewer`, `ara-research-manager`, `verification-before-completion`, `google-drive:google-drive` when exporting or backing up deliverables. |

## 6. Guardrails

- Do not run heavy training because a skill recommends it. Heavy training still
  needs explicit user authorization.
- Do not read or summarize holdout/test data in validation-only work.
- Do not install dependencies or skills unless the user explicitly asks.
- Do not commit, push, create branches, or create pull requests unless the user
  explicitly asks.
- Do not use Gmail, Google Drive, GitHub, Chrome, or web search for private or
  external data unless the task requires it.
- Do not add generic plugin registries, trainer frameworks, or broad utility
  layers to satisfy a skill workflow.
- Always report exact missing paths, file IDs, commit IDs, or message IDs when
  a connector or skill cannot proceed.


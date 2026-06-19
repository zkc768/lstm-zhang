# AGENTS.md - lst_models V2 route
<!-- AGENTS_VERSION: v1.9-anti-spaghetti-structural-gates -->

This is a compact Colab-first research project for the V2 `lst_models` route.
It is not a backend project, not a general ML framework, and not a place to
recreate the large historical project surface.

## 1. Project Identity

- Project: `lst_models`.
- Parent research context: intraday stock direction classification using
  chronological validation.
- Default execution surface: Colab `.ipynb` notebooks.
- User workflow: one user-facing notebook per stage; sidecar files are created
  or updated by agents in the same implementation task.
- Default Colab bootstrap: clone this repo from GitHub at an exact commit,
  then add `src/` to `sys.path`. Zip upload is fallback only.
- Canonical Python package path: `src/lst_models/`.
- Canonical style guide:
  `docs/lst_models_code_style_and_route_guide.md`.
- Canonical route shape: one notebook + one protocol doc + one config file per
  stage, with small reusable Python helpers only when the logic is reused,
  safety-critical, or testable.

## 2. Required Reading Before Code

For any task that creates or modifies `lst_models` code, notebooks, configs,
protocol docs, tests, or artifacts, read these files before producing code:

1. this `AGENTS.md`
2. `docs/lst_models_code_style_and_route_guide.md`
3. the target stage protocol doc, if it exists
4. the target notebook, config, Python module, or test

Do not produce code until the response or working notes include a placement
decision with these fields:

```text
placement_decision:
  target_file_type: <notebook|stage_config|model_search_space|python_module|test|protocol|artifact>
  target_path: <exact intended path>
  guide_sections: ["Where Code Goes", "Code File Types And Common Function Placement"]
  why_not_notebook: <required when creating Python helper code>
  why_not_utils: <required when creating Python helper code>
  safety_tests: <target tests or "not applicable">
```

If the implementer cannot fill this block, stop and update or create the
technical design/protocol first. Do not guess a file location.

If `docs/lst_models_code_style_and_route_guide.md` is missing, stop and report
that exact missing path before creating or editing stage code.

For tasks that mention skills, MCP, connectors, agent workflow, literature
search, paper writing, external apps, multi-perspective review, or codegraph,
also read:

```text
docs/agent_capabilities_and_skill_routing.md
```

Use that file as the project-local routing layer for globally installed skills
and available MCP-style tools. Do not copy skill source code into this
repository, and do not let any skill, connector, or MCP tool override the
safety, placement, validation-only, no-holdout/test, Python-executable, or
reporting rules in this `AGENTS.md`.

## 3. Route Contract

The V2 stage route is:

```text
00_data_split_label_freeze_colab.ipynb
01_feature_window_search_colab.ipynb
02_model_hpo_train_inner_colab.ipynb
03_frozen_validation_readout_colab.ipynb
04_diagnostics_ablation_colab.ipynb
05_thesis_synthesis_colab.ipynb
06_ian_final_progress_record_colab.ipynb
```

A measure-only **V2.1 branch** reads the frozen Stage 03/04 artifacts and runs a
guarded, historically-contacted walk-forward readout (it is NOT a clean test and
never reopens Stage 00-02 selection). Its sidecar bundle is
`v2_1_guarded_walkforward_readout_colab.ipynb` +
`configs/stages/v2_1_guarded_walkforward_readout.yaml` +
`docs/protocols/v2_1_guarded_walkforward_readout_protocol.md` +
`src/lst_models/guarded_walkforward.py` (with the
`stages/guarded_walkforward_readout.py` entry point). It branches off after Stage
04 and feeds Stage 05 synthesis.

The route also carries **measure-only analyses** layered on the frozen dumps,
with zero new scoring: Stage 04 hosts calibration / selective-AURC / robustness
LOO / the leakage sentinel; Stage 05 (thesis synthesis) aggregates the
validation-budget ledger, claim boundary register, expectation calibration, and
the descriptive multiplicity discount (CSCV PBO + `min_family_lcb`, BUILT), and
is the home for the still-deferred AUGRC/MDE and four-estimand analyses.

Build status (2026-06-18): stages 00-05 and the V2.1 branch have full sidecar
bundles (notebook + protocol + config + entry point + tests). Stage 06
(`06_ian_final_progress_record`) currently has its protocol only; its config and
notebook are pending — it is the route's closing progress record, not an
executable scoring stage. The listing above is the route contract (intended
shape), not an assertion that every file already exists.

Each executable stage has exactly one user-facing notebook. When an agent
creates or materially changes that notebook, the same task must create or update
the GitHub sidecar bundle. The user should not need a separate manual generation
step.

Each executable stage must have:

- one notebook in `notebooks/`
- one protocol doc in `docs/protocols/`
- one config in `configs/stages/`
- one Python stage entry point when reusable logic is needed:
  `run_stage(config)`
- one run manifest when execution occurs

Sidecar files are a repository contract, not extra user workflow. Optional
`scripts/notebooks/generate_<stage>_colab.py` helpers may exist for agents, but
they must not become a required user command or a second execution surface.

## 4. Code Style Rules

Follow `docs/lst_models_code_style_and_route_guide.md` as the source of truth.
The short version:

- Keep notebooks readable and linear.
- Keep one user-facing notebook per stage; update sidecars in the same task.
- Keep Python files small and purpose-specific.
- Use lowercase snake_case for files, folders, functions, configs, and artifacts.
- Prefer explicit config over hidden defaults.
- For file placement, follow `docs/lst_models_code_style_and_route_guide.md`
  sections `Where Code Goes` and `Code File Types And Common Function
  Placement`; if a change does not fit, stop and update the guide first.
- Reusable Python logic belongs under `src/lst_models/`, not in notebooks,
  `scripts/notebooks/`, or a broad `utils.py`.
- HPO search ranges belong in `configs/models/<model>/search_space.yaml`.
- Frozen selected params belong in `configs/frozen_params/<stage>/`.
- Use `run_stage(config)` as the public entry point for executable stage code.
- Raise exact-path errors for missing data or artifacts.
- Do not add a generic trainer, callback framework, plugin registry, or broad
  utility layer unless the style guide is updated first.
- Do not import one active notebook from another active notebook.

### Anti-Spaghetti Structural Gates

These gates are mandatory for all Python changes.

- Stage modules under `src/lst_models/stages/` are orchestration files. They
  own `run_stage(config)`, stage-specific gates, ledgers, selection logic, and
  artifact payload writers. They are not reusable libraries.
- Production code must not import one stage module from another. Forbidden in
  any `src/` file: `from lst_models.stages import <other_stage>`. Downstream
  stages consume upstream run artifacts (manifests, CSVs, JSON) and public
  domain modules, never upstream stage code.
- Any function whose source participates in a provenance code hash (for
  example the `feature_rebuild_code_sha256` payload) must live in a domain
  module such as `data.py`, `features.py`, `windows.py`, or `splits.py`, never
  in a stage module. Provenance hash builders themselves live in
  `artifacts.py`. The scientific mechanism hash must stay independent of stage
  orchestration refactors.
- A helper needed by two stages moves to the domain module named by the route
  guide before the second stage uses it. Do not copy a helper into a second
  module; move it and import it. Two implementations of the same helper in two
  modules are a structural violation, not a convenience.
- Long-term tests assert on public domain functions or `run_stage(config)`.
  No test may import a private helper from a different stage's module. A
  same-stage private-helper test is allowed only with an explicit temporary
  marker and a removal target.
- Size ratchet: a new stage module stays under 700 lines and a new
  `run_stage(config)` body under 90 lines. Existing stage modules must not
  grow beyond their recorded post-migration baselines; approved stage-scoped
  features may add lines only with a recorded reason in the task report.
- `tests/contracts/test_module_structure.py` is the enforcing static gate. A
  structural violation is `non_compliant_pending_fix`, not a style note.

Known temporary exception: the pre-migration Stage 01/02/03 cross-stage
private imports exist until the Route A migration
(`docs/lst_models_post_stage02_code_migration_plan.md`) removes them. Do not
extend that legacy surface; new code must comply immediately.

## 5. Notebook Rules

- Colab `.ipynb` is the visible execution entrypoint.
- Package-backed notebooks must include a first bootstrap/config cell that can
  clone `https://github.com/zkc768/lstm-zhang.git` at an exact commit and add
  `/content/lst_models/src` to `sys.path`.
- The user should not manually run `git clone` in Colab. The notebook bootstrap
  cell owns clone/fetch/checkout and verifies the resolved commit.
- Normal Colab workflow must not require uploading a project zip on every run.
  Manual zip upload is emergency fallback only.
- Google Drive project bundle zip is fallback for unpushed review work only and
  should use an explicit Drive file ID, not filename search, when possible.
- A package-backed notebook must fail loudly if its bootstrap target is missing
  required project files such as `configs/`, `src/lst_models/`, `docs/protocols/`,
  or the active stage sidecars. The fix is to push/sync the full bundle, not to
  silently run from a partial notebook-only state.
- Stage artifacts may be written first to Colab runtime paths such as
  `/content/lst_models_results/...`, then optionally backed up to Drive. Any
  `artifact_inventory.csv` must remain portable after that backup: use
  `file_name` and `relative_path` as locators, keep `original_runtime_path` as
  provenance only, and do not require downstream stages to read a stale
  `/content/...` absolute path.
- Every executable stage notebook must include a durable result-save cell
  immediately after the cell that successfully creates `result` from
  `run_stage(config)`. The cell must save required stage artifacts to:

```text
My Drive/lst_models/results/<stage_name>/<run_id>/
```

  The run id must come from the local output folder name or manifest, not from
  a manually typed value. The save cell must print `stage_run_id`,
  `drive_path`, and `drive_folder_id`.
- The durable result-save cell must validate the stage required artifact list
  before uploading. Missing required files must raise `FileNotFoundError` with
  exact names and the local output folder.
- Prefer the Google Drive API for durable uploads: authenticate with
  `google.colab.auth`, create folders with `files.create()` and MIME type
  `application/vnd.google-apps.folder`, and upload/update files with
  `MediaFileUpload(resumable=True)`. Do not rely on dragging files in the UI or
  on copying a whole folder through mounted Drive as the only save path.
- Final result sync must create or update a `drive_backup_manifest.json` that
  records `stage_name`, `run_id`, local output dir, Drive path parts, Drive
  folder id, uploaded file names, Drive file ids, uploaded byte sizes, and sync
  timestamp. Upload that manifest with the other required artifacts.
- Drive folder/file duplicates under the exact target parent are a hard error.
  Do not silently pick one duplicate or infer the latest run.
- Downstream stages must point to exact upstream run folders by run id and
  required artifact names. They must not infer the latest run from a parent
  folder, and they must not use a copied `artifact_inventory.csv`
  `original_runtime_path` as the active input locator. If a Colab runtime lacks
  the frozen upstream run folder, the notebook may fetch the required upstream
  artifacts from Drive by exact path parts before execution.
- Runtime paths computed by a notebook are part of the executable contract, not
  display-only variables. If a notebook computes `RAW_DATA_DIR`,
  `STAGE00_OUTPUT_DIR`, `OUTPUT_DIR`, an exact upstream run folder, or similar
  Colab/Drive path values, it must inject or normalize those values into the
  loaded stage config before calling `run_stage(config)` and before config
  contract assertions. Do not assume the YAML sidecar already contains
  runtime-specific Colab paths such as `raw_data_dir`.
- Static notebook gates and config-contract tests must verify required runtime
  path injection for every package-backed notebook that uses runtime paths.
- Long-running stages, including HPO, fold loops, model-family probes, and
  diagnostics over many candidates, must create recovery checkpoints while the
  run is in progress. Checkpoints go to:

```text
My Drive/lst_models/checkpoints/<stage_name>/<run_id>/
```

  Checkpoints must include a `checkpoint_manifest.json` with
  `stage_name`, `run_id`, `status=incomplete`, completed units, pending units,
  timestamp, and resume instructions. They are recovery state only and are not
  final evidence artifacts.
- Long-running stage code should write checkpoint files locally first, then
  mirror compact checkpoint files to Drive after each natural unit such as
  ticker, fold, window size, feature set, model family, or at a documented time
  interval. Avoid frequent small reads/writes directly against mounted Drive.
- Resume logic must require an exact `run_id` and checkpoint folder. It must not
  resume from the latest checkpoint folder by parent directory scan.
- Put research question, protocol summary, scope, and config near the top.
- Use `RUN_FULL = False` or equivalent guards for heavy cells by default.
- Keep committed outputs empty unless the notebook is explicitly a run-copy.
- Do not mount Drive in the default setup cell.
- Do not rely on machine-local paths as the active research path.
- Prefer compact tables and a small number of useful plots over long logs.
- Do not ask the user to run a separate generator just to obtain the required
  protocol, config, or tests; agents maintain those files with the notebook.
- When publishing package-backed Colab notebooks to GitHub with
  `PROJECT_REPO_COMMIT`, use a two-step exact-commit pin when needed: first
  create a full-bundle commit containing the required notebook, config,
  protocol, `src/lst_models/`, and tests; then create the final notebook commit
  that pins `PROJECT_REPO_COMMIT` to that full-bundle commit. Before reporting
  success, verify the pinned commit contains required sidecars with `git ls-tree`
  or equivalent. Do not pin to a notebook-only or scaffold-only commit.
- Long-running stage loops must print one compact progress line per completed
  natural unit (profile, fold, ticker, model family) so Colab shows liveness
  and progress can be correlated with checkpoints. Do not print per-batch or
  per-epoch spam by default.
- `drive_backup_manifest.json` must be written and uploaded last. Its own
  `uploaded_files` entry must not record a stale byte size: record its own
  size as null (self-reference) or omit its own entry. A self-referential size
  mismatch must not be reported as an upload failure.

## 6. Research Safety Rules

These rules are mandatory:

- No random split or shuffled validation for time-series evaluation.
- Train, validation, and holdout/test boundaries must be chronological.
- Fit preprocessing only on train rows.
- Label horizons must not cross split boundaries or trading-day boundaries.
- Multi-stock windows must be generated per ticker; no window may span tickers.
- Validation-only work must not read, transform, window, score, summarize, or
  use holdout/test rows.
- Model comparisons must include a stratified dummy baseline on the same target
  rows when metrics are reported.
- Do not fabricate metrics, paths, model behavior, or experiment outcomes.
- Do not catch and ignore exceptions.
- Stage 00 raw-data manifests must record `bytes` and `sha256` for every raw
  input file.
- Any stage that rebuilds features or windows must record the provenance code
  hash (`feature_rebuild_code_sha256`) and a `raw_file_integrity` status in
  its run manifest. Missing upstream fields must be recorded with exact
  reasons, never fabricated as matches.

## 7. Implementation Gate For Technical Docs

Every `lst_models` protocol or technical design doc should include this gate:

```text
Before writing or changing code for this stage, the implementer MUST read:

- docs/lst_models_code_style_and_route_guide.md
- this protocol document
- the target notebook or module

Before writing code, the implementer MUST record a placement decision:

- target_file_type
- target_path
- guide_sections used
- why_not_notebook, when creating Python helper code
- why_not_utils, when creating Python helper code
- safety_tests

The implementation MUST preserve:

- Colab-first execution
- one user-facing notebook per stage
- sidecar docs/configs/tests updated in the same task when required
- one run_stage(config) per executable stage
- canonical Python package path: src/lst_models/
- small Python helpers, no framework expansion
- no stage-to-stage imports of stage modules in production code
- validation-only scope unless explicitly authorized
- no holdout/test read, transform, window, score, or summary
- train-only preprocessing
- dummy baseline comparison where model metrics are reported
- run manifest with holdout_test_contact=false
- durable Drive result-save cell immediately after successful `run_stage(config)`
- final artifacts saved to
  `My Drive/lst_models/results/<stage_name>/<run_id>/`
- `drive_backup_manifest.json` written and uploaded with final artifacts
- checkpoint plan for long-running stages under
  `My Drive/lst_models/checkpoints/<stage_name>/<run_id>/`
- runtime paths computed by a notebook injected into the stage config before
  `run_stage(config)` and before config contract assertions
- GPU/CUDA device provenance recorded when Torch/LightGBM GPU paths are used or
  resolved
- exact-commit Colab bootstrap verified against a commit that contains required
  sidecars, not only the notebook
- notebook static-gate compatibility
```

## 8. Minimum Tests

Do not delete all tests. Keep a small GitHub-visible safety suite:

- data schema and exact missing-path tests
- chronological split tests
- label-boundary tests
- window-boundary tests
- train-only preprocessing tests
- dummy-baseline metric contract tests
- run-manifest tests
- notebook static gates
- artifact contract tests
- durable Drive result-save cell static gates for executable notebooks
- checkpoint contract tests for long-running stages
- forbidden holdout/test string checks for validation-only notebooks
- module-structure static gate: no cross-stage stage-module imports;
  provenance payload functions live in domain modules
- golden equivalence constants for provenance payload functions

Slow GPU training, full HPO, full notebook execution, large real-data
regeneration, and long multi-seed experiments may be local-only or slow CI.

## 9. Google Drive Raw Data Rules

For any task that creates or modifies raw-data access, Drive backup, notebook
data loading, or 5-minute bar construction, read these files first:

1. `docs/lst_models_code_style_and_route_guide.md`
2. `docs/lst_models_google_drive_raw_data_guide.md`
3. `configs/lst_models_data.yaml`

The authoritative raw source is the existing Google Drive folder
`s&p 100 adjusted 1 min data` with folder ID
`154SlcH3nViUcvPXFBM-E4NPg_ybljBTG`. New notebooks must download the five raw
`.txt` files by file ID into `/content/lst_models_raw_stock_data`; they must not
discover raw data by scanning mounted Drive folders, shortcuts, or old project
directories.

The canonical raw-data path is:

```text
Google Drive file ID -> Colab runtime .txt -> canonical 1min-to-5min recipe ->
[ticker, timestamp, open, high, low, close, volume]
```

Do not copy raw files into this project or into `My Drive/lst_models/data/` as a
second source of truth unless the user explicitly approves a raw-data copy task.

## 10. GPU / CUDA Rules

For model code that can use GPU acceleration, default to GPU when available.
This is a runtime acceleration rule, not a research-selection axis.

- PyTorch model code must resolve device with CUDA preference: use `cuda` when
  `torch.cuda.is_available()` is true, otherwise use `cpu`.
- If config sets `require_gpu: true`, missing CUDA/GPU support must fail loudly
  before training starts.
- If config sets `require_gpu: false` or omits it, CPU fallback is allowed but
  must be recorded in the run manifest.
- LightGBM code may request `device_type=cuda` or `device_type=gpu` only when
  the installed LightGBM build and runtime support it; unsupported GPU/CUDA
  must be recorded as an environment fallback or failure, not as model evidence.
- GPU/CPU runtime differences must not change features, labels, thresholds,
  candidates, model-family decisions, or thesis wording.
- Every training manifest must record `requested_device`, `resolved_device`,
  `cuda_available`, `gpu_name_or_null`, and `device_fallback_reason`.
- Any stage that calls `resolve_torch_device`, checks `torch.cuda.is_available`,
  moves tensors/models with `.to(device)`, or requests LightGBM GPU/CUDA must
  write device provenance to `run_manifest.json`. If per-model or per-probe
  ledgers are produced, include at least `requested_device`, `resolved_device`,
  and `device_fallback_reason` there as well.
- Fast manifest/schema tests or tiny smoke tests must assert the device
  provenance fields exist. These tests must pass on CPU-only machines.
- If CUDA-capable code exists but the manifest or ledgers omit required device
  provenance, report the stage as `non_compliant_pending_fix`. Do not claim the
  stage follows the GPU/CUDA rules until the code and tests are fixed.
- Fast tests, notebook static gates, and artifact-contract tests must not
  require GPU.
- Slow GPU checks may be local-only or marked as slow CI.

Recommended PyTorch pattern:

```python
import torch

def resolve_torch_device(requested_device="auto", require_gpu=False):
    cuda_available = torch.cuda.is_available()
    if requested_device == "auto" and cuda_available:
        return torch.device("cuda"), None
    if requested_device == "auto" and not cuda_available:
        if require_gpu:
            raise RuntimeError("GPU required, but torch.cuda.is_available() is False")
        return torch.device("cpu"), "cuda_unavailable"
    if str(requested_device).startswith("cuda") and not cuda_available:
        raise RuntimeError("CUDA requested, but torch.cuda.is_available() is False")
    return torch.device(requested_device), None
```

## 11. Compliance Failure Handling

When a task reveals an `AGENTS.md` compliance gap, do not treat it as a casual
note. Classify it and either fix it in the same task or report it as pending.

- If the user authorized edits for this task, fix code, notebook, config,
  tests, and docs together when the gap is in scope.
- If the user requested design-only or read-only work, do not edit files. Report
  `non_compliant_pending_fix` with exact paths and the smallest safe patch
  target.
- A runtime `KeyError` such as missing `raw_data_dir` in a stage config is a
  notebook/config contract failure. Fix the notebook injection point and add a
  static or contract test; do not only patch the YAML or only explain the error.
- A stage notebook that produces `result` but has no immediate durable
  result-save cell is a notebook contract failure. Add the save cell, update
  notebook static gates, and require the canonical Drive path before asking the
  user to rerun the stage.
- A long-running stage without checkpoint writing and exact-run resume rules is
  a recovery contract failure. Add a checkpoint plan before running expensive
  work.
- A Colab bootstrap failure caused by missing `configs/`, `src/lst_models/`,
  `docs/protocols/`, or target notebooks in the pinned commit is an exact-commit
  bundle failure. Push or pin a full-bundle commit and verify the pinned tree.
- CUDA-capable code without manifest device provenance is a compliance failure,
  even if GPU execution itself works.
- Notebook static gates must be strong enough to catch the contract failures
  discovered in prior work; when a new failure class appears, update the gate.

## 12. Codegraph Structural Audit Rules

Use `mcp__codegraph` as a structural audit tool for non-trivial Python changes.
It helps detect dependency direction, duplicate helpers, symbol impact, and
circular imports. It is not the source of research truth and does not replace
tests, notebook static gates, artifact contracts, protocol docs, or
holdout/test safety rules.

Codegraph is mandatory when a task:

- touches three or more Python modules under `src/lst_models/`
- creates, moves, or renames reusable helpers
- changes `run_stage(config)` or a stage entry point
- changes shared data, split, label, window, feature, metric, artifact,
  checkpoint, or device/GPU logic
- refactors imports, module placement, or file boundaries
- needs to explain impact across callers/callees before pushing

Preferred codegraph use:

- run `find_cycles` before and after non-trivial Python refactors
- use `semantic_search` before adding a new helper, to avoid duplicates
- use `context` before editing an existing function/class with callers
- use `path` when dependency direction between modules is unclear
- use `branch_compare` for structural impact review across commits/branches

If the codegraph database is missing or stale, report the exact tool failure and
use fallback checks: `rg`, direct file reads, `py_compile`, targeted pytest, and
notebook/static gates. Do not fabricate codegraph results. For a non-trivial
Python change, the end-of-task report must say either `codegraph: run` with the
useful result summary, or `codegraph: unavailable` with fallback validation.

## 13. Environment And Git

- Use the project-specified Python executable when one is documented.
- Do not use bare `python` or bare `pytest` when a project Python path exists.
- Do not install dependencies implicitly.
- Do not run heavy training unless explicitly instructed.
- Do not delete raw data.
- Do not commit, push, or create branches unless explicitly asked.
- Start and end scoped code-editing work by reporting `git status --short` and
  `git diff --stat` when a git repository exists.

## 14. End-of-Task Report

At the end of each task, report:

- files inspected
- files changed
- commands run
- validation results
- unresolved issues
- compliance gaps found, and whether each one is fixed or
  `non_compliant_pending_fix`
- codegraph result for non-trivial Python changes, or reason it was not
  required/unavailable

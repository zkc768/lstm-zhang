# AGENTS.md - lst_models V2 route
<!-- AGENTS_VERSION: v1.3-colab-github-bootstrap -->

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
- Put research question, protocol summary, scope, and config near the top.
- Use `RUN_FULL = False` or equivalent guards for heavy cells by default.
- Keep committed outputs empty unless the notebook is explicitly a run-copy.
- Do not mount Drive in the default setup cell.
- Do not rely on machine-local paths as the active research path.
- Prefer compact tables and a small number of useful plots over long logs.
- Do not ask the user to run a separate generator just to obtain the required
  protocol, config, or tests; agents maintain those files with the notebook.

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
- validation-only scope unless explicitly authorized
- no holdout/test read, transform, window, score, or summary
- train-only preprocessing
- dummy baseline comparison where model metrics are reported
- run manifest with holdout_test_contact=false
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
- forbidden holdout/test string checks for validation-only notebooks

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

## 11. Environment And Git

- Use the project-specified Python executable when one is documented.
- Do not use bare `python` or bare `pytest` when a project Python path exists.
- Do not install dependencies implicitly.
- Do not run heavy training unless explicitly instructed.
- Do not delete raw data.
- Do not commit, push, or create branches unless explicitly asked.
- Start and end scoped code-editing work by reporting `git status --short` and
  `git diff --stat` when a git repository exists.

## 12. End-of-Task Report

At the end of each task, report:

- files inspected
- files changed
- commands run
- validation results
- unresolved issues

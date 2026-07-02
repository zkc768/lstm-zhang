# lst_models_code_style_and_route_guide

Status: draft technical guide.

Scope: V2 `lst_models` route only. This document defines code style, file
naming, notebook style, config style, artifact naming, and minimum GitHub tests.
It does not move files, rename current notebooks, run notebooks, train models,
or touch holdout/test data.

## 1. Decision

Current GitHub remote: `https://github.com/zkc768/lstm-zhang.git`.

The practical target is a small, readable `lst_models` research route inside
that repo, while keeping the compact `intraday_stock_direction_research` style:

- Colab `.ipynb` remains the visible execution entrypoint.
- Core reusable logic lives in a small number of `.py` files.
- Each stage has one notebook, one protocol doc, and one config file.
- Tests stay focused on chronology, leakage, static notebook safety, artifact
  contracts, and run manifests.
- The code should look closer to a clean thesis research route than a general
  ML framework.

The useful pattern borrowed from forecasting repositories is config organization:
small YAML files, frozen parameters, and explicit output locations. The full
benchmark-framework structure is too heavy for this project.

## 2. Route Name And Stage List

The route name is:

```text
lst_models
```

Canonical guide file:

```text
docs/lst_models_code_style_and_route_guide.md
```

V2 stage sequence:

| stage | notebook | purpose |
|---|---|---|
| 00 | `00_data_split_label_freeze_colab.ipynb` | Freeze raw data manifest, chronological splits, label rules, and no-holdout boundary. |
| 01 | `01_feature_window_search_colab.ipynb` | Search feature sets and window sizes under validation-only rules. |
| 02 | `02_model_hpo_train_inner_colab.ipynb` | Run train-inner HPO for approved model families only. |
| 03 | `03_frozen_validation_readout_colab.ipynb` | Read frozen validation results under pre-registered rules. |
| 04 | `04_diagnostics_ablation_colab.ipynb` | Run diagnostics, ablations, ECE/AURC, SHAP/permutation, and robustness checks without reselection. |
| 05 | `05_thesis_synthesis_colab.ipynb` | Package thesis tables, figures, and wording from already-authorized evidence. |
| 06 | `06_ian_final_progress_record_colab.ipynb` | Final progress record and reproducibility inventory. |

## 3. Repository Layout

Target layout for V2 should stay small:

```text
intraday_stock_direction_research/
├── configs/
│   ├── lst_models_pipeline.yaml
│   ├── lst_models_data.yaml
│   ├── lst_models_validation_rules.yaml
│   └── stages/
│       ├── 00_data_split_label_freeze.yaml
│       ├── 01_feature_window_search.yaml
│       ├── 02_model_hpo_train_inner.yaml
│       ├── 03_frozen_validation_readout.yaml
│       ├── 04_diagnostics_ablation.yaml
│       ├── 05_thesis_synthesis.yaml
│       └── 06_ian_final_progress_record.yaml
├── docs/
│   ├── lst_models_code_style_and_route_guide.md
│   └── protocols/
│       ├── 00_data_split_label_freeze_protocol.md
│       ├── 01_feature_window_search_protocol.md
│       ├── 02_model_hpo_train_inner_protocol.md
│       ├── 03_frozen_validation_readout_protocol.md
│       ├── 04_diagnostics_ablation_protocol.md
│       ├── 05_thesis_synthesis_protocol.md
│       └── 06_ian_final_progress_record_protocol.md
├── notebooks/
│   ├── 00_data_split_label_freeze_colab.ipynb
│   ├── 01_feature_window_search_colab.ipynb
│   ├── 02_model_hpo_train_inner_colab.ipynb
│   ├── 03_frozen_validation_readout_colab.ipynb
│   ├── 04_diagnostics_ablation_colab.ipynb
│   ├── 05_thesis_synthesis_colab.ipynb
│   └── 06_ian_final_progress_record_colab.ipynb
├── src/
│   └── lst_models/
│       ├── config.py
│       ├── data.py
│       ├── splits.py
│       ├── labels.py
│       ├── features.py
│       ├── windows.py
│       ├── preprocessing.py
│       ├── metrics.py
│       ├── artifacts.py
│       ├── device.py
│       ├── fitting.py
│       ├── models/
│       │   ├── registry.py
│       │   ├── standard_dlinear.py
│       │   ├── tcn.py
│       │   └── ms_dlinear_tcn.py
│       └── stages/
│           ├── data_split_label_freeze.py
│           ├── feature_window_search.py
│           ├── model_hpo_train_inner.py
│           ├── frozen_validation_readout.py
│           ├── diagnostics_ablation.py
│           ├── thesis_synthesis.py
│           └── ian_final_progress_record.py
├── scripts/
│   └── notebooks/
│       └── generate_<stage_name>_colab.py
├── tests/
│   ├── data/
│   ├── stages/
│   ├── notebooks/
│   └── contracts/
└── results/
    └── <stage_name>/
```

This layout intentionally avoids a large framework tree such as `trainer/`,
`callbacks/`, `experiment/`, `pipeline/`, and `registry/` unless a real repeated
need appears.

## 4. Where Code Goes

Use this table before adding a new file. If a change does not fit one row, stop
and update the guide before creating a new directory or abstraction.

| Put it here | What belongs here | What does not belong here |
|---|---|---|
| `AGENTS.md` | Agent rules, required reading, safety gates, GPU/Drive defaults | Stage-specific experiment logic or results |
| `README.md` | Human overview, route summary, quick links | Long protocols, raw data IDs as the only manifest |
| `docs/agent_capabilities_and_skill_routing.md` | Project-level skill, plugin, MCP, connector, and agent-workflow routing | Stage-specific experiment logic, metrics, or connector secrets |
| `configs/lst_models_data.yaml` | Raw Drive file IDs, raw `.txt` schema, 1min-to-5min recipe, holdout boundary | Generated outputs, local Windows paths, Python expressions |
| `configs/lst_models_pipeline.yaml` | Ordered stage registry: stage name, config, notebook, protocol, expected outputs | Hyperparameter search results or ad hoc notes |
| `configs/stages/<nn>_<stage>.yaml` | Stage parameters frozen before execution | Code, metrics observed after validation, secrets |
| `configs/frozen_params/<stage>/` | HPO-selected params after the authorized stage freezes them | Search spaces that are still open-ended |
| `docs/protocols/<nn>_<stage>_protocol.md` | Pre-registered stage purpose, inputs, outputs, decision rules, stop conditions | Notebook logs, generated result dumps |
| `docs/lst_models_code_style_and_route_guide.md` | Repo layout, naming, file placement, style rules, minimum tests | Stage-specific metric claims |
| `docs/lst_models_google_drive_raw_data_guide.md` | Drive/raw-data access rules and file-ID policy | Duplicate raw data |
| `notebooks/<nn>_<stage>_colab.ipynb` | Colab entrypoint: config display, stage call, artifact display, compact interpretation | Canonical reusable logic, hidden imports from other notebooks |
| `src/lst_models/config.py` | Config loading, path normalization, config hash helpers | Stage-specific model logic |
| `src/lst_models/data.py` | Raw bar schemas, Drive file-ID manifest loading, 1min-to-5min conversion | Model training or thesis prose |
| `src/lst_models/splits.py` | Chronological train/validation/closed-holdout boundary helpers | Random or shuffled time-series splits |
| `src/lst_models/labels.py` | Label construction, no-trade band labels, boundary invalidation | Threshold decisions based on validation results |
| `src/lst_models/features.py` | Feature construction that is reused or safety-critical | One-off exploratory plots |
| `src/lst_models/windows.py` | Per-ticker window creation and trading-day/window boundary checks | Cross-ticker batching or model code |
| `src/lst_models/preprocessing.py` | Train-only scaler/imputer helpers and transform contracts | Fit-on-all-data shortcuts |
| `src/lst_models/metrics.py` | Macro F1, balanced accuracy, dummy-baseline deltas, LCB helpers, calibration/selective-prediction measurement (reliability bins, ECE, Brier decomposition, risk-coverage, AURC) | Wording decisions or thesis claims |
| `src/lst_models/diagnostics.py` | Measure-only validation-diagnostics frame builders over frozen prediction dumps: dump schema gates plus derived columns, calibration/selective/robustness/failure tables, baseline-reconstruction equality gates | Model or calibrator fitting, stage entry gates, ledgers, artifact writing |
| `src/lst_models/microstructure.py` | Measure-only microstructure spread proxies from already-loaded canonical bars (Roll / Corwin-Schultz half-spread), the frozen spread-to-band partition, spread-conditioned dump readouts, and the preregistered mechanical verdict rules | Raw-file loading, model fitting, stage entry gates, artifact writing, tradeability or significance wording |
| `src/lst_models/artifacts.py` | Manifest writing, artifact inventory, schema checks, artifact paths | Model architecture |
| `src/lst_models/device.py` | CUDA/CPU resolution and manifest fields | Research-selection decisions |
| `src/lst_models/models/registry.py` | Small model registry and model lookup | Stage orchestration or training loops |
| `src/lst_models/models/<model>.py` | One compact model class/wrapper per model family | Config parsing, data loading, result writing |
| `src/lst_models/fitting.py` | Shared probe/trial fit wrappers: logreg/LightGBM/torch sequence fits and early-stopping splits, as plain functions | Trainer frameworks, callback systems, plugin registries, stage orchestration |
| `src/lst_models/stages/<stage>.py` | One public `run_stage(config)` orchestration function per executable stage; must not import other stage modules or define provenance-hashed mechanism code | Notebook UI, markdown display, raw HPO notebooks, reusable helper libraries |
| `scripts/notebooks/generate_<stage>_colab.py` | Notebook generation only | Research logic that should be tested as package code |
| `tests/data/` | Raw schema, split, label, window, train-only preprocessing tests | Slow full training |
| `tests/stages/` | `run_stage(config)` smoke and contract tests with tiny synthetic data | GPU-required full HPO |
| `tests/notebooks/` | Static gates: parse, AST, empty outputs, forbidden strings | Notebook execution as the default gate |
| `tests/contracts/` | Artifact schemas, manifest fields, ledger rules | Exploratory plots |
| `results/` | Local/Drive generated outputs, usually gitignored | Raw source data, hand-authored protocols |
| `artifacts/` | Small review/provenance artifacts when explicitly useful | Large checkpoints, raw data copies |
| `paper/` or `reports/` | Thesis-ready tables, figures, and prose packages after evidence is authorized | Upstream model-selection logic |

Placement rules:

- If code is reused by two notebooks, move it to `src/lst_models/`.
- If code protects chronology, leakage, labels, windows, metrics, manifests, or
  artifacts, move it to `src/lst_models/` and test it.
- If code only displays a table or plot for one stage, keep it in the notebook.
- If a value changes the research conclusion, put it in a config or protocol,
  not as a hidden Python default.
- If a file is generated by running a stage, it belongs under `results/` or
  `artifacts/`, not under `docs/` or `configs/`.
- If a folder would contain only one vague catch-all module such as `utils.py`,
  do not create the folder yet.

Anti-placement examples:

```text
notebooks importing other active notebooks
training loops hidden in notebook cells after package migration
raw `.txt` files committed under data/
HPO-selected params edited directly into model source files
validation result summaries stored as configs
stage logic placed in scripts/notebooks/
GPU-only checks required by the fast test suite
one stage module imported as a helper library by another stage
provenance-hashed functions defined inside a stage module
the same helper duplicated into a second module instead of moved to a domain module
```

## 5. Code File Types And Common Function Placement

Use this section before writing code. A technical doc that asks for code must
name the target file type and expected module from this table. If it cannot,
the doc is not implementation-ready.

| Function or class type | Put it here | Naming pattern | Test location |
|---|---|---|---|
| YAML read/write, config merge, config hash | `src/lst_models/config.py` | `load_stage_config`, `hash_config` | `tests/contracts/` |
| Google Drive raw-data manifest helpers | `src/lst_models/data.py` | `load_raw_manifest`, `download_raw_files` | `tests/data/` |
| Raw `.txt` schema checks | `src/lst_models/data.py` | `validate_raw_bar_schema` | `tests/data/` |
| 1-minute to 5-minute OHLCV conversion | `src/lst_models/data.py` | `resample_1min_to_5min` | `tests/data/` |
| Chronological split construction | `src/lst_models/splits.py` | `make_chronological_splits` | `tests/data/` |
| Inner-fold construction for train-inner CV | `src/lst_models/splits.py` | `build_train_inner_folds` | `tests/data/` |
| Split-boundary and closed-holdout guards | `src/lst_models/splits.py` | `assert_no_holdout_contact` | `tests/contracts/` |
| Direction labels and no-trade band | `src/lst_models/labels.py` | `make_direction_labels` | `tests/data/` |
| Label horizon invalidation | `src/lst_models/labels.py` | `invalidate_cross_boundary_labels` | `tests/data/` |
| Feature construction | `src/lst_models/features.py` | `build_feature_frame` | `tests/data/` |
| Window tensors | `src/lst_models/windows.py` | `make_ticker_windows` | `tests/data/` |
| Train-only preprocessing | `src/lst_models/preprocessing.py` | `fit_train_preprocessor`, `transform_with_preprocessor` | `tests/data/` |
| Dummy baseline | `src/lst_models/metrics.py` | `score_stratified_dummy` | `tests/contracts/` |
| Classification metrics and LCB | `src/lst_models/metrics.py` | `score_classifier`, `compute_metric_lcb` | `tests/contracts/` |
| Run manifest | `src/lst_models/artifacts.py` | `write_run_manifest` | `tests/contracts/` |
| Artifact names and paths | `src/lst_models/artifacts.py` | `build_stage_artifact_paths` | `tests/contracts/` |
| Provenance code-hash builders | `src/lst_models/artifacts.py` | `feature_rebuild_code_sha256` | `tests/contracts/` |
| CUDA/CPU resolution | `src/lst_models/device.py` | `resolve_torch_device` | `tests/contracts/` |
| Model lookup | `src/lst_models/models/registry.py` | `register_model`, `get_model_class` | `tests/contracts/` |
| Model architecture | `src/lst_models/models/<model>.py` | `<ModelName>Model` | `tests/stages/` or `tests/contracts/` |
| Probe/trial fit wrappers and early-stopping splits | `src/lst_models/fitting.py` | `fit_probe`, `fit_lightgbm_probe`, `torch_inner_train_early_stopping_split` | `tests/stages/` or `tests/contracts/` |
| Dump-frame diagnostics builders | `src/lst_models/diagnostics.py` | `gate_and_derive_dump`, `calibration_frames`, `robustness_frames` | `tests/stages/` (stage smoke) |
| Spread proxies and spread-partition dump readouts | `src/lst_models/microstructure.py` | `roll_halfspread_by_day`, `assign_spread_partition`, `halfspread_partition_readout`, `verdict_from_readout` | `tests/contracts/` |
| Stage orchestration | `src/lst_models/stages/<stage>.py` | `run_stage` | `tests/stages/` |
| Notebook generation | `scripts/notebooks/generate_<stage>_colab.py` | `build_notebook` | `tests/notebooks/` |

Rules for common functions:

- Do not create a broad `utils.py`. If a helper has a clear domain, put it in
  that domain file. If it has no clear domain, the design is not clear enough.
- Do not put HPO search ranges inside model source. Use
  `configs/models/<model>/search_space.yaml`.
- Do not put selected HPO params inside model source. Use
  `configs/frozen_params/<stage>/<model>_best_params.yaml`.
- Do not put train loops in notebooks after the package-backed route begins.
  Notebooks call a stage; stages call tested helpers.
- Do not let `models/<model>.py` read files, write results, parse YAML, or know
  Drive paths. Models receive tensors and config values.
- Do not let `metrics.py` choose thesis wording. Metrics returns numbers and
  flags; protocols decide allowed wording.

Borrowed pattern from `compare_forecasting_models`:

```text
configs/models/<model>/search_space.yaml
    -> src/lst_models/stages/02_model_hpo_train_inner.py
    -> configs/frozen_params/02_model_hpo_train_inner/<model>_best_params.yaml
```

This pattern is acceptable because search ranges, HPO execution, and frozen
results live in different file types. It should stay small; do not recreate a
large benchmark framework.

## 6. Naming Rules

Use lowercase snake_case everywhere.

| item | pattern | example |
|---|---|---|
| route | lowercase short name | `lst_models` |
| notebook | `<nn>_<stage_name>_colab.ipynb` | `01_feature_window_search_colab.ipynb` |
| protocol doc | `<nn>_<stage_name>_protocol.md` | `01_feature_window_search_protocol.md` |
| stage config | `<nn>_<stage_name>.yaml` | `01_feature_window_search.yaml` |
| Python stage module | `<stage_name_without_number>.py` | `feature_window_search.py` |
| result folder | `results/<stage_name>/` | `results/01_feature_window_search/` |
| run folder | `<timestamp>_<run_id>/` | `2026-06-08_1430_a1b2c3/` |
| manifest | `run_manifest.json` | `run_manifest.json` |
| summary table | `<stage_name>_summary.csv` | `feature_window_search_summary.csv` |
| frozen params | `<model>_<candidate>_best_params.yaml` | `dlinear_mean_candidate_best_params.yaml` |

Keep notebook numbers in V2 because this route is a visible thesis execution
sequence. Keep Python imports unnumbered because import paths should describe
behavior, not order.

## 7. Single-Notebook User Flow

Each stage has exactly one user-facing execution notebook. The notebook is what
the user opens, reviews, and runs in Colab. GitHub sidecar files exist to make
the notebook reproducible and safe; they must not become extra manual steps for
the user.

User workflow:

```text
open one Colab notebook
run first bootstrap/config cell
verify PROJECT_ROOT and PROJECT_COMMIT
review stage config cell
run approved cells
read compact outputs
```

Colab project bootstrap policy:

```text
github_commit -> drive_bundle -> manual_upload
```

| mode | status | allowed use |
|---|---|---|
| `github_commit` | default | Clone `https://github.com/zkc768/lstm-zhang.git` at an exact commit and add `/content/lst_models/src` to `sys.path`. |
| `drive_bundle` | fallback | Download a project bundle zip by explicit Google Drive file ID for unpushed review work. |
| `manual_upload` | emergency fallback | Upload a project bundle zip only when GitHub or Drive bundle access is unavailable. |
| `already_present` | local/runtime fallback | Use an existing `/content/lst_models` tree only after required files are verified. |

A package-backed notebook must never assume that the `.ipynb` file alone is
sufficient. The bootstrap target must contain:

```text
configs/
src/lst_models/
docs/protocols/
notebooks/
```

For an active stage, the exact commit or bundle must also contain that stage's
notebook, protocol, config, and required source/test sidecars. If any required
path is missing, fail loudly with the exact missing path. Do not continue from a
partial notebook-only state.

Notebook bootstrap switches should follow this pattern:

```python
RUN_PROJECT_BOOTSTRAP = False
PROJECT_BOOTSTRAP_MODE = "github_commit"  # github_commit | drive_bundle | manual_upload | already_present

PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"
PROJECT_REPO_COMMIT = "<exact_commit_hash>"
PROJECT_ROOT = Path("/content/lst_models")

PROJECT_DRIVE_BUNDLE_FILE_ID = ""  # required only for drive_bundle
RUN_DOWNLOAD = False
RUN_STAGE00 = False
```

Rules:

- Do not clone a floating branch such as `main` as the research runtime.
- Do not ask the user to manually run `git clone` in a Colab terminal.
- Do not make zip upload the normal workflow.
- Update `PROJECT_REPO_COMMIT` whenever package/config/protocol code needed by
  the notebook changes and is pushed.
- If local Stage 00/01 files exist only on this machine and are not pushed to
  GitHub, `github_commit` bootstrap is not ready for those files. Use a Drive
  bundle only as a temporary fallback, or push the full stage bundle first.

Agent workflow when creating or materially changing a stage notebook:

```text
read AGENTS.md and this guide
create/update the one stage notebook
create/update the matching protocol doc
create/update the matching stage config
create/update static notebook gates if notebook safety rules changed
create/update contract or data tests if reusable logic or artifact schemas changed
leave heavy execution off by default
```

Required sidecar bundle:

| user-facing file | required sidecar files |
|---|---|
| `notebooks/<nn>_<stage>_colab.ipynb` | `docs/protocols/<nn>_<stage>_protocol.md` |
| same notebook | `configs/stages/<nn>_<stage>.yaml` |
| same notebook, if reusable stage logic exists | `src/lst_models/stages/<stage>.py` |
| same notebook, if model HPO search changes | `configs/models/<model>/search_space.yaml` |
| same notebook, if selected params freeze | `configs/frozen_params/<stage>/<model>_best_params.yaml` |
| same notebook, if safety behavior changes | targeted tests under `tests/` |

Important: `scripts/notebooks/generate_<stage>_colab.py` is an optional agent
helper for repeatable notebook creation. It is not a required user command and
must not be treated as a second execution surface. If a generator exists, it
must generate the same single user-facing notebook and keep sidecars aligned.

Do not ask the user to separately "generate protocol", "generate config", or
"generate tests" after asking for a notebook. If those files are required by the
GitHub contract, the agent creates or updates them in the same implementation
task.

## 8. Notebook Style

Each notebook is a readable execution report, not the canonical source of all
logic.

Required notebook structure:

```text
1. title, research question, route scope
2. frozen protocol summary
3. config cell
4. dependency and exact-commit install cell, when package-backed
5. raw input manifest and missing-path checks
6. stage invocation cell
7. artifact inventory
8. result tables
9. small plots, only when useful
10. honest interpretation and limitations
```

Notebook rules:

- Keep one early config cell.
- Use `RUN_FULL = False` or a stage-specific `RUN_* = False` default for heavy
  cells.
- Do not mount Drive in the default setup cell.
- Do not read, transform, window, score, or summarize holdout/test rows in
  validation-only stages.
- Do not hide mutable local paths inside notebook code.
- Keep committed outputs empty unless the file is explicitly a run-copy artifact.
- Prefer tables over long logs.
- Prefer small plots over figure dumps.
- Do not use previous notebooks as active imports.

Example notebook control cell:

```python
RUN_FULL = False
STAGE_NAME = "01_feature_window_search"
SCOPE = "validation_only"

config = {
    "stage_name": STAGE_NAME,
    "scope": SCOPE,
    "raw_data_dir": "/content/stage0_raw_stock_data",
    "output_dir": "/content/lst_models_results/01_feature_window_search",
    "tickers": ["CSCO", "JPM", "KO", "MSFT", "WMT"],
    "window_sizes": [5, 10, 20],
    "holdout_test_contact": False,
}
```

Example stage call:

```python
from lst_models.stages.feature_window_search import run_stage

if RUN_FULL:
    result = run_stage(config)
    display(result)
else:
    print("RUN_FULL=False; stage not executed.")
```

## 9. Config Style

Config files should be boring, explicit, and small.

Example:

```yaml
stage_name: 01_feature_window_search
scope: validation_only
holdout_test_contact: false

tickers: [CSCO, JPM, KO, MSFT, WMT]
window_sizes: [5, 10, 20]

inputs:
  raw_data_dir: /content/stage0_raw_stock_data
  previous_stage_manifest: null

outputs:
  output_dir: /content/lst_models_results/01_feature_window_search
  summary: feature_window_search_summary.csv
  manifest: run_manifest.json

selection_rules:
  primary_metric: macro_f1
  baseline: stratified_dummy
  require_delta_macro_f1_vs_dummy: true
```

Config rules:

- Do not put Python expressions in YAML.
- Do not put machine-local Windows paths in GitHub configs.
- Put stage order in `configs/lst_models_pipeline.yaml`.
- Put frozen model params in small YAML files after HPO.
- Put large generated outputs under `results/`, not under `configs/`.
- Config values that affect research conclusions must be protocol-backed.

Borrowed frozen-param pattern:

```text
configs/
└── frozen_params/
    └── 02_model_hpo_train_inner/
        ├── lightgbm_mean_candidate_best_params.yaml
        ├── dlinear_mean_candidate_best_params.yaml
        └── lstm_lcb_candidate_best_params.yaml
```

## 10. Python Code Style

Python should be small, direct, and testable.

Rules:

- One stage module exposes exactly one public `run_stage(config)` entry point.
- Use short, specific helper names.
- Avoid generic `utils.py` unless the file is tiny and has one purpose.
- Prefer typed dataclasses for stage configs and results.
- Do not swallow exceptions.
- Missing data must raise `FileNotFoundError` with the exact missing path.
- Use train-only preprocessing helpers rather than inline scaler fitting.
- Any helper that can affect chronology, labels, windows, metrics, or artifacts
  needs a targeted test.
- Stage modules are orchestration-only: they must not import another stage
  module and must not define provenance-hashed mechanism code. See the
  `Anti-Spaghetti Structural Gates` section in `AGENTS.md`.

Function size targets:

| function type | target |
|---|---|
| pure helper | 10 to 35 lines |
| stage orchestration | 30 to 70 lines |
| notebook generator function | split before 80 lines |
| model class | split when forward logic and validation logic mix |

Example stage module style:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class StageConfig:
    stage_name: str
    scope: str
    raw_data_dir: Path
    output_dir: Path
    tickers: tuple[str, ...]
    window_sizes: tuple[int, ...]


@dataclass(frozen=True)
class StageResult:
    summary_path: Path
    manifest_path: Path


def run_stage(config: Mapping[str, object]) -> StageResult:
    cfg = parse_config(config)
    require_validation_only(cfg.scope)

    frames = load_inputs(cfg.raw_data_dir, cfg.tickers)
    candidates = build_candidate_table(frames, cfg.window_sizes)
    summary = score_candidates(candidates)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = cfg.output_dir / "feature_window_search_summary.csv"
    manifest_path = cfg.output_dir / "run_manifest.json"

    summary.to_csv(summary_path, index=False)
    write_manifest(cfg, summary_path, manifest_path)

    return StageResult(summary_path=summary_path, manifest_path=manifest_path)


def require_validation_only(scope: str) -> None:
    if scope != "validation_only":
        raise ValueError(f"expected validation_only scope, got {scope!r}")


def load_inputs(raw_data_dir: Path, tickers: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    frames = {}
    for ticker in tickers:
        path = raw_data_dir / f"{ticker}.csv"
        if not path.exists():
            raise FileNotFoundError(f"missing raw ticker file: {path}")
        frames[ticker] = pd.read_csv(path)
    return frames
```

Anti-patterns:

```text
helpers.py with hundreds of unrelated functions
train.py that changes model, data, metrics, and plots in one file
try/except Exception: pass
global config mutated by notebook cells
random train_test_split for time-series validation
function names such as do_it, process, run_all, get_data2
from lst_models.stages import <other_stage> used as a helper library
```

## 11. Artifact Naming

Each run writes one manifest and a small portable inventory.

Canonical result locations:

```text
Colab runtime: /content/lst_models_results/<stage_name>/<run_id>/
Drive backup:  My Drive/lst_models/results/<stage_name>/<run_id>/
Repo-relative: results/<stage_name>/<run_id>/
```

Required run files:

```text
results/<stage_name>/<run_id>/
├── run_manifest.json
├── artifact_inventory.csv
├── <stage_name>_summary.csv
└── logs.txt                         # optional, keep short
```

`artifact_inventory.csv` must be portable across Colab runtime and Drive
backup. Do not make a runtime-only absolute `path` column the only locator.
Minimum columns:

```text
artifact_name
file_name
relative_path
original_runtime_path
exists
bytes
sha256
```

Consumers must locate artifacts as:

```text
run_folder / relative_path
```

`original_runtime_path` is provenance only. Stage 01 and later stages must not
use it as the input path after a run folder has been copied to Drive or another
machine.

Downstream stage configs must point to exact upstream run folders, not parent
stage folders. For example Stage 01 must freeze:

```text
stage00_run_id
stage00_runtime_run_dir
stage00_drive_path_parts
stage00_run_manifest
```

If a Colab runtime is missing the frozen upstream run folder, the notebook may
download the required upstream artifacts from Drive by exact path parts through
the Drive API. It must not scan for the latest run, use a stale `/content/...`
inventory path, or require manual upload of upstream results.

Manifest minimum fields:

```json
{
  "route": "lst_models",
  "stage_name": "01_feature_window_search",
  "scope": "validation_only",
  "repo_url": null,
  "git_commit": null,
  "config_sha256": "<sha256>",
  "notebook_sha256": "<sha256>",
  "input_artifacts": [],
  "output_artifacts": [],
  "holdout_test_contact": false
}
```

Artifact rules:

- Raw data is never deleted or rewritten.
- Generated run copies and full-run notebooks should not become canonical.
- Large outputs, checkpoints, and prediction dumps should be gitignored unless
  a specific small artifact is needed for thesis evidence.
- Every result table that supports a claim must include `scope`.

## 12. Minimum Tests For GitHub

Do not delete all tests. Keep a small but hard test set.

Must keep on GitHub:

| test area | purpose |
|---|---|
| data loading | raw ticker schema and exact missing-path failures |
| chronological splits | no random split, no shuffled validation |
| label boundaries | label horizon does not cross split or trading-day boundary |
| windows | no window crosses ticker, trading day, or split boundary |
| preprocessing | scalers and imputers fit train rows only |
| dummy baseline | model comparisons include same-row stratified dummy baseline |
| metrics | macro F1, balanced accuracy, and delta vs dummy columns exist |
| artifact contracts | required CSV/JSON schemas are stable |
| run manifest | config hash, notebook hash, scope, and `holdout_test_contact=false` |
| notebook static gate | notebook parses, code cells AST-parse, outputs empty |
| forbidden strings | no active holdout/test read in validation-only notebooks |
| module structure | no cross-stage stage-module imports; provenance payload functions live in domain modules |
| golden equivalence | provenance payload functions pinned by committed output constants |

Can be local-only or slow CI:

- GPU training checks.
- Full HPO runs.
- Full notebook execution.
- Large real-data regeneration.
- Plot rendering checks.
- Long multi-seed experiments.

Minimum test command shape:

```powershell
E:\codex_workspace\_envs\py311_shared\python.exe -m pytest tests\data tests\stages tests\notebooks tests\contracts -q -rs
```

The default GitHub test suite should be fast enough to run often. Heavy training
is not required to prove chronology, leakage, manifests, and notebook safety.

## 13. What Not To Build

Do not add these unless a later stage proves the need:

- Full experiment framework.
- Generic trainer abstraction.
- Callback system.
- Deep plugin registry.
- Multi-backend config engine.
- Notebook-to-notebook imports.
- Large process-document chain.
- Test suite that requires GPU training for basic safety.

The V2 route should be understandable from:

```text
one guide
one pipeline config
one notebook per stage
one protocol per stage
small Python helpers
minimum safety tests
```

## 14. Acceptance Checklist

Before calling the V2 route GitHub-ready:

- [ ] Every stage has one notebook, one protocol doc, and one config.
- [ ] Every executable stage has `run_stage(config)`.
- [ ] Canonical notebooks have empty outputs.
- [ ] Heavy cells default to off.
- [ ] No validation-only notebook reads or summarizes holdout/test data.
- [ ] Every model comparison includes a stratified dummy baseline.
- [ ] Run manifests record config hash, notebook hash, scope, and holdout flag.
- [ ] Minimum GitHub tests pass.
- [ ] Raw data and large generated outputs are not committed.
- [ ] Thesis wording is based only on authorized evidence scope.

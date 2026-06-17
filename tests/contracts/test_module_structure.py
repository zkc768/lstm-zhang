"""Static structure gates (AGENTS.md, Anti-Spaghetti Structural Gates).

These tests enforce the post-migration module boundaries mechanically:

- No production code under ``src/`` may import a stage module. Stages consume
  upstream run artifacts and public domain modules, never upstream stage code.
- Stage modules are orchestration-only: no torch model classes
  (``nn.Module``) and no provenance source hashing (``inspect.getsource``)
  inside ``src/lst_models/stages/``. Provenance payload functions live in
  domain modules; hash builders live in ``lst_models.artifacts``.
- Tests may touch a stage module's private helpers only when the test file
  targets that same stage (``test_stage<NN>_*`` naming); cross-stage private
  access is forbidden.
- Size ratchet: existing stage modules must not grow beyond their recorded
  post-migration baselines. Growing a baseline requires editing this file in
  the same change with a recorded reason (visible in review). New stage
  modules must stay under 700 lines.

A violation here is ``non_compliant_pending_fix``, not a style note.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "lst_models"
STAGES = SRC / "stages"
TESTS = ROOT / "tests"

# Post-migration baselines recorded 2026-06-09 (Route A Phase 4). Raising a
# number requires an approved stage-scoped reason in the same change.
# 2026-06-10 Stage 03 plan Task 7: PROBE_BY_FAMILY / lightgbm params /
# lightgbm tail split / trial probe config dedupe-moved from stage02 into
# fitting.py (model_hpo_train_inner.py tightened 2084 -> 1920), and the
# approved stage-scoped mechanism-frozen refit wrappers were added to
# frozen_validation_readout.py (495 -> 647).
# 2026-06-10 Stage 03 plan Tasks 8+9: the approved stage-scoped one-shot
# scoring loop, mechanical-only fallback wiring, predeclared-criteria
# judgement, per-seed checkpoints, and the seven readout artifact/manifest/
# decision-record writers landed in frozen_validation_readout.py
# (647 -> 1603); the registry baseline scorer dedupe-moved from stage02 to
# metrics.score_registry_baseline (model_hpo_train_inner.py tightened
# 1920 -> 1880).
# 2026-06-10 Stage 03 protocol section 11 resume contract: the approved
# stage-scoped exact-run-id resume entry (_load_resume_state/_ResumeState),
# ledger-state checkpoint payload, and failed-seed retry purge landed in
# frozen_validation_readout.py (1603 -> 1844).
STAGE_MODULE_MAX_LINES = {
    "data_split_label_freeze.py": 133,
    "feature_window_search.py": 1004,
    "model_hpo_train_inner.py": 1880,
    "frozen_validation_readout.py": 1844,
}
NEW_STAGE_MODULE_MAX_LINES = 700

# Test files prefixed test_stage<NN> may use that stage's private helpers
# (with a TEMPORARY marker per AGENTS.md); all other private access is
# cross-stage and forbidden.
STAGE_MODULE_BY_TEST_PREFIX = {
    "test_stage00": "data_split_label_freeze",
    "test_stage01": "feature_window_search",
    "test_stage02": "model_hpo_train_inner",
    "test_stage03": "frozen_validation_readout",
    "test_stage04": "diagnostics_ablation",
    "test_v2_1": "guarded_walkforward_readout",
}


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _violations_for_stage_imports(path: Path, tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "lst_models.stages" or module.startswith("lst_models.stages."):
                found.append(f"{path}:{node.lineno} imports {module}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("lst_models.stages"):
                    found.append(f"{path}:{node.lineno} imports {alias.name}")
    return found


def test_src_has_no_stage_to_stage_imports() -> None:
    violations = []
    for path in _python_files(SRC):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        violations.extend(_violations_for_stage_imports(path, tree))
    assert not violations, "stage modules imported inside src/:\n" + "\n".join(violations)


def test_stage_modules_contain_no_models_or_source_hashing() -> None:
    violations = []
    for path in _python_files(STAGES):
        text = path.read_text(encoding="utf-8")
        if "nn.Module" in text:
            violations.append(f"{path}: defines torch model code (nn.Module)")
        if "inspect.getsource" in text:
            violations.append(f"{path}: hashes source text (inspect.getsource)")
    assert not violations, (
        "stage modules must stay orchestration-only:\n" + "\n".join(violations)
    )


def test_stage_modules_respect_line_baselines() -> None:
    violations = []
    for path in _python_files(STAGES):
        if path.name == "__init__.py":
            continue
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        baseline = STAGE_MODULE_MAX_LINES.get(path.name)
        if baseline is None:
            if line_count > NEW_STAGE_MODULE_MAX_LINES:
                violations.append(
                    f"{path.name}: new stage module has {line_count} lines "
                    f"(max {NEW_STAGE_MODULE_MAX_LINES})"
                )
        elif line_count > baseline:
            violations.append(
                f"{path.name}: {line_count} lines exceeds recorded baseline {baseline}; "
                "move logic to a domain module or record an approved reason here"
            )
    assert not violations, "\n".join(violations)


def _stage_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("lst_models.stages."):
                    bound = alias.asname or alias.name
                    aliases[bound] = alias.name.rsplit(".", 1)[-1]
        elif isinstance(node, ast.ImportFrom) and (node.module or "") == "lst_models.stages":
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
    return aliases


def _allowed_stage_for_test(path: Path) -> str | None:
    for prefix, module in STAGE_MODULE_BY_TEST_PREFIX.items():
        if path.name.startswith(prefix):
            return module
    return None


def test_tests_do_not_touch_other_stages_privates() -> None:
    violations = []
    for path in _python_files(TESTS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed = _allowed_stage_for_test(path)
        aliases = _stage_aliases(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("lst_models.stages."):
                    stage = module.rsplit(".", 1)[-1]
                    for alias in node.names:
                        if alias.name.startswith("_") and stage != allowed:
                            violations.append(
                                f"{path}:{node.lineno} imports {stage}.{alias.name}"
                            )
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                stage = aliases.get(node.value.id)
                if stage and node.attr.startswith("_") and stage != allowed:
                    violations.append(
                        f"{path}:{node.lineno} touches {stage}.{node.attr}"
                    )
    assert not violations, (
        "cross-stage private access in tests:\n" + "\n".join(violations)
    )

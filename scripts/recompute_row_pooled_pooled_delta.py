"""Measure-only recompute of the protocol row-pooled ``pooled_delta`` (FIX-1).

The shipped guarded walk-forward code (pre-commit f10637b) reported the
EQUAL-WEIGHT-per-period ``pooled_delta`` (+0.005439 for run
20260617_051047_321730). The frozen protocol section 8 (lines 508-511) defines
``pooled_delta`` as a ROW-POOLED statistic: for each seed, concatenate the
judged row's predictions across all periods and the per-period stratified-dummy
predictions across all periods, compute one macro-F1 on each row-union, take the
delta, then mean over seeds.

For the already-completed run the row-pooled value cannot be read off the stored
artifacts because the per-period stratified-dummy *predictions* were never
persisted (only their macro-F1). This script reconstructs them deterministically
and recomputes the protocol value WITHOUT contacting the holdout or refitting any
model (zero new scoring events):

  1. Rebuild the data context exactly as the runner does
     (``_verify_entry_gates`` + ``_load_data_context``; ``_validate_config`` is
     deliberately NOT called so the ``sign_off: pending`` repo config still runs).
  2. For each period, mask train/eval by ``trading_day_ts`` and re-score the
     stratified dummy at ``seeds[0]`` -- ``predict_stratified_dummy`` is fully
     deterministic in ``(y_train, n_eval, seed)`` (metrics.py), so the
     reconstruction is byte-identical to the run.
  3. SELF-CHECK: the reconstructed per-period dummy macro-F1 must match the run's
     stored ``v2_1_same_row_baselines.csv`` to ``tol``; the per-period candidate
     eval-row counts/positives (from ``v2_1_predictions.csv``) must match the
     data context. If either fails the row-pooled number is NOT trusted.
  4. Compute the protocol row-pooled ``pooled_delta`` via the same helper the
     runner now uses (``_row_pooled_pooled_delta``), plus the equal-weight value
     for cross-checking against the reported +0.005439.

Run inside a Colab/Drive session that already has the v2.1 ``config`` built and
the run's ``v2_1_predictions.csv`` / ``v2_1_same_row_baselines.csv`` available::

    from scripts.recompute_row_pooled_pooled_delta import recompute_and_verify
    out = recompute_and_verify(
        config,
        predictions_csv="/content/.../v2_1_predictions.csv",
        baselines_csv="/content/.../v2_1_same_row_baselines.csv",
    )
    print(out)

``config`` is the SAME mapping passed to ``run_guarded_walkforward`` (the v2.1
notebook builds it with the Colab runtime input paths).
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import guarded_walkforward as gw
from lst_models import metrics


def _period_train_eval(meta: pd.DataFrame, period: Mapping[str, Any]):
    """Replicate the runner's per-period split (guarded_walkforward.py:498)."""
    p_start = pd.Timestamp(period["start"])
    p_end = pd.Timestamp(period["end_exclusive"])
    train_mask = meta["trading_day_ts"] < p_start
    test_mask = (meta["trading_day_ts"] >= p_start) & (meta["trading_day_ts"] < p_end)
    y_train = meta.loc[train_mask, "label"].to_numpy(dtype=int)
    test_meta = meta.loc[test_mask].reset_index(drop=True)
    return y_train, test_meta


def recompute_and_verify(
    config: Mapping[str, Any],
    predictions_csv: str,
    baselines_csv: str | None = None,
    dummy_tol: float = 1e-9,
    reported_equal_weight: float | None = 0.005439378325602524,
) -> dict[str, Any]:
    """Return the protocol row-pooled ``pooled_delta`` plus verification flags.

    Raises ``AssertionError`` if a self-check fails (reconstruction not trusted).
    """
    wf = gw.require_mapping(config["walkforward"], "walkforward")
    periods = list(wf["periods"])
    seeds = [int(s) for s in wf["seeds"]]
    judged_row = str(
        gw.require_mapping(config["predeclared_criteria"], "predeclared_criteria")[
            "judged_row"
        ]
    )

    # 1. Rebuild the data context exactly as the runner does (skip _validate_config
    #    so the sign_off: pending repo config still runs -- this is read-only).
    inputs_map = gw._verify_entry_gates(config)
    data_context = gw._load_data_context(config, inputs_map)
    meta = data_context.metadata

    # 2. Reconstruct the per-period stratified dummy at seeds[0].
    baseline_frames: list[pd.DataFrame] = []
    recon_rows: list[dict[str, Any]] = []
    eval_truth: dict[str, dict[str, int]] = {}
    for period in periods:
        pid = str(period["period_id"])
        y_train, test_meta = _period_train_eval(meta, period)
        y_test = test_meta["label"].to_numpy(dtype=int)
        bl = metrics.score_registry_baseline(
            "stratified_dummy_train_prior", y_train, y_test, seed=seeds[0]
        )
        recon_rows.append({"period_id": pid, "macro_f1": float(bl["macro_f1"])})
        eval_truth[pid] = {"n": int(len(y_test)), "pos": int(y_test.sum())}
        for seed in seeds:
            baseline_frames.append(pd.DataFrame({
                "baseline_id": "stratified_dummy_train_prior",
                "period_id": pid,
                "seed": int(seed),
                "y_true": y_test,
                "y_pred": np.asarray(bl["predictions"], dtype=int),
            }))

    # 3a. SELF-CHECK: reconstructed dummy macro-F1 == run's stored baselines.
    dummy_check: dict[str, Any] = {"performed": False, "max_abs_diff": None}
    if baselines_csv:
        stored = pd.read_csv(baselines_csv)
        stored = stored[stored["baseline_id"] == "stratified_dummy_train_prior"]
        stored_map = stored.set_index("period_id")["macro_f1"].astype(float).to_dict()
        diffs = []
        for r in recon_rows:
            assert r["period_id"] in stored_map, (
                f"period {r['period_id']} missing from stored baselines"
            )
            diffs.append(abs(r["macro_f1"] - stored_map[r["period_id"]]))
        max_diff = max(diffs)
        dummy_check = {"performed": True, "max_abs_diff": max_diff}
        assert max_diff <= max(dummy_tol, 1e-9), (
            f"dummy reconstruction mismatch (max |diff|={max_diff}); "
            "row-pooled value NOT trusted"
        )

    # 3b. Load candidate predictions; verify eval coverage matches the data context.
    preds = pd.read_csv(predictions_csv)
    cand = preds[preds["table_row_id"] == judged_row].copy()
    assert not cand.empty, f"no predictions for judged row {judged_row!r}"
    for pid, truth in eval_truth.items():
        # one seed's worth of candidate rows per period == the eval set
        per = cand[(cand["period_id"] == pid) & (cand["seed"] == seeds[0])]
        assert len(per) == truth["n"], (
            f"period {pid}: candidate rows {len(per)} != data-context eval {truth['n']}"
        )
        assert int(per["y_true"].sum()) == truth["pos"], (
            f"period {pid}: candidate positives != data-context positives"
        )

    # 4. Protocol row-pooled pooled_delta (same helper the runner now uses).
    pooled_delta_row_pooled = gw._row_pooled_pooled_delta(
        [cand], baseline_frames, judged_row
    )
    assert pooled_delta_row_pooled is not None, "row-pooled computation returned None"

    # Equal-weight cross-check (per-(period,seed) candidate-vs-dummy delta mean).
    dummy_mf1 = {r["period_id"]: r["macro_f1"] for r in recon_rows}
    cell_deltas: list[float] = []
    period_seed_delta: dict[str, list[float]] = {}
    for (pid, seed), grp in cand.groupby(["period_id", "seed"]):
        cf1 = metrics.binary_macro_f1(
            grp["y_true"].to_numpy(dtype=int), grp["y_pred"].to_numpy(dtype=int)
        )
        d = float(cf1) - dummy_mf1[str(pid)]
        cell_deltas.append(d)
        period_seed_delta.setdefault(str(pid), []).append(d)
    pooled_delta_equal_weight = float(np.mean(cell_deltas))
    positive_period_count = sum(
        1 for ds in period_seed_delta.values() if float(np.mean(ds)) > 0
    )

    equal_weight_check: dict[str, Any] = {"performed": False, "abs_diff": None}
    if reported_equal_weight is not None:
        ew_diff = abs(pooled_delta_equal_weight - reported_equal_weight)
        equal_weight_check = {"performed": True, "abs_diff": ew_diff}

    decision_unchanged = (
        positive_period_count >= int(config["predeclared_criteria"]
                                     ["positive_period_count_minimum"])
        and pooled_delta_row_pooled > 0
    )
    return {
        "run_predictions_csv": predictions_csv,
        "judged_row": judged_row,
        "seeds": seeds,
        "pooled_delta_row_pooled": pooled_delta_row_pooled,
        "pooled_delta_equal_weight": pooled_delta_equal_weight,
        "reported_equal_weight": reported_equal_weight,
        "positive_period_count": positive_period_count,
        "row_pooled_sign_positive": pooled_delta_row_pooled > 0,
        "met_decision_holds_under_row_pooled": bool(decision_unchanged),
        "dummy_reconstruction_check": dummy_check,
        "equal_weight_crosscheck": equal_weight_check,
        "per_period_dummy_macro_f1": dummy_mf1,
    }


if __name__ == "__main__":  # pragma: no cover - Colab/CLI convenience
    import argparse
    import json
    import sys
    from pathlib import Path

    import yaml

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, help="v2.1 runtime config YAML/JSON")
    ap.add_argument("--predictions", required=True, help="v2_1_predictions.csv")
    ap.add_argument("--baselines", default=None, help="v2_1_same_row_baselines.csv")
    args = ap.parse_args()

    text = Path(args.config).read_text(encoding="utf-8")
    cfg = json.loads(text) if args.config.endswith(".json") else yaml.safe_load(text)
    out = recompute_and_verify(cfg, args.predictions, args.baselines)
    json.dump(out, sys.stdout, indent=2, default=float)
    print()

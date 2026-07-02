"""Semi-synthetic planted-label injection for the train-domain positive control.

This module owns the SYNTHETIC positive-control mechanism only:

* the planted, feature-measurable label rule and its per-row deterministic
  relabeling (``inject_planted_labels``),
* the hard train-domain date-bound guards (``assert_train_domain_only``),
* the real-run null-band reader and the predeclared pass/fail evaluator.

It never modifies, wraps, or re-implements the real label / feature / window
mechanism. Real-pipeline construction (labels, features, windows, folds,
baselines, fits) is imported from the existing domain modules by the stage
entry point ``stages/synthetic_positive_control.py``; a divergent label or
window implementation here would invalidate the control.

Every function in this module operates on eligible TRAIN rows only. The
experiment invariant is enforced in code: no row at or after
``TRAIN_END_EXCLUSIVE`` (2013-09-16) may ever be touched, which also implies
zero contact with the official validation split and with post-2017 data.
Outputs of this control are protocol-validation evidence about the
measurement chain, never market evidence about any model.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from lst_models.metrics import (
    block_delta_macro_f1,
    compute_metric_lcb,
    same_row_delta_sentinels,
    score_classifier,
    score_registry_baseline,
    ticker_delta_macro_f1,
)
from lst_models.windows import (
    cap_indices,
    fold_indices,
    materialize_window_matrix,
    sample_id_hash,
)


TRAIN_START = pd.Timestamp("1998-01-02")
TRAIN_END_EXCLUSIVE = pd.Timestamp("2013-09-16")
OFFICIAL_VALIDATION_START = pd.Timestamp("2013-09-16")
CLOSED_HOLDOUT_TEST_START = pd.Timestamp("2017-01-25")

PLANTED_RULE_ID = "sign_of_day_local_log_return_at_target_bar"
PLANTED_RULE_FEATURE = "log_return"
MAX_PLANTED_STRENGTH = 0.5

REGISTRY_BASELINES = (
    "stratified_dummy_train_prior",
    "majority_train_prior",
    "constant_up",
    "constant_down",
)

TRIAL_LEDGER_COLUMNS = [
    "trial_id", "arm_id", "planted_strength", "candidate_id", "feature_set",
    "feature_columns_json", "window_size", "model_family", "probe_id",
    "hpo_profile_id", "hpo_profile_params_json", "fold_id", "seed", "fit_status",
    "n_train_samples", "n_eval_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "sample_id_hash", "baseline_id", "baseline_fit_status",
    "baseline_macro_f1", "baseline_balanced_accuracy", "baseline_accuracy",
    "baseline_roc_auc", "baseline_mcc", "macro_f1", "balanced_accuracy",
    "accuracy", "roc_auc", "mcc", "delta_macro_f1_vs_baseline",
    "delta_balanced_accuracy_vs_baseline", "positive_ticker_count",
    "ticker_delta_macro_f1_json", "block_delta_macro_f1_json",
    "requested_device", "resolved_device", "device_fallback_reason",
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason", "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash", "error_message",
]

BASELINE_CONTROL_COLUMNS = [
    "arm_id", "planted_strength", "candidate_id", "fold_id", "seed", "baseline_id",
    "fit_status", "n_train_samples", "n_eval_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "sample_id_hash", "macro_f1", "balanced_accuracy",
    "accuracy", "roc_auc", "mcc", "error_message",
]

SENTINEL_LEDGER_COLUMNS = [
    "arm_id", "planted_strength", "fold_id", "seed", "observed_delta",
    "label_shuffle_mean", "label_shuffle_sd", "label_shuffle_p95",
    "label_shuffle_p_value", "time_reverse_delta", "n_blocks", "n_perm",
]

ARM_SUMMARY_COLUMNS = [
    "arm_id", "planted_strength", "expected_rows", "completed_rows", "failed_rows",
    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "lcb_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_dummy_macro_f1", "min_positive_ticker_count", "mean_positive_ticker_count",
    "flag_mean_positive", "flag_lcb_positive", "flag_ticker_floor_met", "flags_signal",
    "mean_label_shuffle_p_value", "mean_time_reverse_delta",
    "realized_agreement_rate", "synthetic_up_prior", "synthetic_label_sha256",
]


def arm_tag(strength: float) -> str:
    """Canonical arm identifier for a planted strength, e.g. 0.02 -> arm_s0p020."""
    return f"arm_s{float(strength):.3f}".replace(".", "p")


def require_frozen_train_boundaries(split_freeze: Mapping[str, Any]) -> None:
    """Fail closed unless the frozen Stage 00 split artifact matches the
    preregistered train-domain boundaries this control is allowed to touch."""
    expected = {
        "train_start": TRAIN_START,
        "train_end": TRAIN_END_EXCLUSIVE,
        "validation_start": OFFICIAL_VALIDATION_START,
        "closed_holdout_test_start": CLOSED_HOLDOUT_TEST_START,
    }
    for field, expected_value in expected.items():
        observed = split_freeze.get(field)
        if observed is None or pd.Timestamp(str(observed)) != expected_value:
            raise ValueError(
                "synthetic positive control blocked: frozen split boundary "
                f"{field}={observed!r} does not match the preregistered "
                f"{expected_value.date().isoformat()}"
            )


def assert_train_domain_only(
    frame: pd.DataFrame,
    timestamp_columns: Sequence[str],
    *,
    stage_label: str,
) -> None:
    """Hard train-domain guard: every timestamp in the named columns must be
    strictly before ``TRAIN_END_EXCLUSIVE`` (2013-09-16).

    This makes contact with the official validation split (>= 2013-09-16) and
    with post-2017 rows (>= 2017-01-25) impossible, not merely discouraged.
    Raises ``ValueError`` naming the offending column and timestamp. At least
    one named column must exist in the frame.
    """
    if frame.empty:
        raise ValueError(f"{stage_label} blocked: empty frame in train-domain guard")
    present = [column for column in timestamp_columns if column in frame.columns]
    if not present:
        raise ValueError(
            f"{stage_label} blocked: none of the timestamp columns "
            f"{list(timestamp_columns)} exist for the train-domain guard"
        )
    for column in present:
        values = pd.to_datetime(frame[column])
        max_timestamp = values.max()
        if max_timestamp >= TRAIN_END_EXCLUSIVE:
            raise ValueError(
                f"{stage_label} blocked: {column} contains {max_timestamp.isoformat()} "
                f">= train_end_exclusive {TRAIN_END_EXCLUSIVE.date().isoformat()}; "
                "the synthetic positive control is train-domain only (zero official "
                "validation contact, zero post-2017 contact)"
            )
        min_timestamp = values.min()
        if min_timestamp < TRAIN_START:
            raise ValueError(
                f"{stage_label} blocked: {column} contains {min_timestamp.isoformat()} "
                f"< train_start {TRAIN_START.date().isoformat()}"
            )
    if "split" in frame.columns:
        observed_splits = sorted(set(frame["split"].astype(str)))
        if observed_splits != ["train"]:
            raise ValueError(
                f"{stage_label} blocked: expected split=train rows only, got {observed_splits}"
            )


def planted_rule_values(
    feature_frame: pd.DataFrame, events: pd.DataFrame
) -> tuple[np.ndarray, int]:
    """Planted rule r for every eligible event row, from the REAL feature frame.

    r = 1 when the target bar's day-local ``log_return`` is strictly positive,
    else 0 (non-finite values map to 0 and are counted). The rule reads only
    close[t-1] and close[t], both at or before the window end, so it is
    measurable at prediction time and leaks nothing from the label horizon.
    Returns ``(rule_values, rule_nan_count)`` aligned to ``events`` row order.
    """
    bars = feature_frame.loc[:, ["ticker", "timestamp", PLANTED_RULE_FEATURE]].rename(
        columns={"timestamp": "target_timestamp"}
    )
    merged = events.loc[:, ["sample_id", "ticker", "target_timestamp"]].merge(
        bars,
        on=["ticker", "target_timestamp"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    unmatched = merged.loc[merged["_merge"] != "both", "sample_id"]
    if not unmatched.empty:
        preview = ", ".join(str(sample_id) for sample_id in unmatched.head(5))
        raise ValueError(
            "synthetic positive control blocked: "
            f"{len(unmatched)} eligible event rows have no matching feature bar "
            f"(first offenders: {preview})"
        )
    values = merged[PLANTED_RULE_FEATURE].to_numpy(dtype=float)
    finite = np.isfinite(values)
    rule = np.where(finite & (values > 0.0), 1, 0).astype(int)
    return rule, int((~finite).sum())


def relabel_uniforms(
    sample_ids: Sequence[Any], *, injection_seed: int, arm_id: str
) -> np.ndarray:
    """Deterministic per-row uniforms in [0, 1) keyed by sha256 of
    ``injection_seed|arm_id|sample_id``.

    Order-invariant: the uniform for a row depends only on its identity, never
    on processing order, so the frozen synthetic label set per arm is exactly
    reproducible and auditable.
    """
    denominator = float(2**64)
    values = np.empty(len(sample_ids), dtype=float)
    for position, sample_id in enumerate(sample_ids):
        digest = hashlib.sha256(
            f"{int(injection_seed)}|{arm_id}|{sample_id}".encode("utf-8")
        ).digest()
        values[position] = int.from_bytes(digest[:8], "big") / denominator
    return values


def inject_planted_labels(
    train_events: pd.DataFrame,
    rule_values: np.ndarray,
    rule_nan_count: int,
    *,
    strength: float,
    injection_seed: int,
    arm_id: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Relabel eligible train rows to agree with the planted rule with
    probability ``0.5 + strength``; everything except the ``label`` column is
    untouched.

    * ``strength = 0`` makes every label an independent fair coin flip
      (P(label = rule) = 0.5 exactly), i.e. a true null with no
      feature-label coupling.
    * ``strength = s > 0`` produces P(label = rule | features) = 0.5 + s with
      an approximately balanced class prior, so a model that fully learns the
      rule tops out near accuracy 0.5 + s and the same-row macro-F1 delta over
      the stratified dummy has ceiling approximately s.

    Eligibility, features, timestamps, validity flags, and row identity are
    never modified; only ``label`` changes. Returns the relabeled copy plus an
    injection-stats record (realized agreement rate, synthetic class prior,
    synthetic label sha256).
    """
    if not 0.0 <= float(strength) <= MAX_PLANTED_STRENGTH:
        raise ValueError(
            f"planted strength must be within [0.0, {MAX_PLANTED_STRENGTH}], got {strength}"
        )
    if len(rule_values) != len(train_events):
        raise ValueError(
            f"rule values length {len(rule_values)} != eligible event rows {len(train_events)}"
        )
    assert_train_domain_only(
        train_events, ["target_timestamp", "horizon_end_timestamp"],
        stage_label=f"synthetic positive control injection {arm_id}",
    )
    sample_ids = train_events["sample_id"].astype(str).tolist()
    uniforms = relabel_uniforms(sample_ids, injection_seed=injection_seed, arm_id=arm_id)
    agree = uniforms < (0.5 + float(strength))
    rule = np.asarray(rule_values, dtype=int)
    synthetic_labels = np.where(agree, rule, 1 - rule).astype(int)

    relabeled = train_events.copy()
    real_up_prior = float(relabeled["label"].astype(int).mean())
    relabeled["label"] = synthetic_labels
    relabeled["planted_rule_value"] = rule
    label_payload = [
        f"{sample_id}|{label}" for sample_id, label in zip(sample_ids, synthetic_labels)
    ]
    stats = {
        "arm_id": str(arm_id),
        "planted_strength": float(strength),
        "injection_seed": int(injection_seed),
        "rule_id": PLANTED_RULE_ID,
        "rule_feature": PLANTED_RULE_FEATURE,
        "n_rows": int(len(relabeled)),
        "rule_positive_rate": float(rule.mean()),
        "rule_nan_count": int(rule_nan_count),
        "realized_agreement_rate": float(agree.mean()),
        "synthetic_up_prior": float(synthetic_labels.mean()),
        "real_up_prior": real_up_prior,
        "synthetic_label_sha256": sample_id_hash(label_payload),
        "labels_are_synthetic": True,
    }
    return relabeled, stats


def base_trial_row(
    *, arm: Mapping[str, Any], candidate: Mapping[str, Any], model: Mapping[str, Any],
    profile: Mapping[str, Any], fold: Mapping[str, Any], seed: int,
    feature_columns: tuple[str, ...], n_train: int, n_eval: int, train_hash: str,
    eval_hash: str, primary: Mapping[str, Any],
) -> dict[str, Any]:
    """One trial-ledger row with identity, row-contract, and same-row baseline
    fields filled and model fields blank (Stage 02 ledger schema plus arm
    columns)."""
    profile_id = str(profile["profile_id"])
    profile_only = {
        str(key): value for key, value in profile.items() if str(key) != "profile_id"
    }
    row = {column: pd.NA for column in TRIAL_LEDGER_COLUMNS}
    row.update(
        {
            "trial_id": (
                f"{arm['arm_id']}__{candidate['candidate_id']}__{model['family']}"
                f"__{profile_id}__{fold['fold_id']}__seed{seed}"
            ),
            "arm_id": str(arm["arm_id"]),
            "planted_strength": float(arm["strength"]),
            "candidate_id": str(candidate["candidate_id"]),
            "feature_set": str(candidate["feature_set"]),
            "feature_columns_json": json.dumps(list(feature_columns)),
            "window_size": int(candidate["window_size"]),
            "model_family": str(model["family"]),
            "probe_id": str(model["probe_id"]),
            "hpo_profile_id": profile_id,
            "hpo_profile_params_json": json.dumps(profile_only, sort_keys=True),
            "fold_id": str(fold["fold_id"]),
            "seed": int(seed),
            "fit_status": "not_started",
            "n_train_samples": int(n_train),
            "n_eval_samples": int(n_eval),
            "train_sample_id_hash": train_hash,
            "eval_sample_id_hash": eval_hash,
            "sample_id_hash": eval_hash,
            "baseline_id": "stratified_dummy_train_prior",
            "baseline_fit_status": primary["fit_status"],
            "baseline_macro_f1": primary["macro_f1"],
            "baseline_balanced_accuracy": primary["balanced_accuracy"],
            "baseline_accuracy": primary["accuracy"],
            "baseline_roc_auc": primary["roc_auc"],
            "baseline_mcc": primary["mcc"],
            "ticker_delta_macro_f1_json": "{}",
            "block_delta_macro_f1_json": "{}",
            "error_message": "",
        }
    )
    return row


_FIT_OUTCOME_KEYS = (
    "fit_status", "error_message", "best_iteration", "early_stopping_source",
    "early_stopping_used", "early_stopping_reason",
    "early_stopping_train_sample_id_hash", "early_stopping_eval_sample_id_hash",
    "requested_device", "resolved_device", "device_fallback_reason",
)


def score_arm_trials(
    *,
    arm: Mapping[str, Any],
    dataset: Any,
    folds: pd.DataFrame,
    seeds: Sequence[int],
    candidate: Mapping[str, Any],
    model: Mapping[str, Any],
    profile: Mapping[str, Any],
    config: Mapping[str, Any],
    sample_policy: Mapping[str, Any],
    sentinel_config: Mapping[str, Any],
    fit_function: Callable[..., Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Score one arm over every fold x seed with the protocol's own contract.

    Reuses the real machinery end to end: capped fold rows
    (``windows.cap_indices``, label-stratified exactly as in Stage 02), the
    four registry baselines recomputed on the arm's synthetic labels, the
    provided fit function (``fitting.fit_stage_control`` in production), the
    same-row delta and per-ticker/block deltas, and the label-shuffle /
    time-reverse sentinels on the resulting predictions. Returns
    ``(trial_rows, baseline_rows, sentinel_rows)``.
    """
    trial_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    sentinel_rows: list[dict[str, Any]] = []
    feature_columns = tuple(str(column) for column in candidate["feature_columns"])
    window_size = int(candidate["window_size"])

    for fold in folds.to_dict(orient="records"):
        train_idx, eval_idx = fold_indices(dataset.metadata, fold)
        train_idx = cap_indices(
            dataset.metadata, train_idx, int(sample_policy["max_train_samples_per_fold"])
        )
        eval_idx = cap_indices(
            dataset.metadata, eval_idx, int(sample_policy["max_eval_samples_per_fold"])
        )
        train_meta = dataset.metadata.iloc[train_idx].copy().reset_index(drop=True)
        eval_meta = dataset.metadata.iloc[eval_idx].copy().reset_index(drop=True)
        x_train = materialize_window_matrix(dataset, train_idx)
        x_eval = materialize_window_matrix(dataset, eval_idx)
        train_hash = sample_id_hash(train_meta["sample_id"].tolist())
        eval_hash = sample_id_hash(eval_meta["sample_id"].tolist())
        y_train = train_meta["label"].to_numpy(dtype=int)
        y_eval = eval_meta["label"].to_numpy(dtype=int)
        for seed in (int(value) for value in seeds):
            baselines = {
                baseline_id: score_registry_baseline(baseline_id, y_train, y_eval, seed)
                for baseline_id in REGISTRY_BASELINES
            }
            for baseline_id, score in baselines.items():
                baseline_rows.append(
                    {
                        "arm_id": str(arm["arm_id"]),
                        "planted_strength": float(arm["strength"]),
                        "candidate_id": str(candidate["candidate_id"]),
                        "fold_id": str(fold["fold_id"]),
                        "seed": seed,
                        "baseline_id": baseline_id,
                        "fit_status": score["fit_status"],
                        "n_train_samples": int(len(train_meta)),
                        "n_eval_samples": int(len(eval_meta)),
                        "train_sample_id_hash": train_hash,
                        "eval_sample_id_hash": eval_hash,
                        "sample_id_hash": eval_hash,
                        "macro_f1": score["macro_f1"],
                        "balanced_accuracy": score["balanced_accuracy"],
                        "accuracy": score["accuracy"],
                        "roc_auc": score["roc_auc"],
                        "mcc": score["mcc"],
                        "error_message": score["error_message"],
                    }
                )
            primary = baselines["stratified_dummy_train_prior"]
            row = base_trial_row(
                arm=arm, candidate=candidate, model=model, profile=profile, fold=fold,
                seed=seed, feature_columns=feature_columns, n_train=len(train_meta),
                n_eval=len(eval_meta), train_hash=train_hash, eval_hash=eval_hash,
                primary=primary,
            )
            if primary["fit_status"] != "completed_baseline":
                row["fit_status"] = "skipped_baseline_failed"
                row["error_message"] = str(primary["error_message"])
                trial_rows.append(row)
                continue
            outcome = fit_function(
                str(model["probe_id"]), profile, x_train, train_meta, x_eval, config,
                seed, window_size, len(feature_columns),
            )
            row.update({key: outcome.get(key) for key in _FIT_OUTCOME_KEYS})
            if outcome.get("fit_status") == "completed":
                predictions = np.asarray(outcome["predictions"], dtype=int)
                scored = score_classifier(y_eval, predictions, y_score=outcome.get("scores"))
                baseline_predictions = np.asarray(primary["predictions"], dtype=int)
                ticker_deltas, positive_count = ticker_delta_macro_f1(
                    eval_meta, predictions, baseline_predictions
                )
                block_deltas = block_delta_macro_f1(eval_meta, predictions, baseline_predictions)
                row.update(scored)
                row["delta_macro_f1_vs_baseline"] = float(scored["macro_f1"] - primary["macro_f1"])
                row["delta_balanced_accuracy_vs_baseline"] = float(
                    scored["balanced_accuracy"] - primary["balanced_accuracy"]
                )
                row["positive_ticker_count"] = int(positive_count)
                row["ticker_delta_macro_f1_json"] = json.dumps(ticker_deltas, sort_keys=True)
                row["block_delta_macro_f1_json"] = json.dumps(block_deltas, sort_keys=True)
                block_ids = (
                    eval_meta["ticker"].astype(str) + "|" + eval_meta["trading_day"].astype(str)
                ).to_numpy()
                sentinel = same_row_delta_sentinels(
                    y_eval, predictions, baseline_predictions, block_ids,
                    n_perm=int(sentinel_config["n_perm"]), seed=int(sentinel_config["seed"]),
                )
                sentinel_rows.append(
                    {
                        "arm_id": str(arm["arm_id"]),
                        "planted_strength": float(arm["strength"]),
                        "fold_id": str(fold["fold_id"]),
                        "seed": seed,
                        **sentinel,
                    }
                )
            trial_rows.append(row)
    return trial_rows, baseline_rows, sentinel_rows


def real_control_null_band(
    trial_ledger: pd.DataFrame,
    *,
    candidate_id: str,
    model_family: str,
    hpo_profile_id: str,
    expected_rows: int,
) -> dict[str, Any]:
    """Null band from the frozen REAL Stage 02 train-inner control rows.

    The band is the maximum absolute same-row macro-F1 delta over the
    completed fold-by-seed rows of the identical machinery (same candidate,
    family, and profile) on the real near-null labels — the observed
    train-inner control spread. No number is asserted here; the value is read
    from the frozen artifact at run time.
    """
    required_columns = {
        "candidate_id", "model_family", "hpo_profile_id", "fit_status",
        "delta_macro_f1_vs_baseline",
    }
    missing = sorted(required_columns - set(trial_ledger.columns))
    if missing:
        raise ValueError(f"real Stage 02 trial ledger missing columns: {missing}")
    rows = trial_ledger.loc[
        trial_ledger["candidate_id"].astype(str).eq(candidate_id)
        & trial_ledger["model_family"].astype(str).eq(model_family)
        & trial_ledger["hpo_profile_id"].astype(str).eq(hpo_profile_id)
    ]
    if len(rows) != int(expected_rows):
        raise ValueError(
            "null-band source mismatch: expected "
            f"{int(expected_rows)} real Stage 02 rows for {candidate_id}/{model_family}/"
            f"{hpo_profile_id}, found {len(rows)}"
        )
    if not rows["fit_status"].astype(str).eq("completed").all():
        raise ValueError(
            f"null-band source rows for {candidate_id}/{model_family}/{hpo_profile_id} "
            "contain non-completed fits; cannot define the null band"
        )
    deltas = rows["delta_macro_f1_vs_baseline"].astype(float)
    if not np.isfinite(deltas.to_numpy()).all():
        raise ValueError("null-band source rows contain non-finite deltas")
    return {
        "source_candidate_id": str(candidate_id),
        "source_model_family": str(model_family),
        "source_hpo_profile_id": str(hpo_profile_id),
        "n_rows": int(len(rows)),
        "max_abs_delta": float(deltas.abs().max()),
        "mean_delta": float(deltas.mean()),
    }


def arm_delta_aggregates(
    trial_ledger: pd.DataFrame, *, arm_id: str
) -> dict[str, Any]:
    """Fold-by-seed aggregates of the same-row delta for one arm.

    ``lcb`` is the Student-t lower bound over the completed fold-by-seed
    deltas (``metrics.compute_metric_lcb``), the same conservative statistic
    Stage 02 uses; descriptive, not a significance test.
    """
    rows = trial_ledger.loc[trial_ledger["arm_id"].astype(str).eq(str(arm_id))]
    completed = rows.loc[rows["fit_status"].astype(str).eq("completed")]
    deltas = completed["delta_macro_f1_vs_baseline"].astype(float).to_numpy()
    ticker_counts = completed["positive_ticker_count"].astype(float).to_numpy()
    return {
        "arm_id": str(arm_id),
        "expected_rows": int(len(rows)),
        "completed_rows": int(len(completed)),
        "failed_rows": int(len(rows) - len(completed)),
        "mean_delta": float(np.mean(deltas)) if len(deltas) else float("nan"),
        "lcb_delta": compute_metric_lcb(deltas) if len(deltas) else float("nan"),
        "min_positive_ticker_count": float(np.min(ticker_counts))
        if len(ticker_counts)
        else float("nan"),
        "mean_positive_ticker_count": float(np.mean(ticker_counts))
        if len(ticker_counts)
        else float("nan"),
        "mean_dummy_macro_f1": float(completed["baseline_macro_f1"].astype(float).mean())
        if len(completed)
        else float("nan"),
    }


def flags_signal_fields(
    aggregate: Mapping[str, Any], *, minimum_positive_ticker_count: int
) -> dict[str, bool]:
    """Detection-flag fields for one arm aggregate (preregistration section 6).

    An arm "flags a signal" only when the fold-by-seed mean delta is positive,
    its Student-t LCB is positive, and every completed trial row meets the
    predeclared per-ticker positivity floor — the same evidence pattern the
    real protocol requires before freezing a candidate.
    """
    mean_delta = float(aggregate["mean_delta"])
    lcb_delta = float(aggregate["lcb_delta"])
    min_ticker = float(aggregate["min_positive_ticker_count"])
    flag_mean_positive = bool(np.isfinite(mean_delta) and mean_delta > 0.0)
    flag_lcb_positive = bool(np.isfinite(lcb_delta) and lcb_delta > 0.0)
    flag_ticker_floor_met = bool(
        np.isfinite(min_ticker) and min_ticker >= float(minimum_positive_ticker_count)
    )
    return {
        "flag_mean_positive": flag_mean_positive,
        "flag_lcb_positive": flag_lcb_positive,
        "flag_ticker_floor_met": flag_ticker_floor_met,
        "flags_signal": flag_mean_positive and flag_lcb_positive and flag_ticker_floor_met,
    }


def evaluate_predeclared_criteria(
    arm_aggregates: Mapping[float, Mapping[str, Any]],
    *,
    null_band_abs: float,
    minimum_positive_ticker_count: int,
    null_strength: float,
    detection_strengths: Sequence[float],
    monotone_strengths: Sequence[float],
    threshold_strength: float,
) -> dict[str, Any]:
    """Apply the preregistered pass/fail rules to per-arm delta aggregates.

    ``arm_aggregates`` maps planted strength -> the ``arm_delta_aggregates``
    record for that arm. Rules (preregistration section 6):

    * P1 null honesty: the ``null_strength`` arm must NOT flag a signal; its
      LCB must be <= 0 and its |mean delta| must sit within ``null_band_abs``.
    * P2 monotone response: mean deltas strictly increase across
      ``monotone_strengths``.
    * P3 detection: every ``detection_strengths`` arm flags a signal
      (mean > 0, LCB > 0, per-trial positive-ticker floor met).

    The ``threshold_strength`` arm (the observed-edge-scale arm) is reported,
    never gated. Any arm with incomplete fit rows voids the scientific
    reading (``outcome = incomplete_run_fix_and_rerun``).
    """
    declared = sorted(float(strength) for strength in arm_aggregates)
    for required in [float(null_strength), float(threshold_strength), *detection_strengths]:
        if float(required) not in declared:
            raise ValueError(f"criteria reference strength {required} not among arms {declared}")

    per_arm: dict[str, Any] = {}
    incomplete = False
    for strength in declared:
        aggregate = arm_aggregates[strength]
        flags = flags_signal_fields(
            aggregate, minimum_positive_ticker_count=minimum_positive_ticker_count
        )
        incomplete = incomplete or int(aggregate["completed_rows"]) < int(
            aggregate["expected_rows"]
        )
        per_arm[f"{strength:.3f}"] = {
            "arm_id": str(aggregate["arm_id"]),
            "planted_strength": float(strength),
            "mean_delta": float(aggregate["mean_delta"]),
            "lcb_delta": float(aggregate["lcb_delta"]),
            "min_positive_ticker_count": float(aggregate["min_positive_ticker_count"]),
            "completed_rows": int(aggregate["completed_rows"]),
            "expected_rows": int(aggregate["expected_rows"]),
            **flags,
        }

    null_record = per_arm[f"{float(null_strength):.3f}"]
    p1_lcb_nonpositive = not null_record["flag_lcb_positive"]
    p1_within_band = bool(
        np.isfinite(null_record["mean_delta"])
        and abs(null_record["mean_delta"]) <= float(null_band_abs)
    )
    p1_pass = bool(p1_lcb_nonpositive and p1_within_band and not null_record["flags_signal"])

    monotone_means = [
        per_arm[f"{float(strength):.3f}"]["mean_delta"] for strength in monotone_strengths
    ]
    p2_pass = bool(
        all(np.isfinite(value) for value in monotone_means)
        and all(
            monotone_means[index] < monotone_means[index + 1]
            for index in range(len(monotone_means) - 1)
        )
    )
    p3_pass = bool(
        all(per_arm[f"{float(strength):.3f}"]["flags_signal"] for strength in detection_strengths)
    )

    if incomplete:
        outcome = "incomplete_run_fix_and_rerun"
    elif null_record["flags_signal"] and not p3_pass:
        outcome = "fail_manufacturing_and_insensitive"
    elif null_record["flags_signal"]:
        outcome = "fail_manufacturing"
    elif not p3_pass:
        outcome = "fail_insensitive"
    elif not p2_pass or not p1_pass:
        outcome = "fail_nonmonotone_or_null_band"
    else:
        outcome = "pass"

    threshold_record = per_arm[f"{float(threshold_strength):.3f}"]
    return {
        "null_band_abs": float(null_band_abs),
        "minimum_positive_ticker_count": int(minimum_positive_ticker_count),
        "null_strength": float(null_strength),
        "detection_strengths": [float(value) for value in detection_strengths],
        "monotone_strengths": [float(value) for value in monotone_strengths],
        "threshold_strength": float(threshold_strength),
        "per_arm": per_arm,
        "p1_null_arm_lcb_nonpositive": p1_lcb_nonpositive,
        "p1_null_arm_within_band": p1_within_band,
        "p1_pass": p1_pass,
        "p2_monotone_pass": p2_pass,
        "p3_detection_pass": p3_pass,
        "threshold_arm_flags_signal": bool(threshold_record["flags_signal"]),
        "overall_outcome": outcome,
        "evidence_status": "synthetic_positive_control_protocol_validation_only",
    }

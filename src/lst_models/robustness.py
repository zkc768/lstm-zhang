"""Train-domain robustness-experiment mechanics (band/horizon scan + embargo).

This module owns ONLY the experiment-specific measurement mechanics shared by
the two preregistered TRAIN-DOMAIN robustness experiments:

* ``v2_band_horizon_sensitivity`` — the per-cell label-rebuild adapter around
  the frozen Stage 00 label operator (``labels.make_direction_labels`` is
  IMPORTED, never re-implemented), cell-spec validation, the frozen-cell
  parity gate, and the predeclared sign-stability reading rules. The scan is
  never a tuning pass: no cell is preferred, cells are never ranked, and no
  alternative (band, horizon) is ever recommended.
* ``v2_embargo_robustness`` — the one-trading-day eval-side embargo row filter
  over the UNCHANGED Stage 02 fold boundaries, and the predeclared
  margin-shrinkage reading rules.

Real-pipeline construction (bars, features, windows, folds, baselines, fits)
is imported from the existing domain modules by the stage entry points. Both
experiments run on eligible TRAIN rows only (1998-01-02 through 2013-09-16,
end-exclusive); the hard date-bound guards are the shared
``synthetic_control.assert_train_domain_only`` and
``synthetic_control.require_frozen_train_boundaries``, applied by the stage
entry points to every bar, event, window, and fold frame. Zero contact with
the official validation split, zero contact with post-2017 rows.

Every reading rule below is DESCRIPTIVE. Nothing here is a significance test,
a selection event, or a model comparison across cells.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from lst_models.artifacts import (
    read_json_object,
    require_artifacts,
    require_run_id_chain,
    require_safety_flags,
)
from lst_models.config import load_yaml, require_mapping, resolve_repo_path
from lst_models.data import load_sample_event_index, load_stage01_summary, load_train_bars
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.labels import make_direction_labels
from lst_models.metrics import compute_metric_lcb
from lst_models.splits import train_valid_events
from lst_models.synthetic_control import (
    assert_train_domain_only,
    require_frozen_train_boundaries,
)
from lst_models.windows import sample_id_hash


FROZEN_HORIZON_K = 9
FROZEN_BAND_BPS = 3.0
FROZEN_LABEL_OPERATOR = "endpoint_cumulative_return"
FROZEN_CELL_ID = "h09_bps3p0"
RUN_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")

CELL_AXES = ("band", "horizon", "frozen")
EMBARGO_VARIANTS = ("no_embargo", "embargo_1day")
EMBARGO_RULE_ID = "drop_first_eval_trading_day_per_fold"

LABEL_INVALID_COLUMNS = (
    "invalid_missing_future",
    "invalid_cross_trading_day",
    "invalid_irregular_horizon",
    "invalid_cross_split",
    "invalid_no_trade_band",
)


def cell_tag(horizon_k: int, band_bps: float) -> str:
    """Canonical cell id, matching the Stage 00 ``label_config_id`` style:
    (9, 3.0) -> ``h09_bps3p0``."""
    band_text = f"{float(band_bps):.1f}".replace(".", "p")
    return f"h{int(horizon_k):02d}_bps{band_text}"


def require_frozen_label_policy(label_policy: Mapping[str, Any]) -> None:
    """Fail closed unless the frozen Stage 00 label policy matches the
    preregistered frozen cell this experiment pivots on."""
    observed_operator = label_policy.get("operator")
    if str(observed_operator) != FROZEN_LABEL_OPERATOR:
        raise ValueError(
            "train-domain robustness experiment blocked: frozen Stage 00 label "
            f"policy operator={observed_operator!r} does not match the "
            f"preregistered {FROZEN_LABEL_OPERATOR!r}"
        )
    for field, expected_value in (
        ("horizon_k", float(FROZEN_HORIZON_K)),
        ("no_trade_band_bps", float(FROZEN_BAND_BPS)),
    ):
        observed = float_or_none(label_policy.get(field))
        if observed is None or observed != expected_value:
            raise ValueError(
                "train-domain robustness experiment blocked: frozen Stage 00 "
                f"label policy {field}={label_policy.get(field)!r} does not match "
                f"the preregistered frozen value {expected_value!r}"
            )


def float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_cell_specs(cells: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate the preregistered band/horizon cross (never a grid).

    Every cell must sit on one of the two axes through the frozen cell:
    ``horizon_k == FROZEN_HORIZON_K`` (band axis) or
    ``no_trade_band_bps == FROZEN_BAND_BPS`` (horizon axis). Exactly one cell
    is the frozen cell itself. Cell ids must be the canonical tags. Returns
    normalized cell dicts in declared order.
    """
    if not isinstance(cells, Sequence) or len(cells) < 3:
        raise ValueError("label_scan.cells must declare at least three cells (a cross)")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    frozen_count = 0
    for cell in cells:
        horizon_k = int(cell["horizon_k"])
        band_bps = float(cell["no_trade_band_bps"])
        cell_id = str(cell["cell_id"])
        axis = str(cell.get("cell_axis", ""))
        expected_id = cell_tag(horizon_k, band_bps)
        if cell_id != expected_id:
            raise ValueError(
                f"cell_id {cell_id!r} must equal canonical tag {expected_id!r}"
            )
        if cell_id in seen_ids:
            raise ValueError(f"duplicate cell_id {cell_id!r}")
        seen_ids.add(cell_id)
        is_frozen = horizon_k == FROZEN_HORIZON_K and band_bps == FROZEN_BAND_BPS
        if is_frozen:
            frozen_count += 1
            if axis != "frozen":
                raise ValueError(f"frozen cell {cell_id!r} must declare cell_axis=frozen")
        elif horizon_k == FROZEN_HORIZON_K:
            if axis != "band":
                raise ValueError(f"cell {cell_id!r} sits on the band axis; declare cell_axis=band")
        elif band_bps == FROZEN_BAND_BPS:
            if axis != "horizon":
                raise ValueError(
                    f"cell {cell_id!r} sits on the horizon axis; declare cell_axis=horizon"
                )
        else:
            raise ValueError(
                f"cell {cell_id!r} ({horizon_k}, {band_bps}) is off both axes: the scan "
                "is a cross through the frozen cell, never a grid"
            )
        if horizon_k < 1:
            raise ValueError(f"cell {cell_id!r} horizon_k must be >= 1")
        if band_bps <= 0.0:
            raise ValueError(f"cell {cell_id!r} no_trade_band_bps must be > 0")
        normalized.append(
            {
                "cell_id": cell_id,
                "horizon_k": horizon_k,
                "no_trade_band_bps": band_bps,
                "cell_axis": axis,
                "is_frozen_cell": is_frozen,
            }
        )
    if frozen_count != 1:
        raise ValueError(
            f"label_scan.cells must contain exactly one frozen cell "
            f"({FROZEN_HORIZON_K}, {FROZEN_BAND_BPS}); found {frozen_count}"
        )
    return normalized


def rebuild_cell_events(
    train_bars: pd.DataFrame, *, horizon_k: int, band_bps: float
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Rebuild eligible train label events for one (band, horizon) cell.

    Calls the frozen Stage 00 label operator ``labels.make_direction_labels``
    with the cell's policy — label logic is imported, never forked. Returns
    the eligible (valid-label) events in the Stage 00 event-index shape plus a
    per-cell eligibility profile. Band and horizon change row eligibility
    MECHANICALLY (the band drops near-flat rows; a longer horizon invalidates
    more end-of-day rows), so per-cell eligible-row counts are first-class
    outputs, not incidental.
    """
    labeled = make_direction_labels(
        train_bars,
        {
            "operator": FROZEN_LABEL_OPERATOR,
            "horizon_k": int(horizon_k),
            "no_trade_band_bps": float(band_bps),
        },
    )
    profile: dict[str, Any] = {
        "horizon_k": int(horizon_k),
        "no_trade_band_bps": float(band_bps),
        "n_bar_rows": int(len(labeled)),
        "n_eligible_label_rows": int(labeled["valid_label"].sum()),
        "up_rows": int((labeled["label"] == 1).sum()),
        "down_rows": int((labeled["label"] == 0).sum()),
        "n_trading_days": int(labeled.loc[labeled["valid_label"], "trading_day"].nunique()),
    }
    for column in LABEL_INVALID_COLUMNS:
        profile[f"n_{column}"] = int(labeled[column].sum())
    eligible = labeled.loc[labeled["valid_label"]].copy()
    if eligible.empty:
        raise ValueError(
            f"cell ({horizon_k}, {band_bps}) produced zero eligible train label rows"
        )
    profile["up_prior"] = float(eligible["label"].astype(int).mean())
    profile["n_eligible_by_ticker"] = {
        str(ticker): int(count)
        for ticker, count in eligible.groupby("ticker").size().to_dict().items()
    }
    events = eligible.rename(columns={"timestamp": "target_timestamp"})
    events["label"] = events["label"].astype(int)
    events = events.loc[
        :,
        [
            "sample_id",
            "ticker",
            "target_timestamp",
            "trading_day",
            "split",
            "label",
            "horizon_end_timestamp",
            "future_cumulative_return",
        ],
    ]
    events = events.sort_values(
        ["target_timestamp", "ticker", "sample_id"]
    ).reset_index(drop=True)
    return events, profile


def events_identity_sha256(events: pd.DataFrame) -> str:
    """Order-stable identity hash over ``sample_id|label`` rows."""
    ordered = events.sort_values(["target_timestamp", "ticker", "sample_id"])
    payload = [
        f"{sample_id}|{int(label)}"
        for sample_id, label in zip(
            ordered["sample_id"].astype(str), ordered["label"].astype(int)
        )
    ]
    return sample_id_hash(payload)


def require_frozen_cell_event_parity(
    cell_events: pd.DataFrame, frozen_events: pd.DataFrame, *, stage_label: str
) -> None:
    """Fail closed unless the rebuilt frozen-cell events exactly reproduce the
    frozen Stage 00 event index (same rows, same labels).

    This is the anchor that makes the other cells trustworthy: if the rebuild
    chain cannot reproduce the freeze at (3.0 bps, 9 bars), no adjacent cell
    may be read.
    """
    if len(cell_events) != len(frozen_events):
        raise ValueError(
            f"{stage_label} blocked: rebuilt frozen-cell eligible rows "
            f"{len(cell_events)} != frozen Stage 00 event-index rows {len(frozen_events)}"
        )
    rebuilt_ids = sample_id_hash(
        cell_events.sort_values(["target_timestamp", "ticker", "sample_id"])[
            "sample_id"
        ].astype(str).tolist()
    )
    frozen_ids = sample_id_hash(
        frozen_events.sort_values(["target_timestamp", "ticker", "sample_id"])[
            "sample_id"
        ].astype(str).tolist()
    )
    if rebuilt_ids != frozen_ids:
        raise ValueError(
            f"{stage_label} blocked: rebuilt frozen-cell sample_id hash {rebuilt_ids} "
            f"!= frozen Stage 00 event-index hash {frozen_ids}"
        )
    if events_identity_sha256(cell_events) != events_identity_sha256(frozen_events):
        raise ValueError(
            f"{stage_label} blocked: rebuilt frozen-cell labels differ from the "
            "frozen Stage 00 event index on identical rows"
        )


def group_delta_aggregates(
    trial_ledger: pd.DataFrame, *, group_column: str, group_value: str
) -> dict[str, Any]:
    """Fold-by-seed aggregates of the same-row delta for one ledger group.

    ``lcb`` is the Student-t lower bound over completed fold-by-seed deltas
    (``metrics.compute_metric_lcb``) — descriptive, never a significance test.
    Sign counts over the completed rows expose within-group sign instability.
    """
    rows = trial_ledger.loc[trial_ledger[group_column].astype(str).eq(str(group_value))]
    completed = rows.loc[rows["fit_status"].astype(str).eq("completed")]
    deltas = completed["delta_macro_f1_vs_baseline"].astype(float).to_numpy()
    ticker_counts = completed["positive_ticker_count"].astype(float).to_numpy()
    return {
        group_column: str(group_value),
        "expected_rows": int(len(rows)),
        "completed_rows": int(len(completed)),
        "failed_rows": int(len(rows) - len(completed)),
        "mean_delta": float(np.mean(deltas)) if len(deltas) else float("nan"),
        "lcb_delta": compute_metric_lcb(deltas) if len(deltas) else float("nan"),
        "positive_sign_rows": int((deltas > 0.0).sum()),
        "negative_sign_rows": int((deltas < 0.0).sum()),
        "zero_sign_rows": int((deltas == 0.0).sum()),
        "mean_dummy_macro_f1": float(completed["baseline_macro_f1"].astype(float).mean())
        if len(completed)
        else float("nan"),
        "min_positive_ticker_count": float(np.min(ticker_counts))
        if len(ticker_counts)
        else float("nan"),
        "mean_positive_ticker_count": float(np.mean(ticker_counts))
        if len(ticker_counts)
        else float("nan"),
    }


def _mean_sign(mean_delta: float) -> str:
    if not np.isfinite(mean_delta):
        return "undefined"
    if mean_delta > 0.0:
        return "positive"
    if mean_delta < 0.0:
        return "negative"
    return "zero"


def band_horizon_reading(
    trial_ledger: pd.DataFrame, cell_specs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Apply the preregistered E3 reading rules to the per-cell trial rows.

    Rules (preregistration section 6; all DESCRIPTIVE):

    * every cell is reported; cells are NEVER ranked, no cell is preferred,
      and no alternative (band, horizon) is ever recommended;
    * the sign of each cell is the sign of its fold-by-seed mean same-row
      delta; a zero or undefined mean makes the axis sign-unstable;
    * the frozen cell is "not a knife edge" when the sign is stable across
      ALL cells of the band axis AND all cells of the horizon axis;
    * any sign flip is reported honestly and strengthens the paper's stated
      limitation — it never triggers a re-scan, a new cell, or a preference;
    * any incomplete cell voids the scientific reading entirely.
    """
    per_cell: dict[str, Any] = {}
    incomplete = False
    for spec in cell_specs:
        cell_id = str(spec["cell_id"])
        aggregate = group_delta_aggregates(
            trial_ledger, group_column="cell_id", group_value=cell_id
        )
        incomplete = incomplete or (
            int(aggregate["completed_rows"]) < int(aggregate["expected_rows"])
            or int(aggregate["expected_rows"]) == 0
        )
        per_cell[cell_id] = {
            **aggregate,
            "horizon_k": int(spec["horizon_k"]),
            "no_trade_band_bps": float(spec["no_trade_band_bps"]),
            "cell_axis": str(spec["cell_axis"]),
            "is_frozen_cell": bool(spec["is_frozen_cell"]),
            "mean_sign": _mean_sign(float(aggregate["mean_delta"])),
        }

    band_axis = sorted(
        (record for record in per_cell.values() if record["horizon_k"] == FROZEN_HORIZON_K),
        key=lambda record: record["no_trade_band_bps"],
    )
    horizon_axis = sorted(
        (
            record
            for record in per_cell.values()
            if record["no_trade_band_bps"] == FROZEN_BAND_BPS
        ),
        key=lambda record: record["horizon_k"],
    )
    band_signs = [record["mean_sign"] for record in band_axis]
    horizon_signs = [record["mean_sign"] for record in horizon_axis]
    band_defined = all(sign in {"positive", "negative"} for sign in band_signs)
    horizon_defined = all(sign in {"positive", "negative"} for sign in horizon_signs)
    band_axis_sign_stable = bool(band_defined and len(set(band_signs)) == 1)
    horizon_axis_sign_stable = bool(horizon_defined and len(set(horizon_signs)) == 1)

    if incomplete:
        outcome = "incomplete_run_fix_and_rerun"
    elif not band_defined or not horizon_defined:
        outcome = "sign_undefined_on_an_axis_reported_descriptively"
    elif band_axis_sign_stable and horizon_axis_sign_stable:
        outcome = "not_knife_edge_sign_stable_both_axes"
    elif not band_axis_sign_stable and not horizon_axis_sign_stable:
        outcome = "sign_flip_on_both_axes_limitation_strengthened"
    elif not band_axis_sign_stable:
        outcome = "sign_flip_on_band_axis_limitation_strengthened"
    else:
        outcome = "sign_flip_on_horizon_axis_limitation_strengthened"

    return {
        "per_cell": per_cell,
        "band_axis_cell_ids": [record["cell_id"] for record in band_axis],
        "horizon_axis_cell_ids": [record["cell_id"] for record in horizon_axis],
        "band_axis_signs": band_signs,
        "horizon_axis_signs": horizon_signs,
        "band_axis_sign_stable": band_axis_sign_stable,
        "horizon_axis_sign_stable": horizon_axis_sign_stable,
        "frozen_cell_id": FROZEN_CELL_ID,
        "overall_outcome": outcome,
        "no_cell_preferred": True,
        "no_cell_ranked": True,
        "no_alternative_cell_recommended": True,
        "frozen_protocol_values_unchanged": True,
        "evidence_status": "train_inner_protocol_sensitivity_scan_no_cell_selected",
    }


@dataclass(frozen=True)
class RobustnessInputs:
    """Frozen upstream inputs shared by the two train-domain robustness stages."""

    stage00_paths: Mapping[str, Path]
    stage01_paths: Mapping[str, Path]
    stage02_paths: Mapping[str, Path]
    stage01_manifest: Mapping[str, Any]
    raw_manifest: Mapping[str, Any]
    split_freeze: Mapping[str, Any]
    candidate: Mapping[str, Any]
    frozen_train_events: pd.DataFrame
    train_bars: pd.DataFrame
    feature_frame: pd.DataFrame
    stage01_summary: pd.DataFrame
    stage02_plan_ledger: pd.DataFrame


def load_robustness_inputs(config: Mapping[str, Any], *, stage_label: str) -> RobustnessInputs:
    """Resolve, gate, and load the frozen Stage 00/01/02 inputs both
    robustness stages consume: exact-run-id artifacts, safety flags, run-id
    chain, frozen split/label policy, the frozen primary candidate, the raw
    train bars, the rebuilt feature frame, the Stage 01 summary, and the
    Stage 02 plan ledger. Every loaded frame passes the hard train-domain
    date-bound guard."""
    inputs = require_mapping(config["inputs"], "inputs")
    stage00_paths = require_artifacts(
        Path(str(inputs["stage00_runtime_run_dir"])), inputs["required_stage00_artifacts"]
    )
    stage01_paths = require_artifacts(
        Path(str(inputs["stage01_runtime_run_dir"])), inputs["required_stage01_artifacts"]
    )
    stage02_paths = require_artifacts(
        Path(str(inputs["stage02_runtime_run_dir"])), inputs["required_stage02_artifacts"]
    )
    stage00_manifest = read_json_object(stage00_paths["run_manifest.json"])
    stage01_manifest = read_json_object(stage01_paths["run_manifest.json"])
    stage01_handoff = read_json_object(stage01_paths["01_candidate_inputs.json"])
    stage02_manifest = read_json_object(stage02_paths["run_manifest.json"])
    require_safety_flags(
        [
            ("Stage 00 run_manifest", stage00_manifest),
            ("Stage 01 run_manifest", stage01_manifest),
            ("Stage 01 candidate handoff", stage01_handoff),
            ("Stage 02 run_manifest", stage02_manifest),
        ],
        stage_label=stage_label,
        field="holdout_test_contact",
        expected=False,
    )
    require_run_id_chain(
        [
            ("Stage 02 run id", str(inputs["stage02_run_id"]),
             stage02_manifest.get("stage02_run_id", stage02_manifest.get("run_id"))),
            ("Stage 01 run id of Stage 02", str(inputs["stage01_run_id"]),
             stage02_manifest.get("source_stage01_run_id")),
        ],
        stage_label=stage_label,
    )

    raw_manifest = read_json_object(stage00_paths["raw_data_manifest.json"])
    split_freeze = read_json_object(stage00_paths["split_freeze.json"])
    require_frozen_train_boundaries(split_freeze)
    label_policy = read_json_object(stage00_paths["label_policy.json"])
    require_frozen_label_policy(label_policy)

    candidate = resolve_candidate_input(config, stage01_handoff, stage_label=stage_label)
    sample_events = load_sample_event_index(stage00_paths["sample_event_index.csv"])
    frozen_train_events = train_valid_events(sample_events)
    assert_train_domain_only(
        frozen_train_events, ["target_timestamp", "horizon_end_timestamp"],
        stage_label=f"{stage_label} frozen Stage 00 train events",
    )
    train_bars = load_train_bars(raw_manifest, split_freeze, inputs)
    assert_train_domain_only(train_bars, ["timestamp"], stage_label=f"{stage_label} train bars")
    feature_frame = build_feature_frame(train_bars)
    assert_train_domain_only(
        feature_frame, ["timestamp"], stage_label=f"{stage_label} feature frame"
    )
    require_feature_columns(
        tuple(str(column) for column in candidate["feature_columns"]), feature_frame
    )
    stage01_summary = load_stage01_summary(
        stage01_paths["01_feature_window_search_summary.csv"]
    )
    stage02_plan_ledger = pd.read_csv(stage02_paths["02_hpo_plan_ledger.csv"])
    return RobustnessInputs(
        stage00_paths=stage00_paths,
        stage01_paths=stage01_paths,
        stage02_paths=stage02_paths,
        stage01_manifest=stage01_manifest,
        raw_manifest=raw_manifest,
        split_freeze=split_freeze,
        candidate=candidate,
        frozen_train_events=frozen_train_events,
        train_bars=train_bars,
        feature_frame=feature_frame,
        stage01_summary=stage01_summary,
        stage02_plan_ledger=stage02_plan_ledger,
    )


def resolve_candidate_input(
    config: Mapping[str, Any], stage01_handoff: Mapping[str, Any], *, stage_label: str
) -> Mapping[str, Any]:
    """Exactly one frozen Stage 01 candidate input matching the config pin."""
    configured_id = str(require_mapping(config["candidate"], "candidate")["candidate_id"])
    matches = [
        candidate
        for candidate in stage01_handoff.get("candidate_inputs", [])
        if str(require_mapping(candidate, "candidate_input").get("candidate_id")) == configured_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{stage_label} requires exactly one Stage 01 candidate input named "
            f"{configured_id!r}; found {len(matches)}"
        )
    return matches[0]


def resolve_frozen_tcn_profile(config: Mapping[str, Any], *, stage_label: str) -> Mapping[str, Any]:
    """Exactly one frozen search-space profile matching the config pin."""
    model = require_mapping(config["model"], "model")
    search_space = load_yaml(resolve_repo_path(model["search_space"]))
    if search_space.get("model_family") != str(model["family"]):
        raise ValueError(
            f"search space model_family mismatch: {search_space.get('model_family')!r} "
            f"!= {model['family']!r}"
        )
    profile_id = str(model["hpo_profile_id"])
    matches = [
        profile
        for profile in search_space.get("profiles", [])
        if str(require_mapping(profile, "profile").get("profile_id")) == profile_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{stage_label} requires exactly one profile {profile_id!r} in "
            f"{model['search_space']}; found {len(matches)}"
        )
    return matches[0]


def resolve_run_id_or_new(configured_run_id: Any, *, stage_label: str) -> str:
    if configured_run_id in (None, ""):
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_id = str(configured_run_id)
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError(
            f"{stage_label} outputs.run_id must match YYYYMMDD_HHMMSS_microseconds, "
            f"got {run_id!r}"
        )
    return run_id


def first_eval_trading_day(fold: Mapping[str, Any]) -> str:
    """First eval trading day of a fold: the calendar day of ``eval_start``
    (``eval_start`` is the earliest eval target timestamp by construction of
    ``splits.build_train_inner_folds``)."""
    return pd.Timestamp(fold["eval_start"]).strftime("%Y-%m-%d")


def embargo_keep_mask(eval_meta: pd.DataFrame, first_day: str) -> np.ndarray:
    """Boolean keep-mask for the one-trading-day eval-side embargo.

    EXACT RULE (preregistered): drop every capped eval row whose
    ``trading_day`` equals the fold's first eval trading day. Train rows are
    untouched, so the embargoed variant scores a strict subset of the
    no-embargo eval rows and every fitted model is shared across variants.
    """
    return eval_meta["trading_day"].astype(str).ne(str(first_day)).to_numpy()


def embargo_reading(
    trial_ledger: pd.DataFrame,
    *,
    seeds: Sequence[int],
    shrinkage_fraction: float,
) -> dict[str, Any]:
    """Apply the preregistered E4 reading rules to the variant trial rows.

    Definitions (all DESCRIPTIVE, fixed before the run):

    * per seed and variant, the margin is the mean over folds of the same-row
      ``delta_macro_f1_vs_baseline`` (completed rows only);
    * the shrinkage rule applies to a seed only when that seed's no-embargo
      margin is strictly positive; otherwise the rule is inapplicable for
      that seed (the train-inner margin was already non-positive and the
      inflation question degenerates);
    * a seed flags "materially smaller" when the embargoed margin is below
      ``shrinkage_fraction`` times the no-embargo margin (predeclared
      default 0.5: more than half the baseline margin disappears);
    * both seeds must agree; disagreement or inapplicability is reported as
      such, with no verdict. No outcome removes the paper's limitation — the
      one-day embargo probes lag-one adjacency only.
    """
    if not 0.0 < float(shrinkage_fraction) < 1.0:
        raise ValueError("shrinkage_fraction must be strictly between 0 and 1")
    per_seed: dict[str, Any] = {}
    incomplete = False
    for seed in seeds:
        seed_rows = trial_ledger.loc[trial_ledger["seed"].astype(int).eq(int(seed))]
        record: dict[str, Any] = {"seed": int(seed)}
        for variant in EMBARGO_VARIANTS:
            rows = seed_rows.loc[seed_rows["variant_id"].astype(str).eq(variant)]
            completed = rows.loc[rows["fit_status"].astype(str).eq("completed")]
            incomplete = incomplete or (
                len(rows) == 0 or len(completed) < len(rows)
            )
            deltas = completed["delta_macro_f1_vs_baseline"].astype(float).to_numpy()
            record[f"{variant}_margin"] = (
                float(np.mean(deltas)) if len(deltas) else float("nan")
            )
            record[f"{variant}_completed_rows"] = int(len(completed))
            record[f"{variant}_expected_rows"] = int(len(rows))
        base = float(record["no_embargo_margin"])
        embargoed = float(record["embargo_1day_margin"])
        applicable = bool(np.isfinite(base) and base > 0.0)
        record["rule_applicable"] = applicable
        record["retained_margin_fraction"] = (
            float(embargoed / base) if applicable and np.isfinite(embargoed) else float("nan")
        )
        record["materially_smaller"] = (
            bool(np.isfinite(embargoed) and embargoed < float(shrinkage_fraction) * base)
            if applicable
            else None
        )
        per_seed[str(int(seed))] = record

    flags = [record["materially_smaller"] for record in per_seed.values()]
    applicables = [record["rule_applicable"] for record in per_seed.values()]
    if incomplete:
        outcome = "incomplete_run_fix_and_rerun"
    elif not all(applicables):
        outcome = "baseline_margin_not_positive_rule_inapplicable"
    elif all(flag is True for flag in flags):
        outcome = "materially_smaller_cross_day_dependence_inflation_reported"
    elif all(flag is False for flag in flags):
        outcome = "roughly_unchanged_limitation_bounded_not_removed"
    else:
        outcome = "mixed_across_seeds_inconclusive"

    return {
        "per_seed": per_seed,
        "shrinkage_fraction": float(shrinkage_fraction),
        "embargo_rule_id": EMBARGO_RULE_ID,
        "embargo_trading_days": 1,
        "overall_outcome": outcome,
        "limitation_removed": False,
        "no_final_model_selected": True,
        "evidence_status": "train_inner_embargo_robustness_control",
    }

"""Stage 05 thesis-synthesis domain logic (measure-only).

Pure synthesis/packaging helpers: aggregate the route's frozen Stage 03 /
Stage 04 / V2.1 decision records into the validation-budget ledger (S5.1),
the claim boundary register (S5.2), and the expectation-calibration table
(S5.3). No fits, no scoring, no model objects, no I/O — the runner
(``lst_models.stages.thesis_synthesis``) owns gates, manifest, and artifact
writing; the provenance source hash lives in ``lst_models.artifacts``.

Every measured number is RESOLVED from a frozen upstream record field
(:func:`resolve_record_field`), never hand-typed (protocol 05 §7).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from lst_models import metrics

# Canonical evidence domains (protocol 05 §3). Never mix two in one claim.
EVIDENCE_DOMAINS = ("official_validation", "train_inner_control", "guarded_walkforward")

VALIDATION_BUDGET_LEDGER_COLUMNS = [
    "stage_name", "run_id", "evidence_domain", "data_segment", "contact_type",
    "scoring_events", "for_selection", "notes",
]
CLAIM_BOUNDARY_REGISTER_COLUMNS = [
    "claim_id", "evidence_domain", "is_limitation", "supporting_run_id_key",
    "supporting_run_id", "supporting_artifact", "statement",
]
EXPECTATION_CALIBRATION_COLUMNS = [
    "metric_id", "label", "value", "metric_kind", "value_source", "citation", "context",
]
MULTIPLICITY_DISCOUNT_COLUMNS = [
    "row_kind", "family", "n_periods", "positive_periods", "mean_delta",
    "period_delta_lcb", "min_family_lcb", "median_family_lcb", "max_family_mean",
    "pbo", "pbo_n_combinations", "pbo_n_trials", "pbo_n_blocks", "pbo_method",
    "seed_aggregation", "note",
]
SELECTIVE_AUTOPSY_COLUMNS = [
    "activity_tercile", "seed", "n_rows", "macro_f1", "accuracy",
    "aurc", "e_aurc", "augrc", "full_coverage_risk",
    "delta_vs_dummy", "mde_vs_dummy", "delta_clears_mde",
]
ESTIMAND_CONTRAST_COLUMNS = [
    "evidence_domain", "aggregation", "weight_unit", "pooled_delta",
    "metric_kind", "value_source", "note",
]
LOO_ROBUSTNESS_COLUMNS = [
    "estimand", "weight_unit", "left_out", "n_units_remaining",
    "delta_after_drop", "baseline_delta", "delta_shift", "sign_after_drop", "note",
]
GUARDED_ACTIVITY_TERCILE_COLUMNS = [
    "evidence_domain", "activity_tercile", "seed", "n_rows",
    "macro_f1", "accuracy", "dummy_macro_f1", "delta_vs_dummy",
    "below_random_prior", "note",
]
GUARDED_BASE_RATE_COLUMNS = [
    "scope", "slice", "seed", "n_rows", "up_rate",
    "dummy_macro_f1", "candidate_macro_f1", "delta_vs_dummy", "note",
]
GUARDED_SENTINEL_COLUMNS = [
    "activity_tercile", "n_rows", "observed_macro_f1", "dummy_macro_f1",
    "observed_delta_vs_dummy", "shuffled_macro_f1_mean", "shuffled_macro_f1_max",
    "shuffled_delta_mean", "shuffled_delta_max", "n_perms", "observed_exceeds_shuffle_max", "note",
]
_ACTIVITY_TERCILE_ORDER = ("low", "mid", "high")

_FIELD_MISSING = object()


def resolve_record_field(record: Mapping[str, Any], dotted_path: str) -> Any:
    """Fail-closed nested lookup of ``dotted_path`` in a frozen record.

    Walks ``a.b.c`` through nested mappings. Raises ``KeyError`` when any key in
    the path is absent (a measured number must trace to an existing artifact
    field, never be fabricated). A present key whose value is ``None`` returns
    ``None`` — that is a real recorded value (e.g. ``pooled_delta_row_pooled``
    on a resumed run), not a missing field.
    """
    current: Any = record
    walked: list[str] = []
    for key in dotted_path.split("."):
        if not isinstance(current, Mapping) or key not in current:
            walked_text = ".".join(walked) or "<root>"
            raise KeyError(
                f"frozen record field {dotted_path!r} not found: {key!r} absent under "
                f"{walked_text}"
            )
        current = current[key]
        walked.append(key)
    return current


def find_forbidden_wording(text: str, forbidden: Sequence[str]) -> list[str]:
    """Return the forbidden phrases that appear in ``text`` (case-insensitive)."""
    haystack = str(text).lower()
    return [phrase for phrase in forbidden if str(phrase).strip() and str(phrase).lower() in haystack]


def assert_no_forbidden_wording(text: str, forbidden: Sequence[str], *, context: str) -> None:
    """Fail closed when any forbidden phrase appears in ``text``."""
    hits = find_forbidden_wording(text, forbidden)
    if hits:
        raise ValueError(f"forbidden wording in {context}: {hits}")


def build_validation_budget_ledger(
    stages_config: Sequence[Mapping[str, Any]],
    records_by_key: Mapping[str, Mapping[str, Any]],
    run_ids_by_key: Mapping[str, str],
    *,
    evidence_domains: Sequence[str] = EVIDENCE_DOMAINS,
) -> pd.DataFrame:
    """S5.1 ledger: one row per scoring stage + a ``total`` row.

    ``scoring_events`` for each stage is resolved from that stage's frozen
    record field (``events_source_key`` + ``events_field``), never hand-typed.
    """
    rows: list[dict[str, Any]] = []
    total_events = 0
    for entry in stages_config:
        domain = str(entry["evidence_domain"])
        if domain not in evidence_domains:
            raise ValueError(
                f"budget_ledger stage {entry.get('stage_name')!r} evidence_domain "
                f"{domain!r} is not one of {tuple(evidence_domains)}"
            )
        source_key = str(entry["events_source_key"])
        if source_key not in records_by_key:
            raise KeyError(f"budget_ledger events_source_key {source_key!r} is not a wired record")
        events = int(resolve_record_field(records_by_key[source_key], str(entry["events_field"])))
        run_key = str(entry["run_id_key"])
        if run_key not in run_ids_by_key:
            raise KeyError(f"budget_ledger run_id_key {run_key!r} is not a wired run id")
        rows.append({
            "stage_name": str(entry["stage_name"]),
            "run_id": str(run_ids_by_key[run_key]),
            "evidence_domain": domain,
            "data_segment": str(entry["data_segment"]),
            "contact_type": str(entry["contact_type"]),
            "scoring_events": events,
            "for_selection": bool(entry.get("for_selection", False)),
            "notes": str(entry.get("notes", "")),
        })
        total_events += events
    rows.append({
        "stage_name": "total", "run_id": "", "evidence_domain": "all",
        "data_segment": "full_route", "contact_type": "aggregate",
        "scoring_events": total_events, "for_selection": False,
        "notes": "route official-validation + guarded scoring budget (sum of stage rows)",
    })
    return pd.DataFrame(rows)[VALIDATION_BUDGET_LEDGER_COLUMNS]


def build_claim_boundary_register(
    claims_config: Sequence[Mapping[str, Any]],
    run_ids_by_key: Mapping[str, str],
    forbidden: Sequence[str],
    *,
    evidence_domains: Sequence[str] = EVIDENCE_DOMAINS,
    supporting_artifacts_by_key: Mapping[str, Sequence[str]] | None = None,
) -> pd.DataFrame:
    """S5.2 register: validate each claim's domain, supporting run id, that its
    cited ``supporting_artifact`` is an entry-gated required artifact of that run
    (so the claim->evidence link is presence/hash-verified, not just a string),
    and that its statement carries no forbidden wording; emit the resolved table.
    """
    if not claims_config:
        raise ValueError("claim_boundary_register.claims must be non-empty")
    gated = {
        key: {str(name) for name in names}
        for key, names in (supporting_artifacts_by_key or {}).items()
    }
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for claim in claims_config:
        claim_id = str(claim["claim_id"])
        if claim_id in seen_ids:
            raise ValueError(f"duplicate claim_id {claim_id!r}")
        seen_ids.add(claim_id)
        domain = str(claim["evidence_domain"])
        if domain not in evidence_domains:
            raise ValueError(
                f"claim {claim_id!r} evidence_domain {domain!r} is not one of "
                f"{tuple(evidence_domains)}"
            )
        run_key = str(claim["supporting_run_id_key"])
        if run_key not in run_ids_by_key:
            raise KeyError(
                f"claim {claim_id!r} supporting_run_id_key {run_key!r} is not a wired run id"
            )
        supporting_artifact = str(claim.get("supporting_artifact", ""))
        if gated and supporting_artifact and supporting_artifact not in gated.get(run_key, set()):
            raise ValueError(
                f"claim {claim_id!r} cites supporting_artifact {supporting_artifact!r}, which is "
                f"not an entry-gated required artifact of run {run_key!r}; add it to "
                f"required_{run_key}_artifacts so it is presence/hash-verified"
            )
        statement = str(claim["statement"])
        assert_no_forbidden_wording(statement, forbidden, context=f"claim {claim_id}")
        rows.append({
            "claim_id": claim_id,
            "evidence_domain": domain,
            "is_limitation": bool(claim.get("is_limitation", False)),
            "supporting_run_id_key": run_key,
            "supporting_run_id": str(run_ids_by_key[run_key]),
            "supporting_artifact": str(claim.get("supporting_artifact", "")),
            "statement": statement,
        })
    return pd.DataFrame(rows)[CLAIM_BOUNDARY_REGISTER_COLUMNS]


def build_expectation_calibration(
    rows_config: Sequence[Mapping[str, Any]],
    records_by_key: Mapping[str, Mapping[str, Any]],
    forbidden: Sequence[str],
) -> pd.DataFrame:
    """S5.3 table: literature anchors from config + measured values resolved
    from frozen records (fail-closed). ``value_source`` records the origin so a
    measured number is always traceable to ``<source_key>:<field>``."""
    if not rows_config:
        raise ValueError("expectation_calibration.rows must be non-empty")
    rows: list[dict[str, Any]] = []
    for entry in rows_config:
        metric_id = str(entry["metric_id"])
        if not str(entry.get("metric_kind", "")).strip():
            raise ValueError(
                f"expectation {metric_id!r} must declare a metric_kind so accuracy and "
                "macro-F1 rows are never read as comparable"
            )
        context = str(entry.get("context", ""))
        assert_no_forbidden_wording(context, forbidden, context=f"expectation {metric_id} context")
        source = str(entry.get("value_source", "frozen_record"))
        if source == "config_literature":
            value = entry["value"]
            value_source = "config_literature"
        else:
            source_key = str(entry["value_source_key"])
            if source_key not in records_by_key:
                raise KeyError(
                    f"expectation {metric_id!r} value_source_key {source_key!r} is not a wired record"
                )
            field = str(entry["value_field"])
            value = resolve_record_field(records_by_key[source_key], field)
            value_source = f"{source_key}:{field}"
        rows.append({
            "metric_id": metric_id,
            "label": str(entry.get("label", "")),
            "value": value,
            "metric_kind": str(entry["metric_kind"]),
            "value_source": value_source,
            "citation": str(entry.get("citation", "")),
            "context": context,
        })
    return pd.DataFrame(rows)[EXPECTATION_CALIBRATION_COLUMNS]


def build_multiplicity_discount(
    readout: pd.DataFrame,
    *,
    family_axis: str,
    period_axis: str,
    delta_field: str,
    completed_status_field: str = "fit_status",
    completed_status_value: str = "completed",
    model_row_kind: str | None = "model",
    is_block_count: int | None = None,
    expected_family_count: int | None = None,
    expected_period_count: int | None = None,
    expected_seeds_per_cell: int | None = None,
    seed_aggregation: str = "mean_over_seeds",
    descriptive_note: str = "",
) -> pd.DataFrame:
    """B6 descriptive multiplicity discount over the per-(family, period) delta
    matrix (families as trials, periods as blocks).

    Per family: the period-level Student-t LCB over its period deltas and the
    positive-period count. Across families: the multiple-comparison-aware
    ``min_family_lcb`` (the worst family must still clear the baseline) and a
    CSCV ``pbo`` overfitting share. All values are DESCRIPTIVE discounts -- never
    promoted to a 'statistically significant' claim (register Tier 1 caveat).
    Wires the built-but-unused primitives ``compute_metric_lcb``,
    ``aggregate_family_delta_cis``, and ``cscv_pbo``.

    FAIL-CLOSED on roster incompleteness: the predeclared guarded roster is
    ``expected_family_count`` x ``expected_period_count`` with
    ``expected_seeds_per_cell`` seed rows per cell (the 56-event ledger), and any
    missing (family, period) cell raises rather than silently shrinking the PBO
    block count. Seeds are aggregated by ``seed_aggregation`` before the matrix is
    formed (surfaced in the output, not implicit).
    """
    missing = sorted({family_axis, period_axis, delta_field} - set(readout.columns))
    if missing:
        raise ValueError(f"multiplicity_discount: readout missing columns {missing}")
    frame = readout
    if completed_status_field in frame.columns:
        frame = frame[frame[completed_status_field].astype(str) == str(completed_status_value)]
    if model_row_kind is not None and "row_kind" in frame.columns:
        frame = frame[frame["row_kind"].astype(str) == str(model_row_kind)]
    if frame.empty:
        raise ValueError("multiplicity_discount: no completed model rows in the readout")
    cell_sizes = frame.groupby([family_axis, period_axis]).size()
    if expected_seeds_per_cell is not None:
        offenders = cell_sizes[cell_sizes != int(expected_seeds_per_cell)]
        if not offenders.empty:
            raise ValueError(
                f"multiplicity_discount: {len(offenders)} (family, period) cells lack the "
                f"expected {expected_seeds_per_cell} seed rows: {dict(list(offenders.items())[:8])}"
            )
    # aggregate seeds -> families (rows) x periods (cols) delta matrix
    pivot = (
        frame.groupby([family_axis, period_axis])[delta_field].mean().unstack(period_axis)
    )
    pivot = pivot.sort_index().sort_index(axis=1)
    if bool(pivot.isna().any().any()):
        gaps = [
            (str(fam), str(period))
            for fam in pivot.index for period in pivot.columns
            if pd.isna(pivot.loc[fam, period])
        ]
        raise ValueError(
            f"multiplicity_discount: incomplete family x period matrix; {len(gaps)} missing "
            f"cell(s) e.g. {gaps[:8]}; the predeclared guarded roster must be complete"
        )
    if expected_family_count is not None and pivot.shape[0] != int(expected_family_count):
        raise ValueError(
            f"multiplicity_discount: expected {expected_family_count} families, found "
            f"{pivot.shape[0]} ({[str(f) for f in pivot.index]})"
        )
    if expected_period_count is not None and pivot.shape[1] != int(expected_period_count):
        raise ValueError(
            f"multiplicity_discount: expected {expected_period_count} periods, found "
            f"{pivot.shape[1]} ({[str(p) for p in pivot.columns]})"
        )
    family_cis: dict[str, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for family in pivot.index:
        period_deltas = pivot.loc[family].to_numpy(dtype=float)
        lcb = float(metrics.compute_metric_lcb(period_deltas))
        mean = float(np.mean(period_deltas))
        family_cis[str(family)] = {"lcb": lcb, "mean": mean}
        rows.append({
            "row_kind": "family", "family": str(family),
            "n_periods": int(period_deltas.size),
            "positive_periods": int(np.sum(period_deltas > 0)),
            "mean_delta": mean, "period_delta_lcb": lcb,
            "min_family_lcb": None, "median_family_lcb": None, "max_family_mean": None,
            "pbo": None, "pbo_n_combinations": None, "pbo_n_trials": None,
            "pbo_n_blocks": None, "pbo_method": None, "seed_aggregation": None, "note": "",
        })
    aggregate = metrics.aggregate_family_delta_cis(family_cis)
    pbo = metrics.cscv_pbo(pivot.to_numpy(dtype=float), is_block_count=is_block_count)
    pbo_method = "cscv_symmetric" if pbo["is_symmetric"] else "cscv_odd_block_floor_ceil_adaptation"
    rows.append({
        "row_kind": "summary", "family": "all",
        "n_periods": int(pivot.shape[1]), "positive_periods": None,
        "mean_delta": None, "period_delta_lcb": None,
        "min_family_lcb": aggregate["min_family_lcb"],
        "median_family_lcb": aggregate["median_family_lcb"],
        "max_family_mean": aggregate["max_family_mean"],
        "pbo": pbo["pbo"], "pbo_n_combinations": pbo["n_combinations"],
        "pbo_n_trials": pbo["n_trials"], "pbo_n_blocks": pbo["n_blocks"],
        "pbo_method": pbo_method, "seed_aggregation": str(seed_aggregation),
        "note": str(descriptive_note),
    })
    return pd.DataFrame(rows)[MULTIPLICITY_DISCOUNT_COLUMNS]


def _mde_lookup(
    robustness_slices: pd.DataFrame, seed_slice_axis: str, tercile_slice_axis: str
) -> dict[tuple[str, str], tuple[float, float]]:
    """(seed, tercile-or-'all') -> (delta, bootstrap_lcb) from the frozen Stage 04
    per-trading-day block bootstrap; 'all' from the per-seed slice rows."""
    lookup: dict[tuple[str, str], tuple[float, float]] = {}
    if robustness_slices is None or robustness_slices.empty:
        return lookup
    delta_col = "delta_macro_f1_vs_stratified_dummy_train_prior"
    needed = {"slice_axis", "slice_value", "seed", delta_col, "bootstrap_delta_lcb"}
    if not needed.issubset(robustness_slices.columns):
        return lookup
    for record in robustness_slices.to_dict(orient="records"):
        axis = str(record["slice_axis"])
        seed = str(record["seed"])
        delta = record[delta_col]
        lcb = record["bootstrap_delta_lcb"]
        if axis == seed_slice_axis and str(record["slice_value"]) == seed:
            lookup[(seed, "all")] = (delta, lcb)
        elif axis == tercile_slice_axis:
            lookup[(seed, str(record["slice_value"]))] = (delta, lcb)
    return lookup


def _selective_autopsy_metrics(sub: pd.DataFrame) -> dict[str, Any]:
    nan = float("nan")
    if len(sub) == 0:
        return {"n_rows": 0, "macro_f1": nan, "accuracy": nan, "aurc": nan,
                "e_aurc": nan, "augrc": nan, "full_coverage_risk": nan}
    y_true = sub["y_true"].to_numpy(dtype=int)
    y_pred = sub["y_pred"].to_numpy(dtype=int)
    confidence = sub["confidence"].to_numpy(dtype=float)
    correct = sub["correct"].to_numpy(dtype=bool)
    # deterministic sample_id tie-break (Stage 04 selective contract): confidence
    # ties must not let CSV row order move the curve.
    tie = sub["sample_id"].to_numpy() if "sample_id" in sub.columns else None
    aurc = metrics.aurc_metrics(confidence, correct, tie_break=tie)
    return {
        "n_rows": int(len(sub)),
        "macro_f1": float(metrics.binary_macro_f1(y_true, y_pred)),
        "accuracy": float(correct.mean()),
        "aurc": float(aurc["aurc"]),
        "e_aurc": float(aurc["e_aurc"]),
        "augrc": float(metrics.augrc(confidence, correct, tie_break=tie)),
        "full_coverage_risk": float(aurc["full_coverage_risk"]),
    }


def _finite(value: Any) -> bool:
    try:
        return float(value) == float(value)
    except (TypeError, ValueError):
        return False


def _selective_autopsy_seed_mean(seed_rows: list[dict[str, Any]], tercile: str) -> dict[str, Any]:
    numeric = ["n_rows", "macro_f1", "accuracy", "aurc", "e_aurc", "augrc",
               "full_coverage_risk", "delta_vs_dummy", "mde_vs_dummy"]
    agg: dict[str, Any] = {}
    for col in numeric:
        finite = [float(r[col]) for r in seed_rows if _finite(r[col])]
        agg[col] = float(np.mean(finite)) if finite else float("nan")
    agg["n_rows"] = int(round(agg["n_rows"])) if _finite(agg["n_rows"]) else 0
    # None = MDE unavailable for this slice (no bootstrap LCB in the frozen Stage 04
    # artifact, e.g. per-tercile until B4 adds activity-tercile bootstrap) -- never
    # a misleading False.
    if not (_finite(agg["delta_vs_dummy"]) and _finite(agg["mde_vs_dummy"])):
        clears: bool | None = None
    else:
        clears = bool(agg["delta_vs_dummy"] > agg["mde_vs_dummy"])
    return {"activity_tercile": tercile, "seed": "seed_mean", **agg, "delta_clears_mde": clears}


def build_selective_autopsy(
    dump: pd.DataFrame,
    robustness_slices: pd.DataFrame,
    *,
    seeds: Sequence[int],
    activity_axis: str = "activity_tercile",
    mde_seed_slice_axis: str = "seed",
    mde_tercile_slice_axis: str = "activity_tercile",
) -> pd.DataFrame:
    """B7 selective- and calibration-aware autopsy (measure-only diagnostic).

    On the gated/derived frozen Stage 03 validation dump, per activity tercile x
    seed: model macro-F1 / accuracy, the whole-curve selective AURC / e-AURC /
    AUGRC (Geifman & El-Yaniv 2017; Geifman et al. 2019; Traub et al. 2024) on
    (confidence, correct) with a deterministic ``sample_id`` tie-break, and the
    same-row delta-vs-dummy minimum-detectable effect EXTRACTED from the frozen
    Stage 04 per-trading-day block bootstrap (``mde = delta - lcb``;
    ``delta_clears_mde`` ⟺ lcb > 0, or ``None`` when no bootstrap LCB exists for
    that slice). The frozen Stage 04 artifact carries bootstrap LCBs for the
    seed and ticker axes only, so the pooled ('all') MDE is populated while the
    per-tercile MDE stays ``None`` until B4 adds an activity-tercile bootstrap;
    the per-tercile DELTA and the selective curves are always populated.
    Selective metrics are accuracy-based with NO cost/return component -- a
    diagnostic, never an operating point or a tradeability claim (register F4).
    Wires the 0-call-site ``augrc`` primitive; crosses abstention with the
    activity tercile (register F1: the edge is in low-activity bars, below random
    on high-activity bars).
    """
    required = {"confidence", "correct", "y_true", "y_pred", "seed", activity_axis}
    missing = sorted(required - set(dump.columns))
    if missing:
        raise ValueError(f"selective_autopsy: dump missing derived columns {missing}")
    mde_lookup = _mde_lookup(robustness_slices, mde_seed_slice_axis, mde_tercile_slice_axis)
    present = set(dump[activity_axis].astype(str))
    terciles = ["all"] + [t for t in _ACTIVITY_TERCILE_ORDER if t in present]
    rows: list[dict[str, Any]] = []
    for tercile in terciles:
        seed_rows: list[dict[str, Any]] = []
        for seed in seeds:
            sub = dump[dump["seed"].astype(int) == int(seed)]
            if tercile != "all":
                sub = sub[sub[activity_axis].astype(str) == tercile]
            delta, lcb = mde_lookup.get((str(int(seed)), tercile), (float("nan"), float("nan")))
            mde = float(delta) - float(lcb) if (_finite(delta) and _finite(lcb)) else float("nan")
            row = {
                "activity_tercile": tercile, "seed": str(int(seed)),
                **_selective_autopsy_metrics(sub),
                "delta_vs_dummy": float(delta) if _finite(delta) else float("nan"),
                "mde_vs_dummy": mde,
                # None = MDE unavailable (no bootstrap LCB for this slice in the
                # frozen Stage 04 artifact); only seed/ticker axes carry bootstrap
                # today, so per-tercile MDE needs B4 (activity-tercile bootstrap).
                "delta_clears_mde": (bool(float(lcb) > 0.0) if _finite(lcb) else None),
            }
            rows.append(row)
            seed_rows.append(row)
        rows.append(_selective_autopsy_seed_mean(seed_rows, tercile))
    return pd.DataFrame(rows)[SELECTIVE_AUTOPSY_COLUMNS]


def collect_pooled_delta_estimands(v2_1_record: Mapping[str, Any]) -> dict[str, Any]:
    """The FIX-1 estimand surface read from the frozen V2.1 decision record.

    Surfaces the binding estimand alongside both companions so the synthesis
    report makes the estimand divergence transparent (register FIX-1 / F9)."""
    return {
        "binding_estimand": v2_1_record.get("pooled_delta_estimand"),
        "pooled_delta": v2_1_record.get("pooled_delta"),
        "pooled_delta_row_pooled": v2_1_record.get("pooled_delta_row_pooled"),
        "pooled_delta_equal_weight": v2_1_record.get("pooled_delta_equal_weight"),
        "pooled_delta_row_pooled_available": v2_1_record.get("pooled_delta_row_pooled_available"),
        "positive_period_count": v2_1_record.get("positive_period_count"),
    }


def build_estimand_contrast(
    v2_1_record: Mapping[str, Any],
    selective_autopsy: pd.DataFrame,
    *,
    metric_kind: str = "macro_f1_delta_vs_stratified_dummy_train_prior",
    validation_terciles: Sequence[str] = _ACTIVITY_TERCILE_ORDER,
    seed_mean_label: str = "seed_mean",
) -> pd.DataFrame:
    """B8 / FIX-1 four-estimand contrast: the headline macro-F1 delta under both
    aggregation choices (row-pooled vs equal-weight) in both reportable evidence
    domains, side by side, so no single number is read as THE number (register
    FIX-1 / F9).

    The two guarded walk-forward estimands are READ from the frozen V2.1 decision
    record (row-pooled = binding for the met-criteria claim; equal-weight over the
    7 periods = companion). The two official-validation estimands are READ from
    the intra-stage selective autopsy frame: row-pooled = the pooled ('all')
    seed-mean delta-vs-dummy; equal-weight = the mean of the per-activity-tercile
    seed-mean deltas (regime-balanced). Each row names its ``weight_unit`` because
    the equal-weight unit DIFFERS by domain (walk-forward period vs activity
    tercile) -- the columns are each-vs-its-own-row-pooled, not cross-domain
    comparable. Descriptive estimand surface only; no estimand is promoted to
    'the' result (``no_final_model_selected`` stays true).
    """
    g_row = resolve_record_field(v2_1_record, "pooled_delta_row_pooled")
    g_eq = resolve_record_field(v2_1_record, "pooled_delta_equal_weight")
    if g_row is None or g_eq is None:
        raise ValueError(
            "estimand_contrast: V2.1 record is missing a pooled-delta estimand "
            "(pooled_delta_row_pooled / pooled_delta_equal_weight); a resumed run "
            "without the native row-pooled value cannot form the contrast"
        )

    def _autopsy_delta(tercile: str) -> float:
        sub = selective_autopsy[
            (selective_autopsy["activity_tercile"].astype(str) == tercile)
            & (selective_autopsy["seed"].astype(str) == seed_mean_label)
        ]
        if sub.empty:
            raise ValueError(
                f"estimand_contrast: selective autopsy missing the "
                f"{tercile!r}/{seed_mean_label!r} row needed for the validation estimand"
            )
        return float(sub.iloc[0]["delta_vs_dummy"])

    v_row = _autopsy_delta("all")
    tercile_deltas = [_autopsy_delta(str(t)) for t in validation_terciles]
    v_eq = float(np.mean(tercile_deltas))
    tercile_src = ",".join(str(t) for t in validation_terciles)
    rows = [
        {
            "evidence_domain": "guarded_walkforward", "aggregation": "row_pooled",
            "weight_unit": "row", "pooled_delta": float(g_row), "metric_kind": metric_kind,
            "value_source": "v2_1_decision_record.json:pooled_delta_row_pooled",
            "note": "binding estimand for the guarded met-criteria claim (C4)",
        },
        {
            "evidence_domain": "guarded_walkforward", "aggregation": "equal_weight",
            "weight_unit": "walkforward_period", "pooled_delta": float(g_eq),
            "metric_kind": metric_kind,
            "value_source": "v2_1_decision_record.json:pooled_delta_equal_weight",
            "note": "equal weight over the 7 walk-forward periods (companion, not binding)",
        },
        {
            "evidence_domain": "official_validation", "aggregation": "row_pooled",
            "weight_unit": "row", "pooled_delta": v_row, "metric_kind": metric_kind,
            "value_source": f"05_selective_autopsy.csv:all/{seed_mean_label}:delta_vs_dummy",
            "note": "pooled over all validation rows (seed-mean of n=2 seeds)",
        },
        {
            "evidence_domain": "official_validation", "aggregation": "equal_weight",
            "weight_unit": "activity_tercile", "pooled_delta": v_eq, "metric_kind": metric_kind,
            "value_source": (
                f"05_selective_autopsy.csv:mean({tercile_src})/{seed_mean_label}:delta_vs_dummy"
            ),
            "note": (
                "regime-balanced: equal weight over activity terciles -- a different unit "
                "from the guarded period equal-weight, so compare each only to its own row-pooled"
            ),
        },
    ]
    return pd.DataFrame(rows)[ESTIMAND_CONTRAST_COLUMNS]


def _loo_sweep(
    deltas: Mapping[str, float], *, estimand: str, weight_unit: str
) -> list[dict[str, Any]]:
    """Equal-weight leave-one-out over ``deltas`` (unit -> delta): drop each unit,
    re-average the rest, flag whether the baseline sign survives every drop."""
    labels = list(deltas)
    values = np.array([float(deltas[k]) for k in labels], dtype=float)
    n = int(values.size)
    if n < 3:
        raise ValueError(f"loo_robustness: need >= 3 {weight_unit} units, found {n}")
    baseline = float(values.mean())
    after = {lab: float(np.delete(values, i).mean()) for i, lab in enumerate(labels)}
    rows = [
        {
            "estimand": estimand, "weight_unit": weight_unit, "left_out": str(lab),
            "n_units_remaining": n - 1, "delta_after_drop": after[lab],
            "baseline_delta": baseline, "delta_shift": after[lab] - baseline,
            "sign_after_drop": bool(after[lab] > 0.0), "note": "",
        }
        for lab in labels
    ]
    # baseline sign survives only if NO drop crosses zero (direction-aware)
    if baseline > 0.0:
        sign_flip = any(after[k] <= 0.0 for k in after)
    elif baseline < 0.0:
        sign_flip = any(after[k] >= 0.0 for k in after)
    else:
        sign_flip = True
    worst = min(after, key=lambda k: after[k])
    influential = max(after, key=lambda k: abs(after[k] - baseline))
    rows.append({
        "estimand": estimand, "weight_unit": weight_unit, "left_out": "<all:summary>",
        "n_units_remaining": n, "delta_after_drop": baseline, "baseline_delta": baseline,
        "delta_shift": 0.0, "sign_after_drop": bool(not sign_flip),
        "note": (
            f"equal-weight over {n} {weight_unit}s; loo_sign_flip={sign_flip}; "
            f"worst_after={after[worst]:.6f} (drop {worst}); "
            f"most_influential={influential} (delta_after={after[influential]:.6f})"
        ),
    })
    return rows


def build_loo_robustness(
    period_summary: pd.DataFrame,
    per_ticker: pd.DataFrame,
    *,
    primary_model: str,
    family_axis: str = "table_row_id",
    period_axis: str = "period_id",
    ticker_axis: str = "ticker",
    period_delta_field: str = "mean_delta_vs_dummy",
    ticker_delta_field: str = "delta_macro_f1_vs_stratified_dummy_train_prior",
    expected_period_count: int | None = None,
    expected_ticker_count: int | None = None,
    row_pooled_available: bool = False,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """B8 equal-weight leave-one-out robustness of the guarded pooled delta
    (descriptive; measure-only; reads the frozen V2.1 small aggregates only).

    Two leave-one-out sweeps on the frozen primary model:
      * LOO-period -- drop each walk-forward period, re-average the remaining
        per-period deltas (the equal-weight-over-periods estimand whose full value
        equals ``pooled_delta_equal_weight``).
      * LOO-ticker -- collapse the per-(period, seed, ticker) deltas to a
        per-ticker mean, drop each ticker, re-average the remaining tickers.
    Each row carries the recomputed delta, its shift from the sweep baseline, and
    whether the sign survives the drop; a per-sweep summary row records
    ``loo_sign_flip`` and the most influential unit.

    The BINDING estimand is row-pooled, and macro-F1 is NOT linear across rows, so
    a true row-pooled LOO must recompute pooled macro-F1 from the raw
    ``v2_1_predictions.csv`` -- a deferred marker row records that gap (kept
    measure-only here) rather than silently equating equal-weight LOO with it.
    Descriptive robustness only -- never a significance test or a selection.
    """
    for name, frame, axes in (
        ("period_summary", period_summary, (family_axis, period_axis, period_delta_field)),
        ("per_ticker", per_ticker, (family_axis, ticker_axis, ticker_delta_field)),
    ):
        missing = sorted(set(axes) - set(frame.columns))
        if missing:
            raise ValueError(f"loo_robustness: {name} missing columns {missing}")

    period_rows = period_summary[period_summary[family_axis].astype(str) == str(primary_model)]
    if period_rows.empty:
        raise ValueError(
            f"loo_robustness: period_summary has no rows for primary model {primary_model!r}"
        )
    period_deltas = (
        period_rows.groupby(period_axis)[period_delta_field].mean().sort_index().to_dict()
    )
    if expected_period_count is not None and len(period_deltas) != int(expected_period_count):
        raise ValueError(
            f"loo_robustness: expected {expected_period_count} periods for {primary_model!r}, "
            f"found {len(period_deltas)} ({sorted(period_deltas)})"
        )

    ticker_rows = per_ticker[per_ticker[family_axis].astype(str) == str(primary_model)]
    if ticker_rows.empty:
        raise ValueError(
            f"loo_robustness: per_ticker has no rows for primary model {primary_model!r}"
        )
    ticker_deltas = (
        ticker_rows.groupby(ticker_axis)[ticker_delta_field].mean().sort_index().to_dict()
    )
    if expected_ticker_count is not None and len(ticker_deltas) != int(expected_ticker_count):
        raise ValueError(
            f"loo_robustness: expected {expected_ticker_count} tickers for {primary_model!r}, "
            f"found {len(ticker_deltas)} ({sorted(ticker_deltas)})"
        )

    rows: list[dict[str, Any]] = []
    rows.extend(_loo_sweep(
        {str(k): float(v) for k, v in period_deltas.items()},
        estimand="equal_weight_over_periods", weight_unit="walkforward_period",
    ))
    rows.extend(_loo_sweep(
        {str(k): float(v) for k, v in ticker_deltas.items()},
        estimand="equal_weight_over_tickers", weight_unit="ticker",
    ))
    rows.append({
        "estimand": "row_pooled", "weight_unit": "row", "left_out": "<deferred>",
        "n_units_remaining": None, "delta_after_drop": None, "baseline_delta": None,
        "delta_shift": None, "sign_after_drop": None,
        "note": (
            "row-pooled LOO deferred: macro-F1 is non-linear across rows, so it must "
            "recompute pooled macro-F1 from the raw v2_1_predictions.csv (Drive-only); "
            "kept measure-only here. "
            f"row_pooled_available_in_record={bool(row_pooled_available)}. {descriptive_note}"
        ).strip(),
    })
    return pd.DataFrame(rows)[LOO_ROBUSTNESS_COLUMNS]


def _row_pooled_seed_mean_delta(
    cand: pd.DataFrame, base: pd.DataFrame, *, seed_axis: str
) -> float:
    """Protocol §8 row-union estimand: mean over the seeds present in BOTH frames
    of ``macro_F1(candidate rows) - macro_F1(baseline rows)`` (each pooled across
    all rows of that seed). Mirrors ``guarded_walkforward._row_pooled_pooled_delta``
    exactly -- the no-drop value reproduces ``pooled_delta_row_pooled``."""
    seeds = sorted(set(cand[seed_axis].tolist()) & set(base[seed_axis].tolist()))
    deltas: list[float] = []
    for seed in seeds:
        c = cand[cand[seed_axis] == seed]
        b = base[base[seed_axis] == seed]
        if c.empty or b.empty:
            continue
        cand_f1 = float(metrics.binary_macro_f1(
            c["y_true"].to_numpy(dtype=int), c["y_pred"].to_numpy(dtype=int)
        ))
        base_f1 = float(metrics.binary_macro_f1(
            b["y_true"].to_numpy(dtype=int), b["y_pred"].to_numpy(dtype=int)
        ))
        deltas.append(cand_f1 - base_f1)
    if not deltas:
        raise ValueError(
            "row_pooled_loo: no common seed has both candidate and baseline rows"
        )
    return float(np.mean(deltas))


def build_row_pooled_loo(
    primary_predictions: pd.DataFrame,
    baseline_predictions: pd.DataFrame,
    *,
    primary_model: str,
    family_axis: str = "table_row_id",
    period_axis: str = "period_id",
    ticker_axis: str = "ticker",
    seed_axis: str = "seed",
    expected_period_count: int | None = None,
    expected_ticker_count: int | None = None,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """The TRUE row-pooled leave-one-out of the BINDING guarded estimand
    (protocol §8 row union), recomputed from the raw frozen predictions.

    For each walk-forward period and each ticker: drop that slice's rows from BOTH
    the primary candidate and the stratified-dummy baseline, then recompute the
    row-pooled pooled_delta (:func:`_row_pooled_seed_mean_delta`). macro-F1 is
    NON-linear across rows, so this -- unlike the equal-weight LOO -- cannot be
    derived from the small per-period/per-ticker aggregates; it needs the row-level
    ``v2_1_predictions.csv`` + ``v2_1_baseline_predictions.csv``. The no-drop
    baseline reproduces ``pooled_delta_row_pooled``. Emits the same
    ``LOO_ROBUSTNESS_COLUMNS`` schema as the equal-weight LOO (``weight_unit=row``,
    ``n_units_remaining`` = rows surviving the drop). Descriptive robustness of the
    binding estimand only -- never a significance test or a selection.
    """
    need_c = {family_axis, period_axis, ticker_axis, seed_axis, "y_true", "y_pred"}
    need_b = {period_axis, ticker_axis, seed_axis, "y_true", "y_pred"}
    for name, frame, need in (
        ("primary_predictions", primary_predictions, need_c),
        ("baseline_predictions", baseline_predictions, need_b),
    ):
        missing = sorted(need - set(frame.columns))
        if missing:
            raise ValueError(f"row_pooled_loo: {name} missing columns {missing}")
    cand = primary_predictions[primary_predictions[family_axis].astype(str) == str(primary_model)]
    if cand.empty:
        raise ValueError(f"row_pooled_loo: no rows for primary model {primary_model!r}")
    base = baseline_predictions
    baseline_delta = _row_pooled_seed_mean_delta(cand, base, seed_axis=seed_axis)

    rows: list[dict[str, Any]] = []
    sweeps = (
        ("row_pooled_over_periods", period_axis, expected_period_count),
        ("row_pooled_over_tickers", ticker_axis, expected_ticker_count),
    )
    for estimand, axis, expected in sweeps:
        values = sorted(set(cand[axis].astype(str)))
        if expected is not None and len(values) != int(expected):
            raise ValueError(
                f"row_pooled_loo: expected {expected} {axis} values for {primary_model!r}, "
                f"found {len(values)} ({values})"
            )
        after: dict[str, float] = {}
        for value in values:
            cc = cand[cand[axis].astype(str) != value]
            bb = base[base[axis].astype(str) != value]
            delta = _row_pooled_seed_mean_delta(cc, bb, seed_axis=seed_axis)
            after[value] = delta
            rows.append({
                "estimand": estimand, "weight_unit": "row", "left_out": str(value),
                "n_units_remaining": int(len(cc)), "delta_after_drop": delta,
                "baseline_delta": baseline_delta, "delta_shift": delta - baseline_delta,
                "sign_after_drop": bool(delta > 0.0), "note": "",
            })
        if baseline_delta > 0.0:
            sign_flip = any(after[k] <= 0.0 for k in after)
        elif baseline_delta < 0.0:
            sign_flip = any(after[k] >= 0.0 for k in after)
        else:
            sign_flip = True
        worst = min(after, key=lambda k: after[k])
        influential = max(after, key=lambda k: abs(after[k] - baseline_delta))
        rows.append({
            "estimand": estimand, "weight_unit": "row", "left_out": "<all:summary>",
            "n_units_remaining": int(len(cand)), "delta_after_drop": baseline_delta,
            "baseline_delta": baseline_delta, "delta_shift": 0.0,
            "sign_after_drop": bool(not sign_flip),
            "note": (
                f"row-pooled (protocol §8 row-union) over {len(values)} "
                f"{axis} values; baseline reproduces pooled_delta_row_pooled; "
                f"loo_sign_flip={sign_flip}; worst_after={after[worst]:.6f} (drop {worst}); "
                f"most_influential={influential} (delta_after={after[influential]:.6f}). "
                f"{descriptive_note}"
            ).strip(),
        })
    return pd.DataFrame(rows)[LOO_ROBUSTNESS_COLUMNS]


def _guarded_tercile_row(
    tercile: str, seed: str, cand: pd.DataFrame, base: pd.DataFrame, random_prior: float
) -> dict[str, Any]:
    """One (tercile, seed) guarded conditional-map cell: candidate vs same-row dummy."""
    nan = float("nan")
    head = {"evidence_domain": "guarded_walkforward", "activity_tercile": tercile, "seed": seed}
    if len(cand) == 0 or len(base) == 0:
        return {**head, "n_rows": int(len(cand)), "macro_f1": nan, "accuracy": nan,
                "dummy_macro_f1": nan, "delta_vs_dummy": nan, "below_random_prior": False, "note": ""}
    y_true = cand["y_true"].to_numpy(dtype=int)
    y_pred = cand["y_pred"].to_numpy(dtype=int)
    macro = float(metrics.binary_macro_f1(y_true, y_pred))
    dummy = float(metrics.binary_macro_f1(
        base["y_true"].to_numpy(dtype=int), base["y_pred"].to_numpy(dtype=int)
    ))
    return {
        **head, "n_rows": int(len(cand)), "macro_f1": macro,
        "accuracy": float((y_pred == y_true).mean()),
        "dummy_macro_f1": dummy, "delta_vs_dummy": macro - dummy,
        "below_random_prior": bool(macro < float(random_prior)), "note": "",
    }


def _guarded_tercile_seed_mean(
    tercile: str, seed_rows: list[dict[str, Any]], random_prior: float, note: str
) -> dict[str, Any]:
    """Seed-mean row for a tercile (mean over the per-seed cells; finite values only).
    Mean is linear so ``delta_vs_dummy`` stays == ``macro_f1`` - ``dummy_macro_f1``."""
    numeric = ["n_rows", "macro_f1", "accuracy", "dummy_macro_f1", "delta_vs_dummy"]
    agg: dict[str, Any] = {}
    for col in numeric:
        finite = [float(r[col]) for r in seed_rows if _finite(r[col])]
        agg[col] = float(np.mean(finite)) if finite else float("nan")
    agg["n_rows"] = int(round(agg["n_rows"])) if _finite(agg["n_rows"]) else 0
    macro = agg["macro_f1"]
    return {
        "evidence_domain": "guarded_walkforward", "activity_tercile": tercile, "seed": "seed_mean",
        **agg, "below_random_prior": bool(_finite(macro) and macro < float(random_prior)),
        "note": str(note) if tercile == "all" else "",
    }


def build_guarded_activity_tercile(
    primary_predictions: pd.DataFrame,
    baseline_predictions: pd.DataFrame,
    *,
    primary_model: str,
    family_axis: str = "table_row_id",
    ticker_axis: str = "ticker",
    trading_day_axis: str = "trading_day",
    seed_axis: str = "seed",
    random_prior: float = 0.5,
    activity_tercile_fn: Any = None,
    expected_ticker_count: int | None = None,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """Cross-era replication of the conditional-predictability map on the GUARDED
    walk-forward era (closes the review blocker: the validation-era activity-tercile
    map from Stage 03/04 was never measured on the 2017-2024 guarded segment, even
    though the row-level guarded dump exists and was already re-aggregated for the
    row-pooled LOO).

    Reuses the EXACT validation activity proxy (``diagnostics.activity_terciles`` --
    per-ticker terciles of the per-(ticker, trading_day) eligible-row count) so the
    guarded map is apples-to-apples with the validation map. Per activity tercile x
    seed (plus a seed-mean): primary candidate macro-F1, the same-row stratified-dummy
    macro-F1, their delta, and a below-random-prior flag. Measure-only over the raw
    frozen ``v2_1_predictions.csv`` + ``v2_1_baseline_predictions.csv`` (Drive-only);
    no fit, no scoring, no selection. Descriptive conditional map -- never an operating
    point or a tradeability claim (register F1/F4).
    """
    need_c = {family_axis, ticker_axis, trading_day_axis, seed_axis, "y_true", "y_pred"}
    need_b = {ticker_axis, trading_day_axis, seed_axis, "y_true", "y_pred"}
    for name, frame, need in (
        ("primary_predictions", primary_predictions, need_c),
        ("baseline_predictions", baseline_predictions, need_b),
    ):
        missing = sorted(need - set(frame.columns))
        if missing:
            raise ValueError(f"guarded_activity_tercile: {name} missing columns {missing}")
    cand = primary_predictions[
        primary_predictions[family_axis].astype(str) == str(primary_model)
    ].copy()
    if cand.empty:
        raise ValueError(f"guarded_activity_tercile: no rows for primary model {primary_model!r}")
    if expected_ticker_count is not None:
        n_tickers = int(cand[ticker_axis].nunique())
        if n_tickers != int(expected_ticker_count):
            raise ValueError(
                f"guarded_activity_tercile: expected {expected_ticker_count} tickers, found {n_tickers}"
            )
    cand, base = _guarded_tercile_assign(
        cand, baseline_predictions, ticker_axis=ticker_axis,
        trading_day_axis=trading_day_axis, activity_tercile_fn=activity_tercile_fn,
        context="guarded_activity_tercile",
    )
    present = set(cand["activity_tercile"])
    terciles = ["all"] + [t for t in _ACTIVITY_TERCILE_ORDER if t in present]
    seeds = sorted({int(s) for s in cand[seed_axis].tolist()})
    rows: list[dict[str, Any]] = []
    for tercile in terciles:
        seed_rows: list[dict[str, Any]] = []
        for seed in seeds:
            c = cand[cand[seed_axis].astype(int) == int(seed)]
            b = base[base[seed_axis].astype(int) == int(seed)]
            if tercile != "all":
                c = c[c["activity_tercile"] == tercile]
                b = b[b["activity_tercile"] == tercile]
            row = _guarded_tercile_row(tercile, str(int(seed)), c, b, random_prior)
            rows.append(row)
            seed_rows.append(row)
        rows.append(_guarded_tercile_seed_mean(tercile, seed_rows, random_prior, descriptive_note))
    return pd.DataFrame(rows)[GUARDED_ACTIVITY_TERCILE_COLUMNS]


def build_row_pooled_multiplicity_discount(
    primary_predictions: pd.DataFrame,
    baseline_predictions: pd.DataFrame,
    *,
    families: Sequence[str] | None = None,
    family_axis: str = "table_row_id",
    period_axis: str = "period_id",
    seed_axis: str = "seed",
    is_block_count: int | None = None,
    expected_family_count: int | None = None,
    expected_period_count: int | None = None,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """B6 multiplicity discount recomputed on the BINDING row-pooled estimand
    (closes the review blocker: the shipped ``05_multiplicity_discount.csv`` runs on
    the equal-weight companion 0.005495, not the binding row-pooled 0.006362 that the
    C4 headline cites).

    Each (family, period) cell is the row-pooled-WITHIN-period macro-F1 delta (pool
    the period's rows, mean over seeds -- :func:`_row_pooled_seed_mean_delta`), so the
    CSCV PBO (Bailey et al. 2017) is block-structured over row-pooled blocks. Each
    family's central ``mean_delta`` is the row-pooled-over-ALL-rows binding estimand
    (the TCN primary value reproduces ``pooled_delta_row_pooled``), NOT the equal-weight
    mean of the period cells -- so the discount now centers on the quantity the headline
    cites. ``period_delta_lcb`` is the block Student-t LCB over the period cells; the
    summary row carries the worst-family ``min_family_lcb`` and the descriptive PBO. All
    values DESCRIPTIVE -- never a significance claim (register Tier 1). Emits the same
    ``MULTIPLICITY_DISCOUNT_COLUMNS`` schema as the equal-weight discount so the two can
    be diffed directly. Measure-only over the raw frozen dumps.
    """
    need_c = {family_axis, period_axis, seed_axis, "y_true", "y_pred"}
    need_b = {period_axis, seed_axis, "y_true", "y_pred"}
    for name, frame, need in (
        ("primary_predictions", primary_predictions, need_c),
        ("baseline_predictions", baseline_predictions, need_b),
    ):
        missing = sorted(need - set(frame.columns))
        if missing:
            raise ValueError(f"row_pooled_multiplicity: {name} missing columns {missing}")
    fams = [
        str(f) for f in (
            families if families is not None
            else sorted(set(primary_predictions[family_axis].astype(str)))
        )
    ]
    if not fams:
        raise ValueError("row_pooled_multiplicity: no families to score")
    if expected_family_count is not None and len(fams) != int(expected_family_count):
        raise ValueError(
            f"row_pooled_multiplicity: expected {expected_family_count} families, found "
            f"{len(fams)} ({fams})"
        )
    periods = sorted(set(primary_predictions[period_axis].astype(str)))
    if expected_period_count is not None and len(periods) != int(expected_period_count):
        raise ValueError(
            f"row_pooled_multiplicity: expected {expected_period_count} periods, found "
            f"{len(periods)} ({periods})"
        )
    base = baseline_predictions
    matrix = np.zeros((len(fams), len(periods)), dtype=float)
    family_cis: dict[str, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for i, family in enumerate(fams):
        cand_all = primary_predictions[primary_predictions[family_axis].astype(str) == family]
        if cand_all.empty:
            raise ValueError(f"row_pooled_multiplicity: no rows for family {family!r}")
        period_deltas: list[float] = []
        for j, period in enumerate(periods):
            cc = cand_all[cand_all[period_axis].astype(str) == period]
            bb = base[base[period_axis].astype(str) == period]
            if cc.empty or bb.empty:
                raise ValueError(
                    f"row_pooled_multiplicity: family {family!r} period {period!r} has no "
                    "candidate/baseline rows; the predeclared guarded roster must be complete"
                )
            delta = _row_pooled_seed_mean_delta(cc, bb, seed_axis=seed_axis)
            matrix[i, j] = delta
            period_deltas.append(delta)
        period_deltas_arr = np.asarray(period_deltas, dtype=float)
        block_lcb = float(metrics.compute_metric_lcb(period_deltas_arr))
        binding_central = _row_pooled_seed_mean_delta(cand_all, base, seed_axis=seed_axis)
        family_cis[family] = {"lcb": block_lcb, "mean": binding_central}
        rows.append({
            "row_kind": "family", "family": family,
            "n_periods": int(period_deltas_arr.size),
            "positive_periods": int(np.sum(period_deltas_arr > 0)),
            "mean_delta": binding_central, "period_delta_lcb": block_lcb,
            "min_family_lcb": None, "median_family_lcb": None, "max_family_mean": None,
            "pbo": None, "pbo_n_combinations": None, "pbo_n_trials": None,
            "pbo_n_blocks": None, "pbo_method": None, "seed_aggregation": None, "note": "",
        })
    aggregate = metrics.aggregate_family_delta_cis(family_cis)
    pbo = metrics.cscv_pbo(matrix, is_block_count=is_block_count)
    pbo_method = "cscv_symmetric" if pbo["is_symmetric"] else "cscv_odd_block_floor_ceil_adaptation"
    rows.append({
        "row_kind": "summary", "family": "all",
        "n_periods": int(len(periods)), "positive_periods": None,
        "mean_delta": None, "period_delta_lcb": None,
        "min_family_lcb": aggregate["min_family_lcb"],
        "median_family_lcb": aggregate["median_family_lcb"],
        "max_family_mean": aggregate["max_family_mean"],
        "pbo": pbo["pbo"], "pbo_n_combinations": pbo["n_combinations"],
        "pbo_n_trials": pbo["n_trials"], "pbo_n_blocks": pbo["n_blocks"],
        "pbo_method": pbo_method, "seed_aggregation": "row_pooled_within_period_then_block",
        "note": (
            "BINDING row-pooled estimand: per-family mean_delta is the row-pooled-over-all-rows "
            "pooled_delta (the TCN primary reproduces pooled_delta_row_pooled); PBO and per-family "
            "period_delta_lcb are block-structured over row-pooled-within-period deltas; contrast "
            f"with the equal-weight 05_multiplicity_discount.csv. {descriptive_note}"
        ).strip(),
    })
    return pd.DataFrame(rows)[MULTIPLICITY_DISCOUNT_COLUMNS]


def _guarded_tercile_assign(
    cand: pd.DataFrame,
    base: pd.DataFrame,
    *,
    ticker_axis: str,
    trading_day_axis: str,
    activity_tercile_fn: Any = None,
    context: str = "guarded",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign the activity tercile to candidate rows (reusing the provenance-hashed
    ``diagnostics.activity_terciles`` proxy verbatim) and carry the SAME
    (ticker, trading_day) -> tercile map onto the baseline rows, so candidate and
    baseline (which score the same eval rows) are binned identically. Shared by the
    guarded activity-tercile / base-rate / sentinel builders."""
    if activity_tercile_fn is None:
        from lst_models.diagnostics import activity_terciles as activity_tercile_fn
    cand = cand.copy()
    cand["activity_tercile"] = activity_tercile_fn(cand).astype(str)
    day_map = (
        cand.groupby([ticker_axis, trading_day_axis])["activity_tercile"].first().reset_index()
    )
    base = base.drop(columns=["activity_tercile"], errors="ignore").merge(
        day_map, on=[ticker_axis, trading_day_axis], how="left"
    )
    if bool(base["activity_tercile"].isna().any()):
        n_missing = int(base["activity_tercile"].isna().sum())
        raise ValueError(
            f"{context}: {n_missing} baseline rows have no (ticker, trading_day) match in the "
            "candidate tercile map; candidate and baseline eval rows must align"
        )
    return cand, base


def _macro_f1_delta_row(
    scope: str, slice_val: str, seed: str, cand: pd.DataFrame, base: pd.DataFrame
) -> dict[str, Any]:
    """One (scope, slice, seed) base-rate cell: support, up-rate, dummy floor, delta."""
    nan = float("nan")
    head = {"scope": scope, "slice": slice_val, "seed": seed}
    if len(cand) == 0 or len(base) == 0:
        return {**head, "n_rows": int(len(cand)), "up_rate": nan, "dummy_macro_f1": nan,
                "candidate_macro_f1": nan, "delta_vs_dummy": nan, "note": ""}
    yt = cand["y_true"].to_numpy(dtype=int)
    cm = float(metrics.binary_macro_f1(yt, cand["y_pred"].to_numpy(dtype=int)))
    dm = float(metrics.binary_macro_f1(
        base["y_true"].to_numpy(dtype=int), base["y_pred"].to_numpy(dtype=int)
    ))
    return {**head, "n_rows": int(len(cand)), "up_rate": float(yt.mean()),
            "dummy_macro_f1": dm, "candidate_macro_f1": cm, "delta_vs_dummy": cm - dm, "note": ""}


def _base_rate_seed_mean(scope: str, slice_val: str, seed_rows: list[dict[str, Any]], note: str) -> dict[str, Any]:
    cols = ["n_rows", "up_rate", "dummy_macro_f1", "candidate_macro_f1", "delta_vs_dummy"]
    agg: dict[str, Any] = {}
    for col in cols:
        finite = [float(r[col]) for r in seed_rows if _finite(r[col])]
        agg[col] = float(np.mean(finite)) if finite else float("nan")
    agg["n_rows"] = int(round(agg["n_rows"])) if _finite(agg["n_rows"]) else 0
    return {"scope": scope, "slice": slice_val, "seed": "seed_mean", **agg, "note": str(note)}


def build_guarded_base_rates(
    primary_predictions: pd.DataFrame,
    baseline_predictions: pd.DataFrame,
    *,
    primary_model: str,
    family_axis: str = "table_row_id",
    ticker_axis: str = "ticker",
    trading_day_axis: str = "trading_day",
    period_axis: str = "period_id",
    seed_axis: str = "seed",
    activity_tercile_fn: Any = None,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """#5 regime composition + class balance over the guarded era (measure-only):
    per walk-forward PERIOD and per ACTIVITY TERCILE, the support, base rate
    (``up_rate`` = mean y_true), same-row stratified-dummy macro-F1 floor, candidate
    macro-F1, and delta (plus a seed-mean). Makes the COVID / bear-period composition
    visible (register: the structural-break year drags the edge down) and shows the
    per-tercile dummy floor / base rate are ~constant, so the calm-bar edge is not a
    class-balance artifact (register E). Descriptive only -- no operating point."""
    need_c = {family_axis, ticker_axis, trading_day_axis, period_axis, seed_axis, "y_true", "y_pred"}
    need_b = {ticker_axis, trading_day_axis, period_axis, seed_axis, "y_true", "y_pred"}
    for name, frame, need in (
        ("primary_predictions", primary_predictions, need_c),
        ("baseline_predictions", baseline_predictions, need_b),
    ):
        missing = sorted(need - set(frame.columns))
        if missing:
            raise ValueError(f"guarded_base_rates: {name} missing columns {missing}")
    cand = primary_predictions[
        primary_predictions[family_axis].astype(str) == str(primary_model)
    ].copy()
    if cand.empty:
        raise ValueError(f"guarded_base_rates: no rows for primary model {primary_model!r}")
    cand, base = _guarded_tercile_assign(
        cand, baseline_predictions, ticker_axis=ticker_axis,
        trading_day_axis=trading_day_axis, activity_tercile_fn=activity_tercile_fn,
        context="guarded_base_rates",
    )
    seeds = sorted({int(s) for s in cand[seed_axis].tolist()})
    terciles = [t for t in _ACTIVITY_TERCILE_ORDER if t in set(cand["activity_tercile"])]
    periods = sorted(set(cand[period_axis].astype(str)))
    rows: list[dict[str, Any]] = []
    for scope, axis, values in (("period", period_axis, periods), ("activity_tercile", "activity_tercile", terciles)):
        for val in values:
            seed_rows: list[dict[str, Any]] = []
            for seed in seeds:
                c = cand[cand[seed_axis].astype(int) == int(seed)]
                b = base[base[seed_axis].astype(int) == int(seed)]
                c = c[c[axis].astype(str) == val]
                b = b[b[axis].astype(str) == val]
                row = _macro_f1_delta_row(scope, val, str(int(seed)), c, b)
                rows.append(row)
                seed_rows.append(row)
            rows.append(_base_rate_seed_mean(scope, val, seed_rows, descriptive_note))
    return pd.DataFrame(rows)[GUARDED_BASE_RATE_COLUMNS]


def _shuffle_within_groups(values: np.ndarray, codes: np.ndarray, base_order: np.ndarray, rng) -> np.ndarray:
    """Vectorized within-group permutation: return ``values`` permuted within each
    group (group id = ``codes``); deterministic given ``rng``. lexsort primary key is
    the group, secondary key is a random draw -> random order within each group."""
    r = rng.random(values.shape[0])
    order = np.lexsort((r, codes))
    out = np.empty_like(values)
    out[base_order] = values[order]
    return out


def build_guarded_label_shuffle_sentinel(
    primary_predictions: pd.DataFrame,
    baseline_predictions: pd.DataFrame,
    *,
    primary_model: str,
    family_axis: str = "table_row_id",
    ticker_axis: str = "ticker",
    trading_day_axis: str = "trading_day",
    seed_axis: str = "seed",
    n_perms: int = 50,
    base_seed: int = 0,
    activity_tercile_fn: Any = None,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """E within-day label-shuffle negative control (measure-only leakage sentinel,
    register Tier 1). Permute y_true WITHIN each (ticker, trading_day) and recompute
    the frozen candidate's per-tercile macro-F1 over ``n_perms`` permutations; a
    genuine, leakage-free edge must NOT survive the shuffle -- the observed macro-F1
    must exceed the per-tercile shuffled null (``observed_exceeds_shuffle_max`` =
    observed > worst shuffle). NOTE the shuffled null can fall BELOW the
    stratified-dummy floor, because the candidate's prediction class-balance differs
    from the dummy's, so the correct test is 'observed edge clears the permutation
    null', not 'shuffled delta == 0'. The candidate's predictions are fixed; only the
    labels are permuted, so an observed edge that did NOT clear the null would
    indicate within-day leakage or a base-rate / construction artifact. Deterministic
    given ``base_seed``. Descriptive negative control -- never a significance test."""
    need_c = {family_axis, ticker_axis, trading_day_axis, seed_axis, "y_true", "y_pred"}
    need_b = {ticker_axis, trading_day_axis, seed_axis, "y_true", "y_pred"}
    for name, frame, need in (
        ("primary_predictions", primary_predictions, need_c),
        ("baseline_predictions", baseline_predictions, need_b),
    ):
        missing = sorted(need - set(frame.columns))
        if missing:
            raise ValueError(f"guarded_sentinel: {name} missing columns {missing}")
    if int(n_perms) < 1:
        raise ValueError("guarded_sentinel: n_perms must be >= 1")
    cand = primary_predictions[
        primary_predictions[family_axis].astype(str) == str(primary_model)
    ].copy()
    if cand.empty:
        raise ValueError(f"guarded_sentinel: no rows for primary model {primary_model!r}")
    cand, base = _guarded_tercile_assign(
        cand, baseline_predictions, ticker_axis=ticker_axis,
        trading_day_axis=trading_day_axis, activity_tercile_fn=activity_tercile_fn,
        context="guarded_sentinel",
    )
    seeds = sorted({int(s) for s in cand[seed_axis].tolist()})
    terciles = ["all"] + [t for t in _ACTIVITY_TERCILE_ORDER if t in set(cand["activity_tercile"])]
    obs: dict[str, list[float]] = {t: [] for t in terciles}
    dum: dict[str, list[float]] = {t: [] for t in terciles}
    shuf: dict[str, list[float]] = {t: [] for t in terciles}
    nrows: dict[str, list[int]] = {t: [] for t in terciles}
    for seed in seeds:
        cs = cand[cand[seed_axis].astype(int) == int(seed)]
        bs = base[base[seed_axis].astype(int) == int(seed)]
        yt = cs["y_true"].to_numpy(dtype=int)
        yp = cs["y_pred"].to_numpy(dtype=int)
        terc = cs["activity_tercile"].to_numpy(dtype=str)
        codes = pd.factorize(cs[ticker_axis].astype(str) + "\x00" + cs[trading_day_axis].astype(str))[0]
        base_order = np.argsort(codes, kind="stable")
        byt = bs["y_true"].to_numpy(dtype=int)
        byp = bs["y_pred"].to_numpy(dtype=int)
        bterc = bs["activity_tercile"].to_numpy(dtype=str)
        for t in terciles:
            m = np.ones(len(yt), dtype=bool) if t == "all" else (terc == t)
            bm = np.ones(len(byt), dtype=bool) if t == "all" else (bterc == t)
            obs[t].append(float(metrics.binary_macro_f1(yt[m], yp[m])))
            dum[t].append(float(metrics.binary_macro_f1(byt[bm], byp[bm])))
            nrows[t].append(int(m.sum()))
        for k in range(int(n_perms)):
            rng = np.random.default_rng(int(base_seed) + k * 100003 + int(seed))
            sh = _shuffle_within_groups(yt, codes, base_order, rng)
            for t in terciles:
                m = np.ones(len(yt), dtype=bool) if t == "all" else (terc == t)
                shuf[t].append(float(metrics.binary_macro_f1(yp[m], sh[m])))
    rows: list[dict[str, Any]] = []
    for t in terciles:
        om = float(np.mean(obs[t])); dm = float(np.mean(dum[t]))
        sm = float(np.mean(shuf[t])); smax = float(np.max(shuf[t]))
        rows.append({
            "activity_tercile": t, "n_rows": int(round(float(np.mean(nrows[t])))),
            "observed_macro_f1": om, "dummy_macro_f1": dm, "observed_delta_vs_dummy": om - dm,
            "shuffled_macro_f1_mean": sm, "shuffled_macro_f1_max": smax,
            "shuffled_delta_mean": sm - dm, "shuffled_delta_max": smax - dm,
            "n_perms": int(n_perms), "observed_exceeds_shuffle_max": bool(om > smax),
            "note": str(descriptive_note) if t == "all" else "",
        })
    return pd.DataFrame(rows)[GUARDED_SENTINEL_COLUMNS]

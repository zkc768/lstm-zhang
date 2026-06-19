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

"""Public V2.1 stage entry point."""

from __future__ import annotations

from typing import Any, Mapping

from lst_models.guarded_walkforward import (
    READOUT_TIER,
    PER_TICKER_READOUT_COLUMNS,
    PREDICTION_COLUMNS,
    SCOPE,
    V21Result,
    WALKFORWARD_READOUT_COLUMNS,
    _WalkforwardLedger,
    _aggregate_and_judge,
    _build_comparison_table,
    _build_period_registry,
    _checkpoint_manifest_payload,
    _protocol_provenance_fields,
    _validate_config,
    run_guarded_walkforward,
)


def run_stage(config: Mapping[str, Any]) -> V21Result:
    return run_guarded_walkforward(config)

from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from lst_models import synthesis  # noqa: E402


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "05_thesis_synthesis.yaml")
STAGE04_CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "04_diagnostics_ablation.yaml")
V2_1_CONFIG = load_yaml(
    REPO_ROOT / "configs" / "stages" / "v2_1_guarded_walkforward_readout.yaml"
)
UPSTREAM_KEYS = ("stage03", "stage04", "v2_1")


def test_scope_and_measure_only_flags() -> None:
    assert CONFIG["stage_name"] == "05_thesis_synthesis"
    assert CONFIG["route"] == "lst_models"
    assert CONFIG["scope"] == "synthesis_measure_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["official_validation_contact"] == "read_frozen_artifacts_only"
    assert CONFIG["new_scoring_events"] == 0
    assert CONFIG["official_validation_for_selection"] is False
    assert CONFIG["no_final_model_selected"] is True
    assert CONFIG["reads_guarded_walkforward_artifacts"] is True


def test_upstream_run_id_chain_matches_stage04_and_v2_1_configs() -> None:
    inputs = CONFIG["inputs"]
    # The binding invariant is a SHARED frozen Stage 03 (what the runtime gate
    # enforces): Stage 05, the Stage 04 config, and V2.1 all chain to it.
    assert inputs["stage03_run_id"] == STAGE04_CONFIG["inputs"]["stage03_run_id"]
    assert inputs["stage03_run_id"] == V2_1_CONFIG["inputs"]["stage03_run_id"]
    # B4: Stage 05 intentionally reads the LATEST Stage 04 diagnostics run (the B4
    # re-run with the per-tercile bootstrap), which is newer than the Stage 04 run
    # V2.1 consumed. Both use the same Stage 04 config (same Stage 03), so they are
    # NOT required to be the same run id -- only siblings off the shared Stage 03.
    assert inputs["stage04_run_id"] >= V2_1_CONFIG["inputs"]["stage04_run_id"]
    for key in UPSTREAM_KEYS:
        assert inputs[f"{key}_run_id"] in inputs[f"{key}_runtime_run_dir"]
        assert inputs[f"{key}_run_id"] in str(inputs[f"{key}_drive_path_parts"])


def test_required_upstream_artifacts_cover_decision_records() -> None:
    inputs = CONFIG["inputs"]
    assert "03_decision_record.json" in inputs["required_stage03_artifacts"]
    assert "04_diagnostics_report.json" in inputs["required_stage04_artifacts"]
    assert "v2_1_decision_record.json" in inputs["required_v2_1_artifacts"]
    # cited supporting artifacts must be gated too (claim->evidence chain)
    assert "04_sentinel_summary.csv" in inputs["required_stage04_artifacts"]
    assert "04_robustness_slices.csv" in inputs["required_stage04_artifacts"]
    assert "v2_1_comparison_table.csv" in inputs["required_v2_1_artifacts"]
    assert "v2_1_walkforward_readout.csv" in inputs["required_v2_1_artifacts"]  # B6 delta matrix
    assert "03_validation_predictions.csv" in inputs["required_stage03_artifacts"]  # B7 dump
    for key in UPSTREAM_KEYS:
        for name in ("run_manifest.json", "artifact_inventory.csv"):
            assert name in inputs[f"required_{key}_artifacts"]


def test_required_upstream_decisions_gate_met_claims() -> None:
    required = CONFIG["required_upstream_decisions"]
    assert required["stage03"] == "met_predeclared_validation_readout_criteria"
    assert required["v2_1"] == "met_predeclared_guarded_stability_criteria"


def test_every_claim_cites_a_gated_supporting_artifact() -> None:
    inputs = CONFIG["inputs"]
    gated = {key: set(inputs[f"required_{key}_artifacts"]) for key in UPSTREAM_KEYS}
    for claim in CONFIG["claim_boundary_register"]["claims"]:
        key = claim["supporting_run_id_key"]
        assert claim["supporting_artifact"] in gated[key], (
            f"{claim['claim_id']} cites un-gated {claim['supporting_artifact']}"
        )


def test_required_artifact_list_closes_with_runner_constant() -> None:
    from lst_models.stages.thesis_synthesis import REQUIRED_STAGE05_ARTIFACTS

    outputs = CONFIG["outputs"]
    stage_artifacts = sorted(value for key, value in outputs.items() if key != "output_dir")
    assert sorted(REQUIRED_STAGE05_ARTIFACTS) == stage_artifacts
    assert "drive_backup_manifest.json" not in REQUIRED_STAGE05_ARTIFACTS
    for key in ("validation_budget_ledger", "claim_boundary_register",
                "expectation_calibration", "multiplicity_discount", "selective_autopsy",
                "synthesis_report"):
        assert outputs[key].startswith("05_")


def test_evidence_domains_are_the_canonical_three() -> None:
    assert tuple(CONFIG["evidence_domains"]) == synthesis.EVIDENCE_DOMAINS


def test_budget_ledger_stages_well_formed() -> None:
    stages = CONFIG["budget_ledger"]["stages"]
    by_stage = {entry["stage_name"]: entry for entry in stages}
    assert set(by_stage) == {
        "03_frozen_validation_readout",
        "04_diagnostics_ablation",
        "v2_1_guarded_walkforward_readout",
    }
    assert by_stage["03_frozen_validation_readout"]["events_field"] == (
        "official_validation_scoring_events"
    )
    assert by_stage["04_diagnostics_ablation"]["events_field"] == (
        "new_validation_fit_predict_events"
    )
    assert by_stage["v2_1_guarded_walkforward_readout"]["events_field"] == "guarded_scoring_events"
    for entry in stages:
        assert entry["evidence_domain"] in synthesis.EVIDENCE_DOMAINS
        assert entry["run_id_key"] in UPSTREAM_KEYS
        assert entry["events_source_key"] in UPSTREAM_KEYS
        assert entry["for_selection"] is False


def test_claims_use_only_allowed_wording_and_known_domains() -> None:
    forbidden = CONFIG["forbidden"]["wording"]
    claims = CONFIG["claim_boundary_register"]["claims"]
    assert claims, "claim register must declare at least one claim"
    claim_ids = [claim["claim_id"] for claim in claims]
    assert len(claim_ids) == len(set(claim_ids))
    assert any(bool(claim["is_limitation"]) for claim in claims), "limitations must be present"
    for claim in claims:
        assert claim["evidence_domain"] in synthesis.EVIDENCE_DOMAINS
        assert claim["supporting_run_id_key"] in UPSTREAM_KEYS
        hits = synthesis.find_forbidden_wording(claim["statement"], forbidden)
        assert not hits, f"forbidden wording in {claim['claim_id']}: {hits}"


def test_expectation_rows_have_traceable_values() -> None:
    forbidden = CONFIG["forbidden"]["wording"]
    rows = CONFIG["expectation_calibration"]["rows"]
    assert rows
    saw_literature = saw_measured = False
    metric_kinds: set[str] = set()
    for row in rows:
        assert not synthesis.find_forbidden_wording(row.get("context", ""), forbidden)
        assert str(row.get("metric_kind", "")).strip(), f"{row['metric_id']} missing metric_kind"
        metric_kinds.add(row["metric_kind"])
        if row.get("value_source") == "config_literature":
            saw_literature = True
            assert "value" in row
            assert row["metric_kind"] == "direction_accuracy"  # accuracy, not macro-F1
            assert str(row.get("citation", "")).strip()  # literature anchors are traceable
        else:
            saw_measured = True
            assert row["value_source_key"] in UPSTREAM_KEYS
            assert row["value_field"]
            assert row["metric_kind"] in {"macro_f1", "macro_f1_delta"}
    assert saw_literature and saw_measured
    # accuracy and macro-F1 are both present and explicitly distinguished
    assert "direction_accuracy" in metric_kinds and metric_kinds & {"macro_f1", "macro_f1_delta"}


def test_forbidden_wording_superset_present() -> None:
    forbidden = CONFIG["forbidden"]["wording"]
    for phrase in (
        "final model", "clean test", "clean holdout", "selected by official validation",
        "chosen threshold", "profitable", "walk-forward winner", "statistically significant",
    ):
        assert phrase in forbidden


def test_guardrails_and_deferred_items_present() -> None:
    assert CONFIG["kb_wording_guardrails"], "KB wording guardrails must be present (S5.5)"
    deferred = CONFIG["deferred_synthesis_items"]
    joined = " ".join(deferred).lower()
    # B6 (PBO/CSCV), B7 (AUGRC/MDE/abstention), and B8's four-estimand contrast +
    # equal-weight LOO are now BUILT -> no longer deferred
    assert "pbo" not in joined and "min_family_lcb" not in joined
    assert "augrc" not in joined and "abstention" not in joined
    assert "estimand" not in joined  # B8 estimand contrast is built, not deferred
    # what remains deferred is only the ROW-POOLED LOO from the raw dump
    assert "row_pooled" in joined and "leave_one_period_out" in joined
    assert "raw" in joined and "v2_1_predictions" in joined


def test_estimand_contrast_and_loo_blocks_well_formed() -> None:
    loo = CONFIG["loo_robustness"]
    assert loo["source_key"] == "v2_1"
    assert loo["period_artifact"] == "v2_1_period_summary.csv"
    assert loo["per_ticker_artifact"] == "v2_1_per_ticker_readout.csv"
    assert loo["primary_model"] == "tcn_frozen_primary"
    assert loo["expected_period_count"] == 7
    assert loo["expected_ticker_count"] == 5
    # the new B8 input aggregates are entry-gated required artifacts
    inputs = CONFIG["inputs"]
    assert "v2_1_period_summary.csv" in inputs["required_v2_1_artifacts"]
    assert "v2_1_per_ticker_readout.csv" in inputs["required_v2_1_artifacts"]
    # the contrast/LOO outputs close with the runner constant
    assert CONFIG["outputs"]["estimand_contrast"] == "05_estimand_contrast.csv"
    assert CONFIG["outputs"]["loo_robustness"] == "05_loo_robustness.csv"


def test_selective_autopsy_block_well_formed() -> None:
    block = CONFIG["selective_autopsy"]
    assert block["dump_source_key"] == "stage03"
    assert block["dump_artifact"] == "03_validation_predictions.csv"
    assert block["mde_source_key"] == "stage04"
    assert block["mde_artifact"] == "04_robustness_slices.csv"
    assert block["activity_axis"] == "activity_tercile"
    assert block["no_operating_point"] is True
    assert block["expected_seeds"] == [101, 202]
    # accuracy-based diagnostic, never an operating-point/tradeability claim
    assert not synthesis.find_forbidden_wording(block["descriptive_note"], CONFIG["forbidden"]["wording"])


def test_multiplicity_discount_block_well_formed() -> None:
    block = CONFIG["multiplicity_discount"]
    assert block["source_key"] == "v2_1"
    assert block["source_artifact"] == "v2_1_walkforward_readout.csv"
    assert block["family_axis"] == "table_row_id"
    assert block["period_axis"] == "period_id"
    assert block["delta_field"] == "delta_macro_f1_vs_stratified_dummy_train_prior"
    assert block["model_row_kind"] == "model"
    # fail-closed roster expectations (the predeclared 56-event ledger)
    assert block["expected_family_count"] == 4
    assert block["expected_period_count"] == 7
    assert block["expected_seeds_per_cell"] == 2
    assert 4 * 7 * 2 == 56  # roster closes to the guarded scoring-event budget
    assert block["seed_aggregation"] == "mean_over_seeds"  # seed aggregation is explicit
    # descriptive note must not itself contain a forbidden phrase
    assert not synthesis.find_forbidden_wording(block["descriptive_note"], CONFIG["forbidden"]["wording"])

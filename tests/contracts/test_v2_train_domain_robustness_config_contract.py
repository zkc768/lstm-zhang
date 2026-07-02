"""Config contracts for the two preregistered train-domain robustness stages.

Pins the repo sidecar configs (`configs/stages/v2_band_horizon_sensitivity.yaml`,
`configs/stages/v2_embargo_robustness.yaml`) to their preregistrations: exact
upstream run-id pins, Stage 02 machinery parity (fold-row caps, torch training
defaults, seeds), the frozen cross / embargo rule, budget arithmetic, scan
guards, and sidecar file existence. No fitting, no data.
"""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]

BHS_CONFIG_PATH = ROOT / "configs" / "stages" / "v2_band_horizon_sensitivity.yaml"
EMB_CONFIG_PATH = ROOT / "configs" / "stages" / "v2_embargo_robustness.yaml"
STAGE02_CONFIG_PATH = ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml"

CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_STAGE02_RUN_ID = "20260610_082130_797479"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _common_contract(config: dict, stage_name: str) -> None:
    assert config["stage_name"] == stage_name
    assert config["route"] == "lst_models"
    assert config["scope"] == "validation_only"
    assert config["holdout_test_contact"] is False
    assert config["train_domain_only"] is True
    inputs = config["inputs"]
    assert inputs["stage00_run_id"] == CURRENT_STAGE00_RUN_ID
    assert inputs["stage01_run_id"] == CURRENT_STAGE01_RUN_ID
    assert inputs["stage02_run_id"] == CURRENT_STAGE02_RUN_ID
    assert "01_feature_window_search_summary.csv" in inputs["required_stage01_artifacts"]
    assert "02_hpo_plan_ledger.csv" in inputs["required_stage02_artifacts"]
    assert inputs["raw_data_manifest"] == "configs/lst_models_data.yaml"
    assert config["candidate"]["candidate_id"] == "price_volume_time_w20"
    model = config["model"]
    assert model["family"] == "tcn"
    assert model["probe_id"] == "tcn_tiny"
    assert model["hpo_profile_id"] == "tcn_p01"
    assert model["search_space"] == "configs/models/tcn/search_space.yaml"
    train_inner = config["train_inner"]
    assert train_inner["n_folds"] == 3
    assert train_inner["seeds"] == [101, 202]
    assert train_inner["official_validation_for_selection"] is False
    assert config["reading_rules"]["primary_baseline"] == "stratified_dummy_train_prior"
    notebook = ROOT / inputs["notebook_path"]
    assert notebook.exists(), notebook


def _stage02_machinery_parity(config: dict, stage02: dict) -> None:
    assert config["sample_policy"] == stage02["hpo_sample_policy"]
    assert config["probe_training_defaults"]["torch"] == (
        stage02["probe_training_defaults"]["torch"]
    )
    assert config["train_inner"]["seeds"] == stage02["train_inner"]["seeds"]
    assert config["train_inner"]["n_folds"] == stage02["train_inner"]["n_folds"]
    assert config["inputs"]["stage00_run_id"] == stage02["inputs"]["stage00_run_id"]
    assert config["inputs"]["stage01_run_id"] == stage02["inputs"]["stage01_run_id"]


def test_bhs_config_contract() -> None:
    config = _load(BHS_CONFIG_PATH)
    _common_contract(config, "v2_band_horizon_sensitivity")
    _stage02_machinery_parity(config, _load(STAGE02_CONFIG_PATH))
    assert config["sensitivity_scan_no_cell_selected"] is True
    assert config["evidence_status"] == (
        "train_inner_protocol_sensitivity_scan_no_cell_selected"
    )
    label_scan = config["label_scan"]
    assert label_scan["operator"] == "endpoint_cumulative_return"
    assert label_scan["frozen_cell"] == {"horizon_k": 9, "no_trade_band_bps": 3.0}
    cells = label_scan["cells"]
    assert [cell["cell_id"] for cell in cells] == [
        "h09_bps2p0", "h09_bps3p0", "h09_bps4p0", "h06_bps3p0", "h12_bps3p0",
    ]
    band_cells = [cell for cell in cells if cell["horizon_k"] == 9]
    horizon_cells = [cell for cell in cells if cell["no_trade_band_bps"] == 3.0]
    assert [cell["no_trade_band_bps"] for cell in band_cells] == [2.0, 3.0, 4.0]
    assert sorted(cell["horizon_k"] for cell in horizon_cells) == [6, 9, 12]
    # A cross, not a grid: every cell sits on one of the two frozen axes.
    for cell in cells:
        assert cell["horizon_k"] == 9 or cell["no_trade_band_bps"] == 3.0
    planned = len(cells) * config["train_inner"]["n_folds"] * len(
        config["train_inner"]["seeds"]
    )
    assert planned == 30
    assert planned <= config["budget"]["max_planned_fit_rows"]
    reading = config["reading_rules"]
    assert reading["cells_are_never_ranked"] is True
    assert reading["no_alternative_cell_recommended"] is True
    forbidden = config["forbidden"]["search_axes"]
    for axis in ("label_operator", "additional_cells_after_first_fit", "cell_ranking",
                 "cell_selection", "calendar_split_boundaries"):
        assert axis in forbidden
    prereg = ROOT / "docs" / "protocols" / (
        "v2_band_horizon_sensitivity_preregistration_20260701.md"
    )
    assert prereg.exists()
    assert (ROOT / "src" / "lst_models" / "stages" / "band_horizon_sensitivity.py").exists()


def test_emb_config_contract() -> None:
    config = _load(EMB_CONFIG_PATH)
    _common_contract(config, "v2_embargo_robustness")
    _stage02_machinery_parity(config, _load(STAGE02_CONFIG_PATH))
    assert config["evidence_status"] == "train_inner_embargo_robustness_control"
    embargo = config["embargo"]
    assert embargo["rule_id"] == "drop_first_eval_trading_day_per_fold"
    assert embargo["embargo_trading_days"] == 1
    assert embargo["fits_shared_across_variants"] is True
    assert [variant["variant_id"] for variant in embargo["variants"]] == [
        "no_embargo", "embargo_1day",
    ]
    planned_fits = config["train_inner"]["n_folds"] * len(config["train_inner"]["seeds"])
    planned_readouts = planned_fits * len(embargo["variants"])
    assert planned_fits == 6
    assert planned_readouts == 12
    assert planned_fits <= config["budget"]["max_planned_fit_rows"]
    assert planned_readouts <= config["budget"]["max_readout_rows"]
    reading = config["reading_rules"]
    assert reading["shrinkage_fraction"] == 0.5
    assert reading["evaluated_per_seed_and_must_agree"] is True
    forbidden = config["forbidden"]["search_axes"]
    for axis in ("label_operator", "horizon_k", "no_trade_band_bps",
                 "embargo_length_after_first_fit", "additional_variants_after_first_fit"):
        assert axis in forbidden
    prereg = ROOT / "docs" / "protocols" / (
        "v2_embargo_robustness_preregistration_20260701.md"
    )
    assert prereg.exists()
    assert (ROOT / "src" / "lst_models" / "stages" / "embargo_robustness.py").exists()


def test_robustness_configs_do_not_reuse_taken_package_names() -> None:
    # Distinct from the in-flight v2 packages (seed addendum, positive control,
    # half-spread control): file names and stage names must not collide.
    taken = {
        "v2_seed_addendum_readout",
        "v2_synthetic_positive_control",
        "v2_halfspread_control",
    }
    for path in (BHS_CONFIG_PATH, EMB_CONFIG_PATH):
        config = _load(path)
        assert config["stage_name"] not in taken

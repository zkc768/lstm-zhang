"""Stage 05 thesis-synthesis run_stage smoke tests.

Exercises the REAL committed config (budget ledger, claim register, expectation
calibration, guardrails) against a tiny synthetic frozen Stage 03 / Stage 04 /
V2.1 chain: fail-closed entry gates, measure-only synthesis, numbers resolved
from frozen record fields, and a no-forbidden-wording happy path. No fits, no
scoring, no model objects.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import diagnostics, synthesis  # noqa: E402
from lst_models.artifacts import write_artifact_inventory, write_json  # noqa: E402
from lst_models.stages import thesis_synthesis as stage05  # noqa: E402
from lst_models.stages.thesis_synthesis import run_stage  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "stages" / "05_thesis_synthesis.yaml"


def _load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class Stage05Dirs:
    """Synthetic frozen Stage 03 / Stage 04 / V2.1 run folders with real sha256
    inventories and decision records carrying exactly the fields the committed
    Stage 05 config resolves."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.base_config = _load_config()
        ids = self.base_config["inputs"]
        self.stage03_run_id = str(ids["stage03_run_id"])
        self.stage04_run_id = str(ids["stage04_run_id"])
        self.v2_1_run_id = str(ids["v2_1_run_id"])
        self.dirs = {
            "stage03": tmp_path / "stage03" / self.stage03_run_id,
            "stage04": tmp_path / "stage04" / self.stage04_run_id,
            "v2_1": tmp_path / "v2_1" / self.v2_1_run_id,
        }
        self.output_dir = tmp_path / "out"
        self.notebook_path = tmp_path / "05_thesis_synthesis_colab.ipynb"
        self.notebook_path.write_text("{}", encoding="utf-8")
        self._write_stage03()
        self._write_stage04()
        self._write_v2_1()

    # ----------------------------------------------------------- records --
    def _stage03_record(self) -> dict:
        return {
            "decision": "met_predeclared_validation_readout_criteria",
            "readout_complete": True,
            "holdout_test_contact": False,
            "official_validation_for_selection": False,
            "official_validation_scoring_events": 2,
            "scoring_event_ledger": [{"seed": 101, "n_rows": 24}, {"seed": 202, "n_rows": 24}],
            "source_stage00_run_id": "stage00",
            "source_stage01_run_id": "stage01",
            "source_stage02_run_id": "stage02",
            "aggregate": {
                "mean_macro_f1": 0.5170,
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": 0.0169,
                "mean_delta_macro_f1_vs_majority_train_prior": 0.1883,
                "positive_ticker_count": 5,
            },
        }

    def _stage04_report(self) -> dict:
        return {
            "route": "lst_models",
            "stage_name": "04_diagnostics_ablation",
            "stage03_decision": "met_predeclared_validation_readout_criteria",
            "new_validation_fit_predict_events": 0,
            "official_validation_scoring_events": 0,
            "holdout_test_contact": False,
            "official_validation_for_selection": False,
            "no_final_model_selected": True,
            "source_stage03_run_id": self.stage03_run_id,
        }

    def _stage04_manifest(self) -> dict:
        return {
            "stage_name": "04_diagnostics_ablation",
            "holdout_test_contact": False,
            "official_validation_for_selection": False,
            "official_validation_contact": "read_frozen_artifacts_only",
            "no_final_model_selected": True,
            "source_stage03_run_id": self.stage03_run_id,
        }

    def _v2_1_record(self) -> dict:
        return {
            "route": "lst_models",
            "stage_name": "v2_1_guarded_walkforward_readout",
            "decision": "met_predeclared_guarded_stability_criteria",
            "readout_complete": True,
            "holdout_test_contact": True,
            "holdout_contact_tier": "guarded_historically_contacted",
            "clean_test_claim": False,
            "official_validation_for_selection": False,
            "no_final_model_selected": True,
            "guarded_scoring_events": 56,
            "scoring_event_ledger": [{"event_index": n} for n in range(56)],
            "positive_period_count": 5,
            "pooled_delta": 0.006362,
            "pooled_delta_estimand": "row_pooled",
            "pooled_delta_equal_weight": 0.005439,
            "pooled_delta_row_pooled": 0.006362,
            "pooled_delta_row_pooled_available": True,
            "source_stage03_run_id": self.stage03_run_id,
            "source_stage04_run_id": self.stage04_run_id,
        }

    # --------------------------------------------------------- folders ----
    def _write_folder(
        self, key: str, json_records: dict[str, dict],
        csv_records: dict[str, pd.DataFrame] | None = None,
    ) -> None:
        run_dir = self.dirs[key]
        run_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in json_records.items():
            write_json(run_dir / name, payload)
        for name, frame in (csv_records or {}).items():
            frame.to_csv(run_dir / name, index=False)
        names = list(json_records) + list(csv_records or {})
        write_artifact_inventory(run_dir, {name: run_dir / name for name in names})

    def _write_stage03(self) -> None:
        self._write_folder(
            "stage03",
            {
                "run_manifest.json": {"holdout_test_contact": False,
                                      "official_validation_for_selection": False},
                "03_decision_record.json": self._stage03_record(),
            },
            {"03_validation_predictions.csv": self._stage03_dump()},
        )

    def _stage03_dump(self) -> pd.DataFrame:
        # 2 seeds x 2 tickers x 6 trading days x 2 rows = 24 rows/seed (48 total),
        # >= 3 days/ticker so activity terciles populate low/mid/high.
        rng = np.random.default_rng(11)
        base = pd.Timestamp("2014-03-03")
        rows = []
        for seed in (101, 202):
            for t_i, ticker in enumerate(("AAA", "BBB")):
                for d in range(6):
                    day = base + pd.Timedelta(days=d + 7 * t_i)
                    for r in range(2):
                        ts = day + pd.Timedelta(hours=10, minutes=5 * (d + r))
                        y_true = int((d + r + t_i) % 2)
                        correct = ((d * 2 + r + seed) % 3) != 0  # ~2/3 edge
                        target = y_true if correct else 1 - y_true
                        p_up = float(np.clip(
                            0.5 + (0.30 if target == 1 else -0.30) + rng.normal(0, 0.04), 0.01, 0.99
                        ))
                        rows.append({
                            "candidate_role": "primary", "candidate_id": "price_volume_time_w20",
                            "model_family": "tcn", "hpo_profile_id": "tcn_p01", "seed": seed,
                            "sample_id": f"{ticker}_{seed}_{d}_{r}", "ticker": ticker,
                            "target_timestamp": ts.isoformat(),
                            "trading_day": day.strftime("%Y-%m-%d"),
                            "y_true": y_true, "p_up": p_up, "y_pred": int(p_up >= 0.5),
                            "scope": "validation_only",
                        })
        return pd.DataFrame(rows)[diagnostics.DUMP_COLUMNS]

    def _write_stage04(self) -> None:
        self._write_folder(
            "stage04",
            {
                "run_manifest.json": self._stage04_manifest(),
                "04_diagnostics_report.json": self._stage04_report(),
            },
            {
                "04_sentinel_summary.csv": pd.DataFrame(
                    [{"sentinel": "label_shuffle", "label_shuffle_p_value": 0.004975}]
                ),
                "04_robustness_slices.csv": self._robustness_slices(),
            },
        )

    def _robustness_slices(self) -> pd.DataFrame:
        # per-seed + per-activity-tercile block-bootstrap rows (the B7 MDE source),
        # mirroring register F1: low +0.054 clears, mid +0.019 borderline, high -0.015
        # below random and does NOT clear its MDE.
        tercile_ci = {
            "low": (0.054, 0.030, 0.078),
            "mid": (0.019, -0.005, 0.043),
            "high": (-0.015, -0.040, 0.010),
        }
        rows = []
        for seed in (101, 202):
            rows.append({
                "seed": seed, "slice_axis": "seed", "slice_value": str(seed),
                "delta_macro_f1_vs_stratified_dummy_train_prior": 0.0169,
                "bootstrap_delta_lcb": 0.011, "bootstrap_delta_ucb": 0.022,
            })
            for tercile, (delta, lcb, ucb) in tercile_ci.items():
                rows.append({
                    "seed": seed, "slice_axis": "activity_tercile", "slice_value": tercile,
                    "delta_macro_f1_vs_stratified_dummy_train_prior": delta,
                    "bootstrap_delta_lcb": lcb, "bootstrap_delta_ucb": ucb,
                })
        return pd.DataFrame(rows)

    def _write_v2_1(self) -> None:
        self._write_folder(
            "v2_1",
            {
                "run_manifest.json": {"holdout_test_contact": True,
                                      "holdout_contact_tier": "guarded_historically_contacted",
                                      "no_final_model_selected": True},
                "v2_1_decision_record.json": self._v2_1_record(),
            },
            {
                "v2_1_comparison_table.csv": pd.DataFrame(
                    [{"Model": "TCN", "Mean delta vs Dummy": 0.0054},
                     {"Model": "LightGBM", "Mean delta vs Dummy": 0.0069}]
                ),
                "v2_1_walkforward_readout.csv": self._v2_1_readout(),
            },
        )

    def _v2_1_readout(self) -> pd.DataFrame:
        # 4 families x 7 periods x 2 seeds = 56 completed model rows
        families = {
            "tcn_frozen_primary": 0.0050,
            "lightgbm_family_best": 0.0069,
            "standard_dlinear_family_best": 0.0042,
            "ms_dlinear_tcn_family_best": 0.0055,
        }
        rows = []
        for family, base in families.items():
            for period_index in range(7):
                period_offset = (period_index - 3) * 0.0008
                for seed in (101, 202):
                    seed_jitter = 0.0003 if seed == 101 else -0.0003
                    rows.append({
                        "table_row_id": family, "row_kind": "model",
                        "model_family": family.split("_")[0],
                        "period_id": f"wf_p{period_index + 1}", "seed": seed,
                        "delta_macro_f1_vs_stratified_dummy_train_prior":
                            base + period_offset + seed_jitter,
                        "fit_status": "completed",
                    })
        return pd.DataFrame(rows)

    # ----------------------------------------------------------- config ---
    def config(self) -> dict:
        config = _load_config()
        inputs = config["inputs"]
        for key in ("stage03", "stage04", "v2_1"):
            inputs[f"{key}_runtime_run_dir"] = str(self.dirs[key])
        inputs["notebook_path"] = str(self.notebook_path)
        config["outputs"]["output_dir"] = str(self.output_dir)
        # fixture dump is tiny; align the gate's expected row count
        config["selective_autopsy"]["expected_dump_rows"] = 48
        return config

    # --------------------------------------------------------- mutators ---
    def override_record(self, key: str, name: str, **overrides: object) -> None:
        path = self.dirs[key] / name
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(overrides)
        write_json(path, record)
        names = [
            p.name for p in self.dirs[key].iterdir()
            if p.is_file() and p.name != "artifact_inventory.csv"
        ]
        write_artifact_inventory(self.dirs[key], {n: self.dirs[key] / n for n in names})

    def remove_artifact(self, key: str, name: str) -> None:
        (self.dirs[key] / name).unlink()

    def rewrite_v2_1_readout(self, frame: pd.DataFrame) -> None:
        frame.to_csv(self.dirs["v2_1"] / "v2_1_walkforward_readout.csv", index=False)
        names = [
            p.name for p in self.dirs["v2_1"].iterdir()
            if p.is_file() and p.name != "artifact_inventory.csv"
        ]
        write_artifact_inventory(self.dirs["v2_1"], {n: self.dirs["v2_1"] / n for n in names})

    def single_run_dir(self) -> Path:
        run_dirs = [path for path in self.output_dir.iterdir() if path.is_dir()]
        assert len(run_dirs) == 1, f"expected one run folder, got {len(run_dirs)}"
        return run_dirs[0]

    def read_output(self, name: str) -> str:
        return (self.single_run_dir() / name).read_text(encoding="utf-8")


@pytest.fixture()
def stage_dirs(tmp_path: Path) -> Stage05Dirs:
    return Stage05Dirs(tmp_path)


def test_happy_path_writes_four_artifacts_and_report(stage_dirs: Stage05Dirs) -> None:
    result = run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    assert result.run_dir == run_dir
    for name in stage05.REQUIRED_STAGE05_ARTIFACTS:
        assert (run_dir / name).exists(), f"missing required artifact {name}"

    report = json.loads(stage_dirs.read_output("05_thesis_synthesis_report.json"))
    assert report["scope"] == "synthesis_measure_only"
    assert report["new_scoring_events"] == 0
    assert report["holdout_test_contact"] is False
    assert report["no_final_model_selected"] is True
    assert report["clean_test_claim"] is False
    assert report["reads_guarded_walkforward_artifacts"] is True
    assert report["source_stage03_run_id"] == stage_dirs.stage03_run_id
    assert report["source_v2_1_run_id"] == stage_dirs.v2_1_run_id
    assert report["v2_1_decision"] == "met_predeclared_guarded_stability_criteria"
    assert report["kb_wording_guardrails"]
    assert report["deferred_synthesis_items"]


def test_budget_ledger_totals_resolved_from_records(stage_dirs: Stage05Dirs) -> None:
    run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    ledger = pd.read_csv(run_dir / "05_validation_budget_ledger.csv")
    assert list(ledger.columns) == synthesis.VALIDATION_BUDGET_LEDGER_COLUMNS
    by_stage = ledger.set_index("stage_name")["scoring_events"].to_dict()
    # Values come from the frozen records, not the config.
    assert int(by_stage["03_frozen_validation_readout"]) == 2
    assert int(by_stage["04_diagnostics_ablation"]) == 0
    assert int(by_stage["v2_1_guarded_walkforward_readout"]) == 56
    assert int(by_stage["total"]) == 58
    assert not ledger["for_selection"].any()
    # every non-total row tagged with a canonical evidence domain
    non_total = ledger.loc[ledger["stage_name"] != "total"]
    assert set(non_total["evidence_domain"]) <= set(synthesis.EVIDENCE_DOMAINS)


def test_expectation_calibration_resolves_measured_values(stage_dirs: Stage05Dirs) -> None:
    run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    table = pd.read_csv(run_dir / "05_expectation_calibration.csv")
    assert list(table.columns) == synthesis.EXPECTATION_CALIBRATION_COLUMNS
    by_metric = table.set_index("metric_id")
    assert float(by_metric.loc["validation_mean_macro_f1", "value"]) == pytest.approx(0.5170)
    assert float(by_metric.loc["guarded_pooled_delta_binding", "value"]) == pytest.approx(0.006362)
    assert float(by_metric.loc["guarded_pooled_delta_equal_weight", "value"]) == pytest.approx(
        0.005439
    )
    # measured rows trace to <source_key>:<field>; literature rows do not
    assert by_metric.loc["guarded_pooled_delta_binding", "value_source"] == "v2_1:pooled_delta"
    assert by_metric.loc["literature_naive_floor", "value_source"] == "config_literature"
    # accuracy literature vs macro-F1 measured are never conflated (metric_kind)
    assert by_metric.loc["literature_naive_floor", "metric_kind"] == "direction_accuracy"
    assert by_metric.loc["guarded_pooled_delta_binding", "metric_kind"] == "macro_f1_delta"
    assert by_metric.loc["literature_naive_floor", "citation"] == "roadmap_section_12"


def test_no_forbidden_wording_in_any_output(stage_dirs: Stage05Dirs) -> None:
    config = stage_dirs.config()
    forbidden = config["forbidden"]["wording"]
    run_stage(config)
    run_dir = stage_dirs.single_run_dir()
    for name in ("05_claim_boundary_register.csv", "05_expectation_calibration.csv",
                 "05_multiplicity_discount.csv", "05_selective_autopsy.csv",
                 "05_thesis_synthesis_report.json", "05_validation_budget_ledger.csv"):
        text = (run_dir / name).read_text(encoding="utf-8")
        assert not synthesis.find_forbidden_wording(text, forbidden), name


def test_selective_autopsy_augrc_abstention_and_mde(stage_dirs: Stage05Dirs) -> None:
    run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    table = pd.read_csv(run_dir / "05_selective_autopsy.csv")
    assert list(table.columns) == synthesis.SELECTIVE_AUTOPSY_COLUMNS
    # pooled + per-tercile, each with per-seed + seed_mean rows
    assert set(table["activity_tercile"]) == {"all", "low", "mid", "high"}
    assert "seed_mean" in set(table["seed"].astype(str))
    # AUGRC (the wired 0-call-site primitive) present and <= AURC pointwise
    assert table["augrc"].notna().all()
    assert (table["augrc"] <= table["aurc"] + 1e-9).all()
    assert (table["e_aurc"] >= -1e-9).all()
    # MDE joined from the frozen Stage 04 bootstrap; register F1 ordering surfaces:
    # low clears its MDE, high does not (below-random high-activity bars)
    low = table[(table["activity_tercile"].eq("low")) & (table["seed"].eq("seed_mean"))].iloc[0]
    high = table[(table["activity_tercile"].eq("high")) & (table["seed"].eq("seed_mean"))].iloc[0]
    assert bool(low["delta_clears_mde"]) is True
    assert bool(high["delta_clears_mde"]) is False
    assert float(low["mde_vs_dummy"]) == pytest.approx(0.054 - 0.030)
    # report surface: accuracy-basis caveat + per-tercile clears map
    report = json.loads(stage_dirs.read_output("05_thesis_synthesis_report.json"))
    autopsy = report["selective_autopsy"]
    assert autopsy["descriptive_only"] is True
    assert autopsy["selective_metric_basis"] == "accuracy_no_cost_or_return"
    assert autopsy["delta_clears_mde_by_tercile"]["high"] is False
    assert autopsy["pooled_augrc"] is not None


def test_multiplicity_discount_descriptive_pbo_and_min_family_lcb(stage_dirs: Stage05Dirs) -> None:
    run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    table = pd.read_csv(run_dir / "05_multiplicity_discount.csv")
    assert list(table.columns) == synthesis.MULTIPLICITY_DISCOUNT_COLUMNS
    family_rows = table.loc[table["row_kind"].eq("family")]
    summary = table.loc[table["row_kind"].eq("summary")]
    assert len(family_rows) == 4  # one per guarded family (trials)
    assert len(summary) == 1
    assert set(family_rows["n_periods"]) == {7}
    srow = summary.iloc[0]
    assert int(srow["pbo_n_trials"]) == 4 and int(srow["pbo_n_blocks"]) == 7
    assert 0.0 <= float(srow["pbo"]) <= 1.0
    # 7 odd periods -> floor/ceil odd-block CSCV adaptation, labeled (not canonical)
    assert srow["pbo_method"] == "cscv_odd_block_floor_ceil_adaptation"
    assert srow["seed_aggregation"] == "mean_over_seeds"  # seed aggregation is explicit
    # min_family_lcb is the worst family's LCB -> <= every family's own LCB
    assert float(srow["min_family_lcb"]) <= float(family_rows["period_delta_lcb"].min()) + 1e-12
    assert float(srow["max_family_mean"]) == pytest.approx(float(family_rows["mean_delta"].max()))
    # descriptive surface echoed in the report
    report = json.loads(stage_dirs.read_output("05_thesis_synthesis_report.json"))
    md = report["multiplicity_discount"]
    assert md["descriptive_only"] is True
    assert md["pbo_n_trials"] == 4 and md["pbo_n_blocks"] == 7
    assert md["pbo_method"] == "cscv_odd_block_floor_ceil_adaptation"
    assert md["seed_aggregation"] == "mean_over_seeds"
    assert md["min_family_lcb"] == pytest.approx(float(srow["min_family_lcb"]))


def test_multiplicity_discount_fails_closed_on_missing_cell(stage_dirs: Stage05Dirs) -> None:
    # drop a whole (family, period) cell -> incomplete matrix -> fail closed,
    # never silently shrink pbo_n_blocks (the reviewer's P1 risk)
    readout = stage_dirs._v2_1_readout()
    keep = ~(readout["table_row_id"].eq("tcn_frozen_primary") & readout["period_id"].eq("wf_p3"))
    stage_dirs.rewrite_v2_1_readout(readout[keep])
    with pytest.raises(ValueError, match="incomplete family"):
        run_stage(stage_dirs.config())


def test_multiplicity_discount_fails_closed_on_wrong_seed_count(stage_dirs: Stage05Dirs) -> None:
    # drop one seed row for one cell -> cell has 1 seed, not 2 -> fail closed
    readout = stage_dirs._v2_1_readout()
    drop = (
        readout["table_row_id"].eq("lightgbm_family_best")
        & readout["period_id"].eq("wf_p1") & readout["seed"].eq(202)
    )
    stage_dirs.rewrite_v2_1_readout(readout[~drop])
    with pytest.raises(ValueError, match="seed rows"):
        run_stage(stage_dirs.config())


def test_claim_register_tags_domains_and_limitations(stage_dirs: Stage05Dirs) -> None:
    run_stage(stage_dirs.config())
    register = pd.read_csv(stage_dirs.single_run_dir() / "05_claim_boundary_register.csv")
    assert list(register.columns) == synthesis.CLAIM_BOUNDARY_REGISTER_COLUMNS
    assert set(register["evidence_domain"]) <= set(synthesis.EVIDENCE_DOMAINS)
    assert register["is_limitation"].astype(bool).any()
    # supporting run id resolved to a wired id, never blank
    assert register["supporting_run_id"].astype(str).str.len().gt(0).all()


def test_manifest_has_provenance_and_safety_fields(stage_dirs: Stage05Dirs) -> None:
    run_stage(stage_dirs.config())
    manifest = json.loads(stage_dirs.read_output("run_manifest.json"))
    assert manifest["scope"] == "synthesis_measure_only"
    assert manifest["holdout_test_contact"] is False
    assert manifest["official_validation_contact"] == "read_frozen_artifacts_only"
    assert manifest["new_scoring_events"] == 0
    assert manifest["no_final_model_selected"] is True
    for field in ("stage05_synthesis_code_sha256", "config_sha256", "git_commit",
                  "source_stage03_run_id", "source_stage04_run_id", "source_v2_1_run_id"):
        assert field in manifest


def test_blocks_when_v2_1_readout_incomplete(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record("v2_1", "v2_1_decision_record.json", readout_complete=False)
    with pytest.raises(ValueError, match="readout_complete"):
        run_stage(stage_dirs.config())


def test_blocks_when_stage04_has_nonzero_events(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record(
        "stage04", "04_diagnostics_report.json", new_validation_fit_predict_events=3
    )
    with pytest.raises(ValueError, match="new_validation_fit_predict_events"):
        run_stage(stage_dirs.config())


def test_blocks_on_run_id_chain_mismatch(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record(
        "v2_1", "v2_1_decision_record.json", source_stage03_run_id="wrong_id"
    )
    with pytest.raises(ValueError, match="run id chain"):
        run_stage(stage_dirs.config())


def test_blocks_on_missing_required_artifact(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.remove_artifact("v2_1", "v2_1_decision_record.json")
    with pytest.raises(FileNotFoundError, match="v2_1_decision_record.json"):
        run_stage(stage_dirs.config())


def test_blocks_when_v2_1_not_guarded_tier(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record(
        "v2_1", "v2_1_decision_record.json", holdout_contact_tier="clean"
    )
    with pytest.raises(ValueError, match="guarded_historically_contacted"):
        run_stage(stage_dirs.config())


def test_blocks_when_v2_1_claims_clean_test(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record("v2_1", "v2_1_decision_record.json", clean_test_claim=True)
    with pytest.raises(ValueError, match="clean_test_claim"):
        run_stage(stage_dirs.config())


def test_blocks_on_forbidden_wording_in_claim(stage_dirs: Stage05Dirs) -> None:
    config = stage_dirs.config()
    config["claim_boundary_register"]["claims"][0]["statement"] = (
        "This is the final model and it is profitable."
    )
    with pytest.raises(ValueError, match="forbidden wording"):
        run_stage(config)


def test_blocks_on_missing_expectation_field(stage_dirs: Stage05Dirs) -> None:
    config = stage_dirs.config()
    for row in config["expectation_calibration"]["rows"]:
        if row.get("value_source") != "config_literature":
            row["value_field"] = "aggregate.does_not_exist"
            break
    with pytest.raises(KeyError, match="not found"):
        run_stage(config)


def test_blocks_on_unknown_evidence_domain_in_claim(stage_dirs: Stage05Dirs) -> None:
    config = stage_dirs.config()
    config["claim_boundary_register"]["claims"][0]["evidence_domain"] = "made_up_domain"
    with pytest.raises(ValueError, match="evidence_domain"):
        run_stage(config)


def test_blocks_when_v2_1_decision_not_met(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record(
        "v2_1", "v2_1_decision_record.json",
        decision="did_not_meet_predeclared_guarded_stability_criteria",
    )
    with pytest.raises(ValueError, match="decision must be"):
        run_stage(stage_dirs.config())


def test_blocks_when_stage03_decision_not_met(stage_dirs: Stage05Dirs) -> None:
    stage_dirs.override_record(
        "stage03", "03_decision_record.json",
        decision="did_not_meet_predeclared_validation_readout_criteria",
    )
    with pytest.raises(ValueError, match="decision must be"):
        run_stage(stage_dirs.config())


def test_blocks_on_scoring_event_ledger_mismatch(stage_dirs: Stage05Dirs) -> None:
    # count disagrees with the ledger length -> tampered/partial budget
    stage_dirs.override_record("v2_1", "v2_1_decision_record.json", guarded_scoring_events=99)
    with pytest.raises(ValueError, match="scoring_event_ledger length"):
        run_stage(stage_dirs.config())


def test_blocks_on_claim_citing_ungated_artifact(stage_dirs: Stage05Dirs) -> None:
    config = stage_dirs.config()
    # cite a file that is not in required_stage04_artifacts -> not presence/hash-gated
    config["claim_boundary_register"]["claims"][0]["supporting_artifact"] = "not_required.csv"
    with pytest.raises(ValueError, match="entry-gated"):
        run_stage(config)


def test_happy_path_resolves_all_gated_supporting_artifacts(stage_dirs: Stage05Dirs) -> None:
    # every claim's supporting_artifact is among the wired required artifacts
    config = stage_dirs.config()
    inputs = config["inputs"]
    gated = {
        key: set(inputs[f"required_{key}_artifacts"]) for key in ("stage03", "stage04", "v2_1")
    }
    for claim in config["claim_boundary_register"]["claims"]:
        assert claim["supporting_artifact"] in gated[claim["supporting_run_id_key"]], claim["claim_id"]
    run_stage(config)  # and it runs clean end-to-end

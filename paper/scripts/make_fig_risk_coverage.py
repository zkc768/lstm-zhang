"""Fig 3 - accuracy-based risk-coverage curve (model vs oracle, seed mean).

Reference-paper visual style (Arial + black/red/blue marker+line, like that
paper's method-comparison panels). The full per-coverage curve needs the
Drive-only row-level dump (NOT in the repo, by design - route guide section 11):

    My Drive/lst_models/results/03_frozen_validation_readout/
        20260610_133305_716174/03_validation_predictions.csv

Download it locally (do NOT git add it) and pass its absolute path:

    python paper/scripts/make_fig_risk_coverage.py  /abs/path/to/03_validation_predictions.csv

It reuses the pipeline's own metrics so AURC is identical by construction, and
it ASSERTS the per-seed AURC reconciles to 09_validation_selective_summary.csv
(0.47173 / 0.46970) before drawing. Pass --no-reconcile only for a smoke test.

If the dump is unavailable, the script follows FIGURE_BRIEF.md's fallback:
copy the already-rendered Stage 04 risk-coverage PDF/PNG into paper/figures/
and write a provenance note. It deliberately does not invent an SVG curve from
summary scalars.
"""
import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "paper/scripts")
sys.path.insert(0, "src")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams

from style import apply_paper_style, FIG_WIDTH_1COL, LINE_CYCLE, PALETTE
from lst_models import metrics  # pipeline's own selective metrics

apply_paper_style()
rcParams.update({"svg.fonttype": "none"})

DUMP_COLUMNS = [
    "candidate_role", "candidate_id", "model_family", "hpo_profile_id", "seed",
    "sample_id", "ticker", "target_timestamp", "trading_day", "y_true", "p_up",
    "y_pred", "scope",
]
# Reconciliation gate: per-seed AURC must match 09_validation_selective_summary.csv.
EXPECTED = {
    101: {"aurc": 0.47173, "oracle_aurc": 0.14043, "e_aurc": 0.33130},
    202: {"aurc": 0.46970, "oracle_aurc": 0.14056, "e_aurc": 0.32914},
}
TOL = 5e-4
DRIVE_HINT = ("My Drive/lst_models/results/03_frozen_validation_readout/"
              "20260610_133305_716174/03_validation_predictions.csv")
OUT_DIR = Path("paper/figures")
OUT_STEM = OUT_DIR / "fig_risk_coverage"
FALLBACK_PDF = Path(
    "artifacts/ian_email_packet_20260611/figures/fig_04_selective_risk_coverage.pdf"
)
FALLBACK_PNG = Path(
    "artifacts/ian_email_packet_20260611/figures/fig_04_selective_risk_coverage.png"
)
SUMMARY_CSV = Path("artifacts/ian_email_packet_20260611/tables/09_validation_selective_summary.csv")
BAND_MIN_COVERAGE = 0.05
PARTIAL_ONSETS = (0.80, 0.90, 0.95)  # deployment-relevant high-coverage bands


def load_dump(path):
    df = pd.read_csv(path)
    if list(df.columns) != DUMP_COLUMNS:
        raise SystemExit(f"column mismatch:\n expected {DUMP_COLUMNS}\n observed {list(df.columns)}")
    df["confidence"] = metrics.top_label_confidence(df["p_up"].to_numpy(dtype=float))
    df["correct"] = df["y_pred"].astype(int).to_numpy() == df["y_true"].astype(int).to_numpy()
    return df


def selective_order(confidence: np.ndarray, tie_break: np.ndarray) -> np.ndarray:
    tie_rank = np.argsort(np.argsort(tie_break, kind="stable"), kind="stable")
    return np.lexsort((tie_rank, -confidence))


def seed_payload(seed_dump):
    sd = seed_dump.sort_values("sample_id", kind="stable")
    conf = sd["confidence"].to_numpy(dtype=float)
    corr = sd["correct"].to_numpy(dtype=bool)
    sample_id = sd["sample_id"].to_numpy()
    trading_day = sd["trading_day"].to_numpy()
    order = selective_order(conf, sample_id)
    return {
        "confidence": conf,
        "correct": corr,
        "sample_id": sample_id,
        "trading_day": trading_day,
        "order": order,
        "correct_ranked": corr[order],
    }


def per_seed(payload):
    conf = payload["confidence"]
    corr = payload["correct"]
    tie = payload["sample_id"]
    curve = metrics.risk_coverage_curve(conf, corr, tie_break=tie)
    aurc = metrics.aurc_metrics(conf, corr, tie_break=tie)
    aurc["augrc"] = metrics.augrc(conf, corr, tie_break=tie)
    n, n_corr = len(corr), int(corr.sum())
    k = np.arange(1, n + 1)
    oracle_risk = np.maximum(0.0, (k - n_corr) / k)  # all-correct-first ranking
    return curve["coverage"].to_numpy(), curve["selective_risk"].to_numpy(), oracle_risk, aurc


def partial_aurc(coverage: np.ndarray, risk: np.ndarray, onset: float) -> float:
    """Mean selective risk over the coverage band ``[onset, 1]`` -- a descriptive
    restricted-range AURC for the deployment-relevant high-coverage region, NOT a
    chosen operating point. Same mean-of-per-row-risk rule as :func:`aurc_metrics`."""
    return float(risk[coverage >= onset].mean())


def ranked_risk_from_counts(correct_ranked: np.ndarray, counts_ranked: np.ndarray, grid: np.ndarray):
    covered = np.cumsum(counts_ranked, dtype=np.int64)
    observed_step = counts_ranked > 0
    if covered[-1] <= 0 or not np.any(observed_step):
        raise RuntimeError("bootstrap produced no covered rows")
    errors = np.cumsum(counts_ranked * (~correct_ranked), dtype=np.int64)
    coverage = covered[observed_step] / covered[-1]
    risk = errors[observed_step] / covered[observed_step]
    return np.interp(grid, coverage, risk, left=risk[0], right=risk[-1]), float(risk[-1])


def day_cluster_counts(cluster_ids: np.ndarray, rng) -> np.ndarray:
    """Per-row multiplicity from resampling whole trading-day clusters with
    replacement (block bootstrap; mirrors metrics.block_bootstrap_macro_f1_delta).
    Resampling days, not individual rows, respects the within-day correlation of
    bars (e.g. bid-ask bounce, shared regime) that i.i.d. row resampling ignores."""
    _, inv = np.unique(cluster_ids, return_inverse=True)
    n_days = int(inv.max()) + 1
    draws = np.bincount(rng.integers(0, n_days, size=n_days), minlength=n_days)
    return draws[inv]


def _scalar_aurc_from_resample(correct_ranked: np.ndarray, counts_ranked: np.ndarray):
    """Exact AURC / full-coverage risk / oracle AURC on a bootstrap resample,
    using the same definitions as metrics.aurc_metrics (mean of per-prefix
    selective risk over the resampled ranked sequence)."""
    rep_corr = np.repeat(correct_ranked, counts_ranked)
    m = rep_corr.size
    k = np.arange(1, m + 1, dtype=float)
    aurc = float(np.mean(1.0 - np.cumsum(rep_corr) / k))
    n_corr = int(rep_corr.sum())
    fcr = float(1.0 - n_corr / m)
    oracle_corr = np.concatenate([np.ones(n_corr), np.zeros(m - n_corr)])
    oracle_aurc = float(np.mean(1.0 - np.cumsum(oracle_corr) / k))
    return aurc, fcr, oracle_aurc


def bootstrap_bands(payloads, grid: np.ndarray, reps: int, seed: int, cluster_ids: np.ndarray):
    if reps <= 0:
        return None
    rng = np.random.default_rng(seed)
    model_curves = np.empty((reps, len(grid)), dtype=float)
    delta_curves = np.empty_like(model_curves)
    s_aurc = np.empty(reps)
    s_delta = np.empty(reps)
    s_eaurc = np.empty(reps)
    s_gap = np.empty(reps)
    s_rel = np.empty(reps)
    for i in range(reps):
        counts = day_cluster_counts(cluster_ids, rng)
        seed_curves, seed_fcr, seed_aurc, seed_oracle = [], [], [], []
        for payload in payloads:
            counts_ranked = counts[payload["order"]]
            risk, fcr = ranked_risk_from_counts(payload["correct_ranked"], counts_ranked, grid)
            seed_curves.append(risk)
            seed_fcr.append(fcr)
            a_s, _, o_s = _scalar_aurc_from_resample(payload["correct_ranked"], counts_ranked)
            seed_aurc.append(a_s)
            seed_oracle.append(o_s)
        mean_curve = np.mean(seed_curves, axis=0)
        mean_fcr = float(np.mean(seed_fcr))
        model_curves[i] = mean_curve
        delta_curves[i] = (mean_fcr - mean_curve) * 100.0
        a, o, f = float(np.mean(seed_aurc)), float(np.mean(seed_oracle)), mean_fcr
        s_aurc[i] = a
        s_delta[i] = a - f
        s_eaurc[i] = a - o
        s_gap[i] = (f - a) / (f - o)
        s_rel[i] = (a - o) / (f - o)
    pct = lambda x: np.percentile(x, [2.5, 97.5])
    return {
        "model": np.percentile(model_curves, [2.5, 97.5], axis=0),
        "delta": np.percentile(delta_curves, [2.5, 97.5], axis=0),
        "scalars": {
            "aurc": pct(s_aurc), "delta": pct(s_delta), "e_aurc": pct(s_eaurc),
            "gap": pct(s_gap), "rel": pct(s_rel),
        },
    }


def permutation_band(payloads, grid: np.ndarray, reps: int, seed: int):
    if reps <= 0:
        return None
    rng = np.random.default_rng(seed)
    n = len(payloads[0]["correct"])
    k = np.clip(np.ceil(grid * n).astype(int), 1, n)
    curves = np.empty((reps, len(grid)), dtype=float)
    for i in range(reps):
        perm = rng.permutation(n)
        seed_curves = []
        for payload in payloads:
            errors = np.cumsum(~payload["correct"][perm], dtype=np.int64)
            seed_curves.append(errors[k - 1] / k)
        curves[i] = np.mean(seed_curves, axis=0)
    return np.percentile(curves, [2.5, 97.5], axis=0)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_provenance(mode: str, lines: list[str]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    note = OUT_DIR / "fig_risk_coverage_provenance.md"
    body = [
        "# fig_risk_coverage provenance",
        "",
        f"- generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        f"- mode: {mode}",
        "- claim_id: C3.2",
        "- evidence_domain: official_validation",
        "- estimand: accuracy_based_selective_risk_coverage",
        "- forbidden_framing_checked: descriptive only; no cost model; no operating point; not well-calibrated; no statistical significance claim",
        "",
        "## Inputs",
        *lines,
    ]
    note.write_text("\n".join(body) + "\n", encoding="utf-8")
    return note


def fallback_copy() -> None:
    missing = [str(p) for p in (FALLBACK_PDF, FALLBACK_PNG, SUMMARY_CSV) if not p.exists()]
    if missing:
        raise SystemExit("Fallback input missing; cannot fabricate curve:\n  " + "\n  ".join(missing))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FALLBACK_PDF, OUT_STEM.with_suffix(".pdf"))
    shutil.copy2(FALLBACK_PNG, OUT_STEM.with_suffix(".png"))
    note = write_provenance(
        "fallback_reuse_rendered_stage04_curve",
        [
            f"- rendered_pdf: {FALLBACK_PDF} sha256={file_sha256(FALLBACK_PDF)}",
            f"- rendered_png: {FALLBACK_PNG} sha256={file_sha256(FALLBACK_PNG)}",
            f"- scalar_summary: {SUMMARY_CSV} sha256={file_sha256(SUMMARY_CSV)}",
            "- full_curve_dump_missing_in_repo: 03_validation_predictions.csv",
            f"- expected_drive_path: {DRIVE_HINT}",
            "- svg_status: not_generated; full per-coverage source arrays are not in repo",
        ],
    )
    print(f"PDF: {OUT_STEM.with_suffix('.pdf')}")
    print(f"PNG: {OUT_STEM.with_suffix('.png')}")
    print("SVG: not generated (fallback render only; no full curve arrays in repo)")
    print(f"provenance: {note}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", nargs="?", default=os.environ.get("LST_FIG3_DUMP"))
    ap.add_argument(
        "--fallback",
        action="store_true",
        help="copy the rendered Stage 04 risk-coverage PDF/PNG when the full dump is unavailable",
    )
    ap.add_argument("--no-reconcile", action="store_true")
    ap.add_argument("--bootstrap-reps", type=int, default=1000)
    ap.add_argument("--permutation-reps", type=int, default=1000)
    ap.add_argument("--rng-seed", type=int, default=314159)
    a = ap.parse_args()
    if not a.dump:
        if a.fallback:
            fallback_copy()
            return
        raise SystemExit("No dump path given. Download from Drive and pass its absolute path:\n  "
                         + DRIVE_HINT + "\nOr run with --fallback to reuse the rendered Stage 04 curve.")
    if not os.path.exists(a.dump):
        raise SystemExit(f"Not found: {a.dump}\nExpected the Drive file:\n  {DRIVE_HINT}")

    dump = load_dump(a.dump)
    display_grid = np.linspace(BAND_MIN_COVERAGE, 1.0, 256)
    model_cur, oracle_cur, aurcs, fcr, partials = [], [], [], [], []
    payloads = []
    sample_id_reference = None
    for seed, sd in dump.groupby(dump["seed"].astype(int)):
        payload = seed_payload(sd)
        if sample_id_reference is None:
            sample_id_reference = payload["sample_id"]
        elif not np.array_equal(sample_id_reference, payload["sample_id"]):
            raise SystemExit("seed prediction rows do not share the same sample_id order")
        payloads.append(payload)
        cov, risk, orisk, aurc = per_seed(payload)
        aurcs.append((int(seed), aurc))
        model_cur.append(np.interp(display_grid, cov, risk))
        oracle_cur.append(np.interp(display_grid, np.arange(1, len(orisk) + 1) / len(orisk), orisk))
        fcr.append(risk[-1])
        partials.append({c0: partial_aurc(cov, risk, c0) for c0 in PARTIAL_ONSETS})
        exp = EXPECTED.get(int(seed))
        print(f"seed {seed}: AURC={aurc['aurc']:.5f} oracle={aurc['oracle_aurc']:.5f} "
              f"e_AURC={aurc['e_aurc']:.5f} AUGRC={aurc['augrc']:.5f}"
              + (f"  (expected AURC {exp['aurc']})" if exp else ""))
        if exp and not a.no_reconcile:
            for key in ("aurc", "oracle_aurc", "e_aurc"):
                d = abs(aurc[key] - exp[key])
                assert d <= TOL, f"seed {seed} {key} off by {d:.2e} (> {TOL}); wrong dump?"
    if not a.no_reconcile:
        print("reconciliation OK (<= %.0e)" % TOL)

    model = np.mean(model_cur, axis=0)
    oracle = np.mean(oracle_cur, axis=0)
    aurc_mean = np.mean([a["aurc"] for _, a in aurcs])
    eaurc_mean = np.mean([a["e_aurc"] for _, a in aurcs])
    augrc_mean = np.mean([a["augrc"] for _, a in aurcs])
    oracle_mean = np.mean([a["oracle_aurc"] for _, a in aurcs])
    fcr_mean = float(np.mean(fcr))
    rel_aurc = (aurc_mean - oracle_mean) / (fcr_mean - oracle_mean)
    gap_closed = (fcr_mean - aurc_mean) / (fcr_mean - oracle_mean)
    delta_aurc = aurc_mean - fcr_mean
    partial_mean = {c0: float(np.mean([p[c0] for p in partials])) for c0 in PARTIAL_ONSETS}
    partial_delta_pp = {c0: (fcr_mean - partial_mean[c0]) * 100.0 for c0 in PARTIAL_ONSETS}

    cluster_ids = payloads[0]["trading_day"]
    bands = bootstrap_bands(payloads, display_grid, a.bootstrap_reps, a.rng_seed, cluster_ids)
    random_band = permutation_band(payloads, display_grid, a.permutation_reps, a.rng_seed + 1)
    scalar_ci = bands["scalars"] if bands is not None else None

    fig, (ax, ax_delta) = plt.subplots(
        2,
        1,
        figsize=(FIG_WIDTH_1COL, 3.15),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.0], "hspace": 0.04},
    )
    fig.subplots_adjust(left=0.26, right=0.98, bottom=0.15, top=0.73)
    m, o = LINE_CYCLE[0], LINE_CYCLE[2]
    if random_band is not None:
        ax.fill_between(display_grid, random_band[0], random_band[1],
                        color="#B8B8B8", alpha=0.25, lw=0, zorder=0)
    if bands is not None:
        ax.fill_between(display_grid, bands["model"][0], bands["model"][1],
                        color=m["color"], alpha=0.14, lw=0, zorder=1)
    ax.plot(display_grid, model, color=m["color"], marker=m["marker"], markevery=32, ms=3.3,
            lw=1.3, label=f"Prespecified score (AURC = {aurc_mean:.3f})")
    ax.plot(display_grid, oracle, color=o["color"], marker=o["marker"], markevery=32, ms=3.5,
            lw=1.3, ls="--", label=f"Oracle ranking (AURC = {oracle_mean:.3f})")
    ax.axhline(fcr_mean, color="#7A7A7A", lw=0.9, ls=(0, (4, 2)), zorder=1,
               label=f"Random ranking (AURC = {fcr_mean:.3f})")

    delta_pp = (fcr_mean - model) * 100.0
    ax_delta.axhline(0.0, color="#7A7A7A", lw=0.8, ls=(0, (4, 2)), zorder=1)
    if bands is not None:
        ax_delta.fill_between(display_grid, bands["delta"][0], bands["delta"][1],
                              color=m["color"], alpha=0.14, lw=0, zorder=1)
    ax_delta.plot(display_grid, delta_pp, color=m["color"], lw=1.1, marker=m["marker"],
                  markevery=32, ms=2.9)

    for target_ax in (ax, ax_delta):
        for s in ("top", "right"):  # paper line-panels use a full box
            target_ax.spines[s].set_visible(True)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.01, 0.52)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
    delta_low = float(np.nanmin(bands["delta"][0])) if bands is not None else float(np.nanmin(delta_pp))
    delta_high = float(np.nanmax(bands["delta"][1])) if bands is not None else float(np.nanmax(delta_pp))
    delta_pad = max(0.2, (delta_high - delta_low) * 0.10)
    ax_delta.set_ylim(delta_low - delta_pad, delta_high + delta_pad)
    ax_delta.set_yticks([0, 1, 2, 3])
    ax_delta.set_xlabel("Coverage")
    ax.set_ylabel("Selective risk", labelpad=6)
    ax_delta.set_ylabel("Random minus\nprespecified risk (pp)", labelpad=4, fontsize=7)
    ax.text(-0.17, 1.02, "(a)", transform=ax.transAxes,
            fontsize=8, fontweight="bold", ha="left", va="bottom")
    ax_delta.text(0.015, 0.95, "(b)", transform=ax_delta.transAxes,
                  fontsize=8, fontweight="bold", ha="left", va="top",
                  bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4, "alpha": 0.85})
    ax.legend(frameon=False, fontsize=7, loc="lower left",
              bbox_to_anchor=(0.0, 1.02), handlelength=1.45,
              labelspacing=0.28, borderaxespad=0.0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix, kwargs in [
        (".pdf", {}),
        (".svg", {}),
        (".png", {"dpi": 300}),
    ]:
        fig.savefig(OUT_STEM.with_suffix(suffix), **kwargs)
        print(f"{suffix[1:].upper()}: {OUT_STEM.with_suffix(suffix)}")
    source_csv = OUT_DIR / "fig_risk_coverage_source.csv"
    source = pd.DataFrame({
        "coverage": display_grid,
        "n_covered_per_seed": np.rint(display_grid * len(payloads[0]["correct"])).astype(int),
        "selective_risk_score": model,
        "selective_risk_oracle": oracle,
        "expected_random_risk": fcr_mean,
        "selective_risk_diff_random_minus_prespecified_pp": delta_pp,
    })
    if bands is not None:
        source["score_bootstrap_lo"] = bands["model"][0]
        source["score_bootstrap_hi"] = bands["model"][1]
        source["selective_risk_diff_bootstrap_lo_pp"] = bands["delta"][0]
        source["selective_risk_diff_bootstrap_hi_pp"] = bands["delta"][1]
    if random_band is not None:
        source["random_permutation_lo"] = random_band[0]
        source["random_permutation_hi"] = random_band[1]
    source.to_csv(source_csv, index=False)
    print(f"SOURCE: {source_csv}")
    rows_per_seed = dump.groupby(dump["seed"].astype(int)).size().to_dict()
    scalar_csv = OUT_DIR / "fig_risk_coverage_scalar_summary.csv"

    def ci_values(key: str) -> tuple[float, float]:
        if scalar_ci is None:
            return (np.nan, np.nan)
        lo, hi = scalar_ci[key]
        return (float(lo), float(hi))

    scalar_rows = [
        {
            "metric": "seed_mean_aurc_score",
            "value": aurc_mean,
            "ci_lower": ci_values("aurc")[0],
            "ci_upper": ci_values("aurc")[1],
            "unit": "aurc",
            "note": "mean across seeds; lower is better",
        },
        {
            "metric": "expected_random_ranking_risk_and_aurc",
            "value": fcr_mean,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "risk_or_aurc",
            "note": "expected random-ordering selective risk equals full-coverage risk",
        },
        {
            "metric": "seed_mean_oracle_aurc",
            "value": oracle_mean,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "aurc",
            "note": "empirical perfect-ranking oracle, not deployable",
        },
        {
            "metric": "seed_mean_e_aurc",
            "value": eaurc_mean,
            "ci_lower": ci_values("e_aurc")[0],
            "ci_upper": ci_values("e_aurc")[1],
            "unit": "aurc",
            "note": "AURC minus oracle AURC",
        },
        {
            "metric": "delta_aurc_score_minus_random",
            "value": delta_aurc,
            "ci_lower": ci_values("delta")[0],
            "ci_upper": ci_values("delta")[1],
            "unit": "aurc",
            "note": "negative means score improves over expected random ordering",
        },
        {
            "metric": "normalized_excess_aurc",
            "value": rel_aurc,
            "ci_lower": ci_values("rel")[0],
            "ci_upper": ci_values("rel")[1],
            "unit": "fraction",
            "note": "oracle=0, random=1; lower is better",
        },
        {
            "metric": "random_to_oracle_gap_closed",
            "value": gap_closed,
            "ci_lower": ci_values("gap")[0],
            "ci_upper": ci_values("gap")[1],
            "unit": "fraction",
            "note": "fraction of random-to-oracle AURC gap recovered",
        },
        {
            "metric": "augrc_generalized_risk",
            "value": augrc_mean,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "augrc",
            "note": "computed from generalized-risk curve, not the displayed selective-risk axis",
        },
        {
            "metric": "n_rows_per_seed",
            "value": len(payloads[0]["correct"]),
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "rows",
            "note": "official validation rows per seed",
        },
        {
            "metric": "n_rows_at_min_display_coverage",
            "value": int(round(BAND_MIN_COVERAGE * len(payloads[0]["correct"]))),
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "rows",
            "note": f"rows per seed at coverage {BAND_MIN_COVERAGE:.2f}",
        },
        {
            "metric": "bootstrap_reps",
            "value": a.bootstrap_reps,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "count",
            "note": "trading-day cluster block bootstrap",
        },
        {
            "metric": "permutation_reps",
            "value": a.permutation_reps,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "count",
            "note": "random row-ordering null",
        },
    ]
    for c0 in PARTIAL_ONSETS:
        scalar_rows.append({
            "metric": f"partial_selective_risk_diff_random_minus_prespecified_{int(c0 * 100)}_100",
            "value": partial_delta_pp[c0],
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "unit": "percentage_points",
            "note": f"mean random-minus-prespecified difference over coverage {c0:.2f}-1.00",
        })
    pd.DataFrame(scalar_rows).to_csv(scalar_csv, index=False)
    print(f"SCALARS: {scalar_csv}")
    note = write_provenance(
        "regenerated_from_validation_prediction_dump",
        [
            f"- dump: {a.dump} sha256={file_sha256(Path(a.dump))}",
            f"- scalar_summary_gate: {SUMMARY_CSV} sha256={file_sha256(SUMMARY_CSV)}",
            f"- figure_source_csv: {source_csv} sha256={file_sha256(source_csv)}",
            f"- figure_scalar_summary_csv: {scalar_csv} sha256={file_sha256(scalar_csv)}",
            f"- seeds: {sorted(int(seed) for seed in dump['seed'].unique())}",
            f"- rows_per_seed: {dict(sorted((int(k), int(v)) for k, v in rows_per_seed.items()))}",
            "- score_order: descending top-label probability; ties broken by stable sample_id order",
            "- aurc_calculation: full per-row ranked sequence; display markers are downsampled only",
            f"- band_min_coverage: {BAND_MIN_COVERAGE}",
            "- coverage_zero: not included in AURC or displayed bands; selective risk starts at coverage 1/n",
            f"- bootstrap_reps: {a.bootstrap_reps}; trading-day cluster (block) bootstrap, whole days resampled with replacement, shared across seeds; rng_seed={a.rng_seed}",
            f"- bootstrap_unit: trading_day cluster (block); {int(np.unique(cluster_ids).size)} unique days per seed",
            f"- permutation_reps: {a.permutation_reps}; random row ordering null; rng_seed={a.rng_seed + 1}",
            "- random_reference: expected risk under random ranking equals full-coverage risk",
            f"- descriptive_random_to_score_aurc_delta: {delta_aurc:.6f}"
            + (f"  95ci=[{scalar_ci['delta'][0]:.6f}, {scalar_ci['delta'][1]:.6f}]" if scalar_ci is not None else ""),
            f"- rel_aurc_random_to_oracle_scale: {rel_aurc:.6f}"
            + (f"  95ci=[{scalar_ci['rel'][0]:.6f}, {scalar_ci['rel'][1]:.6f}]" if scalar_ci is not None else ""),
            f"- random_to_oracle_gap_closed: {gap_closed:.6f}"
            + (f"  95ci=[{scalar_ci['gap'][0]:.6f}, {scalar_ci['gap'][1]:.6f}]" if scalar_ci is not None else ""),
            "- partial_aurc_score_high_coverage_bands: "
            + ", ".join(f"{int(c0 * 100)}-100%={partial_mean[c0]:.6f}" for c0 in PARTIAL_ONSETS),
            "- partial_delta_vs_random_pp: "
            + ", ".join(f"{int(c0 * 100)}-100%={partial_delta_pp[c0]:.4f}" for c0 in PARTIAL_ONSETS),
            "- full_coverage_errors_per_seed: "
            + ", ".join(f"{s}={int(round(d['full_coverage_risk'] * rows_per_seed[s]))}" for s, d in aurcs),
            f"- n_covered_at_min_band: {int(round(BAND_MIN_COVERAGE * len(payloads[0]['correct'])))} rows at coverage {BAND_MIN_COVERAGE:.2f}",
            f"- augrc_caption_only: {augrc_mean:.6f}; computed from generalized-risk curve, not plotted selective-risk area",
            "- reconciliation_tolerance: 5e-4 unless --no-reconcile",
        ],
    )
    print(f"provenance: {note}")


if __name__ == "__main__":
    main()

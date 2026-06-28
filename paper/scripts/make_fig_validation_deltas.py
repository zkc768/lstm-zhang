"""Fig. 2 - descriptive macro-F1 deltas vs same-row dummy.

Regenerates the paper figure from the official validation per-ticker readout
and the guarded non-independent walk-forward period readout. Horizontal
bars show block-bootstrap confidence intervals, open markers show seed-specific
subgroup estimates, and filled squares mark the arithmetic mean of the two fixed
training seeds. The plot is descriptive. Run from the repository root.
"""

from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams
from matplotlib.lines import Line2D

from style import FIG_WIDTH_1COL, PALETTE, apply_paper_style


apply_paper_style()
rcParams.update({"svg.fonttype": "none"})

CSV_PATH = Path("artifacts/ian_email_packet_20260611/tables/03_official_validation_per_ticker_readout.csv")
GUARDED_PERIOD_CSV = Path("artifacts/05_guarded_base_rates/05_guarded_base_rates.csv")
TICKER_CI_CSV = Path("artifacts/ian_email_packet_20260611/tables/10_validation_robustness_slices.csv")
FIG2_CI_CSV = Path("artifacts/05_fig2_uncertainty/fig2_bootstrap_ci.csv")
DELTA_COL = "delta_macro_f1_vs_stratified_dummy_train_prior"
EXPECTED_SEEDS = (101, 202)
COMMON_XLIM = (-1.5, 3.5)
COMMON_XTICKS = [-1, 0, 1, 2, 3]
DELTA_SYMBOL = "\N{GREEK CAPITAL LETTER DELTA}"
MINUS_SIGN = chr(0x2212)
EN_DASH = chr(0x2013)
OVERALL_LABEL = "Overall\n(row-pooled)"
PERIOD_YEAR_LABELS = {
    "wf_p1": f"2017{EN_DASH}18",
    "wf_p2": f"2018{EN_DASH}19",
    "wf_p3": f"2019{EN_DASH}20",
    "wf_p4": f"2020{EN_DASH}21",
    "wf_p5": f"2021{EN_DASH}22",
    "wf_p6": f"2022{EN_DASH}23",
    "wf_p7": f"2023{EN_DASH}24",
}
REQUIRED_COLUMNS = {
    "candidate_role",
    "candidate_id",
    "seed",
    "ticker",
    "n_rows",
    DELTA_COL,
    "scope",
}
GUARDED_REQUIRED_COLUMNS = {"scope", "slice", "seed", "n_rows", "delta_vs_dummy"}

INK = PALETTE["ink"]
VALIDATION_MEAN = PALETTE["validation"]
GUARDED_MEAN = PALETTE["guarded"]
SEED_101 = PALETTE["bluegrey"]
SEED_202 = PALETTE["accent"]
GRID = "#D7D7D7"
RANGE_LINE = "#777777"


def sha256_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing input CSV: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_validation_deltas() -> tuple[pd.DataFrame, str]:
    sha256 = sha256_file(CSV_PATH)
    df = pd.read_csv(CSV_PATH)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"{CSV_PATH} missing required columns: {sorted(missing)}")
    seeds = tuple(sorted(int(seed) for seed in df["seed"].unique()))
    if seeds != EXPECTED_SEEDS:
        raise ValueError(f"expected seeds {EXPECTED_SEEDS}, got {seeds}")
    if set(df["scope"].unique()) != {"validation_only"}:
        raise ValueError("expected scope=validation_only for all rows")
    if set(df["candidate_role"].unique()) != {"primary"}:
        raise ValueError("expected candidate_role=primary for all rows")
    df = df.copy()
    df["delta_pp"] = df[DELTA_COL] * 100.0
    return df, sha256


def load_guarded_period_deltas() -> tuple[pd.DataFrame, str]:
    sha256 = sha256_file(GUARDED_PERIOD_CSV)
    df = pd.read_csv(GUARDED_PERIOD_CSV)
    missing = GUARDED_REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"{GUARDED_PERIOD_CSV} missing required columns: {sorted(missing)}")
    period = df[df["scope"].eq("period")].copy()
    expected_periods = [f"wf_p{i}" for i in range(1, 8)]
    observed_periods = sorted(period["slice"].astype(str).unique())
    if observed_periods != expected_periods:
        raise ValueError(f"expected guarded periods {expected_periods}, got {observed_periods}")
    seed_rows = period[period["seed"].astype(str).isin([str(s) for s in EXPECTED_SEEDS])]
    seeds = tuple(sorted(int(seed) for seed in seed_rows["seed"].unique()))
    if seeds != EXPECTED_SEEDS:
        raise ValueError(f"expected guarded seeds {EXPECTED_SEEDS}, got {seeds}")
    if "seed_mean" not in set(period["seed"].astype(str)):
        raise ValueError(f"{GUARDED_PERIOD_CSV} missing seed_mean period rows")
    period["delta_pp"] = period["delta_vs_dummy"].astype(float) * 100.0
    return period, sha256


def load_ticker_bootstrap_ci() -> tuple[dict, str]:
    """Per-ticker test-row block-resampling interval on the macro-F1 delta
    (pp), averaged over the two fixed seeds. Source: validation robustness
    slices. These are conditional test-row intervals, not training-seed CIs."""
    sha256 = sha256_file(TICKER_CI_CSV)
    df = pd.read_csv(TICKER_CI_CSV)
    tk = df[df["slice_axis"].astype(str) == "ticker"]
    ci = {}
    for ticker, g in tk.groupby("slice_value"):
        ci[str(ticker)] = (
            float(g["bootstrap_delta_lcb"].astype(float).mean()) * 100.0,
            float(g["bootstrap_delta_ucb"].astype(float).mean()) * 100.0,
        )
    return ci, sha256


def load_fig2_ci_artifact() -> tuple[dict, tuple, tuple, str]:
    """Measure-only re-aggregation artifact: guarded per-period block-resampling
    intervals (keyed by year label) and the two pooled Overall intervals
    (validation, guarded). Reconciled to the frozen point estimates; see
    provenance sidecar."""
    sha256 = sha256_file(FIG2_CI_CSV)
    df = pd.read_csv(FIG2_CI_CSV)
    period_ci = {
        str(r["label"]).replace("-", EN_DASH): (float(r["lcb_pp"]), float(r["ucb_pp"]))
        for _, r in df[(df["panel"] == "B") & (df["scope"] == "period")].iterrows()
    }
    a = df[(df["panel"] == "A") & (df["scope"] != "period")].iloc[0]
    b = df[(df["panel"] == "B") & (df["scope"] != "period")].iloc[0]
    val_overall = (float(a["delta_pp"]), float(a["lcb_pp"]), float(a["ucb_pp"]))
    guarded_overall = (float(b["delta_pp"]), float(b["lcb_pp"]), float(b["ucb_pp"]))
    return period_ci, val_overall, guarded_overall, sha256


def format_row_count(n_rows: float) -> str:
    return f"{float(n_rows) / 1000.0:.1f}k"


def format_pp(value: float, *, signed: bool = False) -> str:
    template = "{:+.1f}" if signed else "{:.1f}"
    return template.format(float(value)).replace("-", MINUS_SIGN)


def format_interval(lcb: float, ucb: float) -> str:
    return f"[{format_pp(lcb)}, {format_pp(ucb)}]"


def draw_panel(
    ax: plt.Axes,
    y_labels: list[str],
    means: pd.Series,
    seed_values: dict[int, pd.Series],
    row_counts: pd.Series,
    *,
    mean_color: str,
    panel_label: str,
    ci: dict | None = None,
) -> None:
    y = np.arange(len(y_labels))
    marker_specs = {
        101: {"marker": "o", "color": SEED_101, "offset": -0.12},
        202: {"marker": "D", "color": SEED_202, "offset": 0.12},
    }
    if ci is not None:
        # Forest plot: per-group/per-domain block-resampling interval.
        for yi, label in zip(y, y_labels):
            if label not in ci:
                continue
            lcb, ucb = ci[label]
            m = float(means[label])
            ax.errorbar(
                m, yi, xerr=[[m - lcb], [ucb - m]], fmt="none",
                ecolor=INK, elinewidth=0.8, capsize=2.4, capthick=0.8, zorder=3,
            )
    # Seed markers show the two fitted-model realizations; intervals are the
    # conditional block-resampling bands, not training-seed uncertainty.
    ax.scatter(
        means.loc[y_labels],
        y,
        s=16,
        marker="s",
        facecolor=mean_color,
        edgecolor=INK,
        linewidth=0.55,
        zorder=5,
    )
    for seed, spec in marker_specs.items():
        values = seed_values.get(seed, pd.Series(dtype=float)).reindex(y_labels)
        mask = values.notna().to_numpy()
        if not mask.any():
            continue
        ax.scatter(
            values[mask],
            y[mask] + spec["offset"],
            s=18,
            marker=spec["marker"],
            facecolor="white",
            edgecolor=spec["color"],
            linewidth=0.8,
            zorder=4,
        )

    if y_labels and y_labels[0] == OVERALL_LABEL:
        ax.axhline(0.5, color=GRID, linewidth=0.7, zorder=1)
    for yi, label in zip(y, y_labels):
        value = float(means[label])
        if ci is not None:
            lcb, ucb = ci[label]
            txt = f"{format_pp(value, signed=True)} {format_interval(lcb, ucb)}"
        else:
            txt = f"{format_pp(value, signed=True)}; {format_row_count(row_counts[label])}"
        ax.text(
            1.018,
            yi,
            txt,
            transform=ax.get_yaxis_transform(),
            va="center",
            ha="left",
            fontsize=6.0,
            color=INK,
            clip_on=False,
        )

    ax.axvline(0, color=INK, linewidth=0.85, linestyle=(0, (3, 2)), zorder=1)
    ax.text(
        0.0,
        1.08,
        panel_label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.0,
        fontweight="bold",
        linespacing=1.0,
        clip_on=False,
    )
    header = (
        "Estimate, pp\n[95% CI]" if ci is not None
        else f"{DELTA_SYMBOL} (pp); rows"
    )
    ax.text(
        1.018,
        1.02,
        header,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.8,
        color="#666666",
        clip_on=False,
    )

    ax.set_yticks(y)
    ax.set_yticklabels(y_labels)
    ax.invert_yaxis()
    ax.set_xlim(*COMMON_XLIM)
    ax.set_xticks(COMMON_XTICKS)
    ax.set_ylim(len(y_labels) - 0.5, -0.8)
    ax.xaxis.grid(True, color=GRID, linewidth=0.5, alpha=0.75)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=2.3, width=0.6)


def build_figure(validation_df: pd.DataFrame, guarded_df: pd.DataFrame) -> plt.Figure:
    ticker_ci, _ = load_ticker_bootstrap_ci()
    period_ci, val_ov, guard_ov, _ = load_fig2_ci_artifact()
    means = validation_df.groupby("ticker", sort=False)["delta_pp"].mean().sort_values(ascending=False)
    validation_order = list(means.index)
    validation_rows = validation_df.groupby("ticker", sort=False)["n_rows"].first().loc[validation_order]
    validation_seed_values = {
        seed: validation_df[validation_df["seed"] == seed].set_index("ticker")["delta_pp"]
        for seed in EXPECTED_SEEDS
    }
    validation_labels = [OVERALL_LABEL] + validation_order
    validation_means = pd.concat([pd.Series({OVERALL_LABEL: val_ov[0]}), means])
    validation_rows = pd.concat([pd.Series({OVERALL_LABEL: np.nan}), validation_rows])
    validation_ci = {OVERALL_LABEL: (val_ov[1], val_ov[2]), **ticker_ci}

    guarded_order = [f"wf_p{i}" for i in range(1, 8)]
    guarded_period_labels = [PERIOD_YEAR_LABELS[period] for period in guarded_order]
    guarded_seed_mean = guarded_df[guarded_df["seed"].astype(str).eq("seed_mean")]
    guarded_means = guarded_seed_mean.set_index("slice").loc[guarded_order, "delta_pp"]
    guarded_rows = guarded_seed_mean.set_index("slice").loc[guarded_order, "n_rows"]
    guarded_means.index = guarded_period_labels
    guarded_rows.index = guarded_period_labels
    guarded_seed_values = {}
    for seed in EXPECTED_SEEDS:
        values = (
            guarded_df[guarded_df["seed"].astype(str).eq(str(seed))]
            .set_index("slice")
            .loc[guarded_order, "delta_pp"]
        )
        values.index = guarded_period_labels
        guarded_seed_values[seed] = values
    guarded_labels = [OVERALL_LABEL] + guarded_period_labels
    guarded_means = pd.concat([pd.Series({OVERALL_LABEL: guard_ov[0]}), guarded_means])
    guarded_rows = pd.concat([pd.Series({OVERALL_LABEL: np.nan}), guarded_rows])
    guarded_ci = {OVERALL_LABEL: (guard_ov[1], guard_ov[2]), **period_ci}

    fig, axes = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(FIG_WIDTH_1COL, 4.55),
        sharex=True,
        gridspec_kw={"height_ratios": [1.08, 1.36]},
    )
    fig.subplots_adjust(left=0.20, right=0.76, top=0.85, bottom=0.115, hspace=0.31)

    draw_panel(
        axes[0],
        validation_labels,
        validation_means,
        validation_seed_values,
        validation_rows,
        mean_color=VALIDATION_MEAN,
        panel_label="A",
        ci=validation_ci,
    )
    axes[0].tick_params(labelbottom=False)

    draw_panel(
        axes[1],
        guarded_labels,
        guarded_means,
        guarded_seed_values,
        guarded_rows,
        mean_color=GUARDED_MEAN,
        panel_label="B",
        ci=guarded_ci,
    )
    axes[1].set_xlabel("Difference in macro-F1 (model \u2212 stratified-random baseline), pp")

    ci_handle = axes[0].errorbar(
        [np.nan],
        [np.nan],
        xerr=[[0.2], [0.2]],
        fmt="none",
        ecolor=INK,
        elinewidth=0.9,
        capsize=2.4,
        capthick=0.9,
        label="95% block-bootstrap CI",
    )
    # Matplotlib fills multi-column legends by column; this order renders rows as:
    # Validation mean | Guarded mean | CI, then Seed 101 | Seed 202.
    legend_handles = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=VALIDATION_MEAN,
               markeredgecolor=INK, markersize=3.8, label="Validation mean"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="white",
               markeredgecolor=SEED_101, markersize=3.8, label="Seed 101"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=GUARDED_MEAN,
               markeredgecolor=INK, markersize=3.8, label="Guarded mean"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="white",
               markeredgecolor=SEED_202, markersize=3.8, label="Seed 202"),
        ci_handle,
    ]
    fig.legend(
        handles=legend_handles,
        ncol=3,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        fontsize=5.25,
        columnspacing=0.8,
        handlelength=1.2,
        handletextpad=0.35,
        borderaxespad=0.0,
    )
    return fig


def main() -> None:
    validation_df, validation_sha256 = load_validation_deltas()
    guarded_df, guarded_sha256 = load_guarded_period_deltas()
    fig = build_figure(validation_df, guarded_df)
    out_dir = Path("paper/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / "fig_validation_deltas"
    for suffix, kwargs in [
        (".pdf", {}),
        (".svg", {}),
        (".png", {"dpi": 300}),
    ]:
        out_path = stem.with_suffix(suffix)
        fig.savefig(out_path, **kwargs)
        print(out_path)
    print(f"validation_input_sha256={validation_sha256}")
    print(f"guarded_input_sha256={guarded_sha256}")


if __name__ == "__main__":
    main()

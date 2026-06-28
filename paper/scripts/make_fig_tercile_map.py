"""Fig. 4 - activity-tercile condition map (paired diverging bars).

Regenerates the paper figure from the bound Stage 05 and guarded activity
artifacts only. Bars are seed-mean macro-F1 differences vs the same-row
stratified dummy baseline, expressed in percentage points. Open markers show
the two seed-specific deltas. Faded grey sleeves around bar endpoints show
per-trading-day block MDE half-widths from the audited Fig. 4 uncertainty table;
they are descriptive MDE bands, not confidence intervals. Run from the
repository root.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from style import FIG_WIDTH_1COL, PALETTE, apply_paper_style

apply_paper_style()
rcParams.update({"svg.fonttype": "none"})

VALIDATION_CSV = Path(
    "artifacts/05_thesis_synthesis/20260619_090454_562658/05_selective_autopsy.csv"
)
GUARDED_CSV = Path("artifacts/05_guarded_activity_tercile/05_guarded_activity_tercile.csv")
TERCILE_MDE_CSV = Path("artifacts/05_fig2_uncertainty/fig4_tercile_ci.csv")

TERCILES = ("low", "mid", "high")
TERCILE_LABELS = ("Low\nactivity", "Medium\nactivity", "High\nactivity")
SEEDS = ("101", "202")
SEED_MARKERS = {"101": "o", "202": "D"}
SEED_X_OFFSETS = {"101": -0.045, "202": 0.045}
SOURCE_REQUIRED_COLUMNS = {"activity_tercile", "seed", "delta_vs_dummy"}
MDE_REQUIRED_COLUMNS = {"domain", "tercile", "delta_pp", "mde_pp"}
INK = PALETTE["ink"]

DOMAIN_SPECS = {
    "validation": {
        "label": "Validation",
        "source_label": "validation",
        "path": VALIDATION_CSV,
        "color": PALETTE["validation"],
        "hatch": "",
    },
    "guarded": {
        "label": "Guarded WF",
        "source_label": "guarded_historically_contacted",
        "path": GUARDED_CSV,
        "color": PALETTE["guarded"],
        "hatch": "//",
    },
}


def sha256_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing input artifact: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source_deltas_pp(path: Path, domain: str) -> tuple[pd.Series, pd.DataFrame]:
    df = pd.read_csv(path)
    missing = SOURCE_REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"{path} missing required columns: {sorted(missing)}")
    df = df[df["activity_tercile"].isin(TERCILES)].copy()
    df["seed_str"] = df["seed"].astype(str)

    seed_mean = df[df["seed_str"] == "seed_mean"].copy()
    missing_terciles = set(TERCILES).difference(seed_mean["activity_tercile"].astype(str))
    if missing_terciles:
        raise ValueError(f"{path} missing seed_mean terciles: {sorted(missing_terciles)}")

    values = (
        seed_mean.set_index("activity_tercile")
        .loc[list(TERCILES), "delta_vs_dummy"]
        .astype(float)
        * 100.0
    )

    seed_rows: list[pd.DataFrame] = []
    for seed in SEEDS:
        seed_df = df[df["seed_str"] == seed].copy()
        missing_seed_terciles = set(TERCILES).difference(seed_df["activity_tercile"].astype(str))
        if missing_seed_terciles:
            raise ValueError(
                f"{path} missing seed {seed} terciles: {sorted(missing_seed_terciles)}"
            )
        seed_values = (
            seed_df.set_index("activity_tercile")
            .loc[list(TERCILES), "delta_vs_dummy"]
            .astype(float)
            * 100.0
        )
        seed_rows.append(
            pd.DataFrame(
                {
                    "tercile": list(TERCILES),
                    "seed": seed,
                    "delta_pp": seed_values.to_numpy(),
                }
            )
        )

    print(f"{domain}: {dict(zip(TERCILES, np.round(values.to_numpy(), 3)))}")
    print(f"{domain} input: {path} sha256={sha256_file(path)}")
    return values, pd.concat(seed_rows, ignore_index=True)


def load_mde_frame(source_values: dict[str, pd.Series]) -> pd.DataFrame:
    df = pd.read_csv(TERCILE_MDE_CSV)
    missing = MDE_REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"{TERCILE_MDE_CSV} missing required columns: {sorted(missing)}")

    expected_pairs = {(domain, tercile) for domain in DOMAIN_SPECS for tercile in TERCILES}
    found_pairs = set(zip(df["domain"].astype(str), df["tercile"].astype(str)))
    missing_pairs = expected_pairs.difference(found_pairs)
    if missing_pairs:
        raise ValueError(f"{TERCILE_MDE_CSV} missing domain/tercile rows: {sorted(missing_pairs)}")

    rows: list[dict[str, float | str]] = []
    for domain in DOMAIN_SPECS:
        for tercile in TERCILES:
            row = df[(df["domain"] == domain) & (df["tercile"] == tercile)].iloc[0]
            delta_pp = float(row["delta_pp"])
            source_delta_pp = float(source_values[domain].loc[tercile])
            if not np.isclose(delta_pp, source_delta_pp, atol=0.001):
                raise ValueError(
                    f"{TERCILE_MDE_CSV} delta mismatch for {domain}/{tercile}: "
                    f"{delta_pp:.4f} vs source {source_delta_pp:.4f}"
                )
            mde_pp = float(row["mde_pp"])
            if not np.isfinite(mde_pp) or mde_pp <= 0:
                raise ValueError(f"{TERCILE_MDE_CSV} invalid mde_pp for {domain}/{tercile}")
            rows.append(
                {
                    "domain": domain,
                    "tercile": tercile,
                    "delta_pp": delta_pp,
                    "mde_pp": mde_pp,
                }
            )

    print(f"fig4 MDE input: {TERCILE_MDE_CSV} sha256={sha256_file(TERCILE_MDE_CSV)}")
    return pd.DataFrame(rows)


def main() -> None:
    source_values: dict[str, pd.Series] = {}
    seed_points: list[pd.DataFrame] = []
    for domain, spec in DOMAIN_SPECS.items():
        domain_values, domain_seed_points = load_source_deltas_pp(
            spec["path"], spec["source_label"]
        )
        source_values[domain] = domain_values
        domain_seed_points["domain"] = domain
        seed_points.append(domain_seed_points)
    seed_points_df = pd.concat(seed_points, ignore_index=True)
    plot_df = load_mde_frame(source_values)

    grey = PALETTE["grey"]
    ymin, ymax = -3.05, 6.55
    dodge = 0.16
    bar_width = 0.26
    sleeve_width = 0.34  # wider than the bar, so MDE remains visible.

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_1COL, 2.18))
    x = np.arange(len(TERCILES), dtype=float)

    # Region below the same-row dummy floor (drawn first, beneath all data).
    ax.axhspan(ymin, 0.0, facecolor=grey, alpha=0.13, linewidth=0, zorder=0)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=grey, linewidth=0.42, alpha=0.38, zorder=0.4)
    ax.grid(axis="x", visible=False)

    for domain, spec in DOMAIN_SPECS.items():
        domain_df = plot_df[plot_df["domain"] == domain].set_index("tercile").loc[list(TERCILES)]
        deltas = domain_df["delta_pp"].to_numpy()
        mdes = domain_df["mde_pp"].to_numpy()
        xs = x + (-dodge if domain == "validation" else dodge)

        # Descriptive MDE sleeve: a faded grey box hugging each bar endpoint.
        # This avoids capped whiskers, keeping Fig. 4 visually distinct from
        # Fig. 2's forest-plot confidence intervals.
        for xi, yi, ei in zip(xs, deltas, mdes):
            ax.add_patch(
                Rectangle(
                    (xi - sleeve_width / 2.0, yi - ei),
                    sleeve_width,
                    2 * ei,
                    facecolor=grey,
                    edgecolor="none",
                    alpha=0.6,
                    zorder=3.4,
                )
            )
        ax.bar(
            xs,
            deltas,
            width=bar_width,
            color=spec["color"],
            edgecolor=INK,
            linewidth=0.7,
            hatch=spec["hatch"],
            zorder=5,
        )
        domain_seed_points = seed_points_df[seed_points_df["domain"] == domain]
        for seed in SEEDS:
            seed_values = (
                domain_seed_points[domain_seed_points["seed"] == seed]
                .set_index("tercile")
                .loc[list(TERCILES), "delta_pp"]
                .to_numpy()
            )
            ax.scatter(
                xs + SEED_X_OFFSETS[seed],
                seed_values,
                marker=SEED_MARKERS[seed],
                s=15,
                facecolor="white",
                edgecolor=INK,
                linewidth=0.75,
                zorder=6.5,
            )

    # Bold solid zero rule reads as a threshold (not a thin dashed gridline).
    ax.axhline(0.0, color=INK, linewidth=1.2, zorder=2.5)

    ax.set_xlim(-0.52, 2.52)
    ax.set_ylim(ymin, ymax)
    ax.set_xticks(x)
    ax.set_xticklabels(TERCILE_LABELS)
    ax.set_xlabel("Activity tercile (eligible-row count)")
    ax.tick_params(axis="x", length=0)
    ax.set_yticks([-2, 0, 2, 4, 6])
    ax.set_ylabel(r"$\Delta$ Macro-F1" "\n" "vs. stratified baseline (pp)", labelpad=2.0)

    legend_handles = [
        Patch(
            facecolor=DOMAIN_SPECS["validation"]["color"],
            edgecolor=INK,
            linewidth=0.7,
            label="Validation",
        ),
        Patch(
            facecolor=DOMAIN_SPECS["guarded"]["color"],
            edgecolor=INK,
            linewidth=0.7,
            hatch=DOMAIN_SPECS["guarded"]["hatch"],
            label="Guarded WF",
        ),
        Line2D(
            [0],
            [0],
            marker=SEED_MARKERS["101"],
            color="none",
            markerfacecolor="white",
            markeredgecolor=INK,
            markeredgewidth=0.75,
            markersize=4,
            label="Seed 101",
        ),
        Line2D(
            [0],
            [0],
            marker=SEED_MARKERS["202"],
            color="none",
            markerfacecolor="white",
            markeredgecolor=INK,
            markeredgewidth=0.75,
            markersize=4,
            label="Seed 202",
        ),
        Patch(facecolor=grey, alpha=0.6, edgecolor="none", label="Day-block MDE band"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        bbox_to_anchor=(1.0, 1.0),
        ncol=1,
        handlelength=1.1,
        handletextpad=0.4,
        labelspacing=0.32,
        borderaxespad=0.3,
        fontsize=5.1,
        frameon=False,
    )

    fig.subplots_adjust(left=0.175, right=0.985, bottom=0.205, top=0.965)

    out_dir = Path("paper/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / "fig_tercile_map"
    for suffix, kwargs in (
        (".pdf", {"bbox_inches": "tight", "pad_inches": 0.02}),
        (".svg", {"bbox_inches": "tight", "pad_inches": 0.02}),
        (".png", {"dpi": 600, "bbox_inches": "tight", "pad_inches": 0.02}),
    ):
        output = stem.with_suffix(suffix)
        fig.savefig(output, **kwargs)
        print(output)


if __name__ == "__main__":
    main()

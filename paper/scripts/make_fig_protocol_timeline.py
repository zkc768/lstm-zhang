"""Fig. 1 - evaluation protocol timeline (minimal, single-column).

A visual-first timeline: three contiguous eras to real-date scale -- Training,
prespecified validation, and the guarded walk-forward era (seven 12-month
periods).
The colored band carries phase/action labels; the lower axis carries the date
scale and split-boundary years. The post-2017 span is bracketed above to state
that it was held out throughout validation. Secondary-use,
non-independence, and future-blind limitations live mainly in the caption.
X positions use matplotlib dates. Run from the repository root.
"""

import datetime as dt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.patches import Rectangle

from style import FIG_WIDTH_1COL, apply_paper_style

apply_paper_style()
rcParams.update(
    {
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    }
)

INK = "#333333"
FRAME = "#3F4650"
TRAIN = "#3A6595"
VAL = "#D28D33"
WALK = "#BBC2CA"      # neutral grey: guarded era, not a "pass"
WALK_EDGE = "#DDE2E7"
FRAME_LW = 0.62
INNER_LW = 0.54
BRACKET_LW = 0.50
ARROW_LW = 0.58
AXIS_LW = 0.62
TICK_LW = 0.78
GUIDE_LW = 0.50
ANNUAL_LW = 0.50


def D(year, month, day):
    return mdates.date2num(dt.date(year, month, day))


T0 = D(1998, 1, 2)
T_FREEZE = D(2013, 9, 16)
T_HOLD = D(2017, 1, 25)
WF_EDGES = [D(2017 + k, 1, 25) for k in range(8)]
WF_END = WF_EDGES[-1]

E_Y, E_H = 1.02, 0.52
PRIMARY_Y = E_Y + E_H * 0.60
SECONDARY_Y = E_Y + E_H * 0.34
SECONDARY_LINE_GAP = E_H * 0.070


def main():
    fig = plt.figure(figsize=(FIG_WIDTH_1COL, 1.62))
    ax = fig.add_axes([0.006, 0.006, 0.988, 0.988])
    ax.set_axis_off()

    ax.add_patch(Rectangle((T0, E_Y), T_FREEZE - T0, E_H, fc=TRAIN, ec="none"))
    ax.add_patch(Rectangle((T_FREEZE, E_Y), T_HOLD - T_FREEZE, E_H, fc=VAL, ec="none"))
    for k in range(7):
        ax.add_patch(
            Rectangle(
                (WF_EDGES[k], E_Y),
                WF_EDGES[k + 1] - WF_EDGES[k],
                E_H,
                fc=WALK,
                ec="none",
            )
        )
    annual_line_segments = [
        (E_Y, E_Y + E_H * 0.23),
        (E_Y + E_H * 0.77, E_Y + E_H),
    ]
    for xb in WF_EDGES[1:-1]:
        for y0, y1 in annual_line_segments:
            ax.plot([xb, xb], [y0, y1], color=WALK_EDGE, lw=ANNUAL_LW)
    ax.add_patch(Rectangle((T0, E_Y), WF_END - T0, E_H, fc="none", ec=FRAME, lw=FRAME_LW))
    ax.plot([T_FREEZE, T_FREEZE], [E_Y, E_Y + E_H], color=FRAME, lw=INNER_LW)
    ax.plot([T_HOLD, T_HOLD], [E_Y, E_Y + E_H], color=FRAME, lw=FRAME_LW)

    x_train = (T0 + T_FREEZE) / 2
    ax.text(x_train, PRIMARY_Y, "Training", ha="center", va="center",
            fontsize=7.5, fontweight="bold", color="white")
    ax.text(x_train, SECONDARY_Y, "Model fitting and tuning using training data only",
            ha="center", va="center", fontsize=5.3, color="white")

    x_val = (T_FREEZE + T_HOLD) / 2
    val_center = PRIMARY_Y - E_H * 0.010
    val_gap = E_H * 0.140
    ax.text(x_val, val_center + val_gap / 2, "Prespecified", ha="center",
            va="center", fontsize=4.45, fontweight="bold", color=INK)
    ax.text(x_val, val_center - val_gap / 2, "validation", ha="center",
            va="center", fontsize=5.15, fontweight="bold", color=INK)

    x_guarded = (T_HOLD + WF_END) / 2
    ax.text(
        x_guarded,
        PRIMARY_Y,
        "Guarded\nwalk-forward",
        ha="center",
        va="center",
        fontsize=6.0,
        fontweight="bold",
        color=INK,
        linespacing=0.9,
    )
    ax.text(x_guarded, SECONDARY_Y, "7 annual robustness\nchecks", ha="center",
            va="center", fontsize=5.2, color=INK, linespacing=0.9)

    yw = E_Y + E_H + 0.09
    ax.plot([T_HOLD, WF_END], [yw, yw], color=FRAME, lw=BRACKET_LW)
    for xb in (T_HOLD, WF_END):
        ax.plot([xb, xb], [yw - 0.025, yw + 0.025], color=FRAME, lw=BRACKET_LW)
    ax.text(
        (T_HOLD + WF_END) / 2,
        yw + 0.035,
        "Held out throughout\nvalidation",
        ha="center",
        va="bottom",
        fontsize=5.0,
        color=INK,
        linespacing=1.0,
    )
    ax.annotate(
        "Model specification and analysis protocol locked\nbefore any validation outcome was inspected",
        xy=(T_FREEZE, E_Y + E_H),
        xytext=(T0 + 600, E_Y + E_H + 0.33),
        ha="left",
        va="bottom",
        fontsize=5.15,
        color=INK,
        linespacing=1.15,
        arrowprops=dict(
            arrowstyle="-|>",
            color=INK,
            lw=ARROW_LW,
            mutation_scale=8,
            connectionstyle="arc3,rad=-0.2",
        ),
    )

    by = E_Y - 0.24
    ax.plot([T0, WF_END], [by, by], color=INK, lw=AXIS_LW)
    boundary_ticks = [
        (T0, "1998"),
        (T_FREEZE, "2013"),
        (T_HOLD, "2017"),
        (WF_END, "2024"),
    ]
    for xb, label in boundary_ticks:
        ax.plot([xb, xb], [by, by + 0.078], color=FRAME, lw=TICK_LW)
        ax.text(xb, by - 0.05, label, ha="center", va="top", fontsize=6.2, color=INK)
    for xb in (T_FREEZE, T_HOLD):
        ax.plot([xb, xb], [by + 0.078, E_Y], color=FRAME, lw=GUIDE_LW, ls=(0, (2, 2)))

    ax.set_xlim(T0 - 500, WF_END + 500)
    ax.set_ylim(E_Y - 0.46, E_Y + E_H + 0.54)

    out_dir = Path("paper/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / "fig_protocol_timeline"
    for suffix, kwargs in [(".pdf", {}), (".svg", {}), (".png", {"dpi": 300})]:
        fig.savefig(stem.with_suffix(suffix), **kwargs)
        print(stem.with_suffix(suffix))


if __name__ == "__main__":
    main()

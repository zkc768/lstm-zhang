"""Shared matplotlib style for all paper figures (Doc A contract section 4).

Every figure script imports from this module and saves vector PDF into
paper/figures/. Figures are regenerated from artifacts/ data only; no
hand-edited or notebook-copied images.

Visual style mimics the reference paper (iodinated-THM ML paper, on file):
Arial sans-serif labels in ink grey, a soft pastel earth-tone palette for
categorical / bar / importance figures, and a black/red/blue marker+line
palette for method-comparison curves. Palette hexes were sampled directly
from that paper's embedded figures.
"""

from matplotlib import rcParams

FIG_WIDTH_1COL = 3.33  # inch, sigconf \columnwidth
FIG_WIDTH_2COL = 7.00  # inch, sigconf \textwidth

# Pastel earth-tone palette sampled from the reference paper's figures.
PAPER_PASTEL = ["#6D8989", "#AB8C96", "#E5C4DD", "#A5C1C0", "#848CAA", "#F1D9A8"]

# Semantic aliases, kept stable so figures stay comparable across the paper.
PALETTE = {
    "validation": "#6D8989",  # teal
    "guarded": "#AB8C96",     # mauve
    "accent": "#4B314C",      # dark plum (schematic frozen marker)
    "bluegrey": "#848CAA",
    "sage": "#A5C1C0",
    "pink": "#E5C4DD",
    "tan": "#F1D9A8",
    "ink": "#333333",         # axis lines, tick labels, text
    "grey": "#B6B2BB",        # closed/holdout, baseline ink
}

# Method-comparison curves (reference paper's line-plot style): black / red /
# blue, each with its own marker. Use for risk-coverage and any model-vs-model.
LINE_CYCLE = [
    {"color": "#333333", "marker": "s"},  # primary
    {"color": "#C0392B", "marker": "o"},  # red
    {"color": "#2E5A9C", "marker": "^"},  # blue
]

PAPER_RC = {
    "figure.dpi": 300,
    "savefig.format": "pdf",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#333333",
    "text.color": "#333333",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.3,
    "pdf.fonttype": 42,  # embed TrueType so text stays selectable
}

# Backward-compatible alias: older scripts referenced OKABE_ITO[model]; map the
# model keys onto the paper palette so existing imports keep working.
OKABE_ITO = {
    "tcn": PALETTE["validation"],
    "dlinear": PALETTE["guarded"],
    "lightgbm": PALETTE["sage"],
    "mlp": PALETTE["pink"],
    "dummy_stratified": PALETTE["grey"],
    "majority": PALETTE["bluegrey"],
}


def apply_paper_style() -> None:
    """Apply the shared rcParams. Call once at the top of every figure script."""
    rcParams.update(PAPER_RC)

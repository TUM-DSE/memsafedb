# workaround to select Agg as backend consistenly
import matplotlib as mpl  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.ticker as ticker
from matplotlib.colors import rgb_to_hsv, hsv_to_rgb, to_rgb
import seaborn as sns  # type: ignore
from functools import reduce
import statistics
from scipy.stats import gmean
from natsort import natsorted, ns
import pandas as pd
import os
import numpy as np

dir_path = os.path.dirname(os.path.realpath(__file__))
result_dir = os.path.join(dir_path, "../results")

# 3.3 inch for single column, 7 inch for double column
figwidth_third = 7/3
figwidth_half = 3.3
figwidth_full = 7
fig_height = 1.2
FONTSIZE=7

# Derived font sizes for consistency
FONTSIZE_AXIS_LABEL = FONTSIZE
FONTSIZE_TICK_LABEL = FONTSIZE
FONTSIZE_LEGEND = FONTSIZE - 2
FONTSIZE_ANNOTATION = FONTSIZE - 3

def format_big_numbers(x, pos):
    if x >= 1e9:
        return f'{x / 1e9:.1f}B'
    elif x >= 1e6:
        return f'{x / 1e6:.1f}M'
    elif x >= 1e3:
        return f'{x / 1e3:.1f}K'
    else:
        return f'{x:.0f}'

palette = sns.color_palette("pastel")
#sns.set(rc={"figure.figsize": (5, 5)})
sns.set_style("whitegrid")
sns.set_style("ticks", {"xtick.major.size": FONTSIZE, "ytick.major.size": FONTSIZE})
sns.set_context("paper", rc={"font.size": FONTSIZE, "axes.titlesize": FONTSIZE, "axes.labelsize": FONTSIZE})

mpl.use("Agg")
mpl.rcParams.update({
       "text.usetex": True,
       "font.family": "serif",
       "font.serif": ["Libertine"],
       "text.latex.preamble": r"""
   \usepackage[tt=false, type1=true]{libertine}
   \usepackage[libertine]{newtxmath}
   """
})

def darken(color):
    hue, saturation, value = rgb_to_hsv(to_rgb(color))
    return hsv_to_rgb((hue, saturation, value * 0.9))

def lighten(color, factor=0.5):
    from matplotlib.colors import to_rgb, to_hex
    rgb = to_rgb(color)
    return to_hex([c + (1.0 - c) * factor for c in rgb])

hatch_def = [
    '',
    "//",
    'xx',
    '*',
    "--",
    "++",
    "||",
    "..",
    "oo",
    "\\\\",
]

marker_def = [
    "o",
    "x",
    "D",
    "*",
    "+",
]

BASELINE_MTE_COLOR = lighten('#1F78B4', 0) # slightly lighter Dark blue
MTE_COLOR = lighten('#1F78B4', 0.2)           # Light blue mathematically derived
ASAN_COLOR = '#984EA3'                        # Purple
BASELINE_CHERI_COLOR = lighten('#FF7F00', 0) # slightly lighter Dark Orange
CHERI_COLOR = lighten('#FF7F00', 0.2)           # Light Orange mathematically derived
MTE_GREEN_1 = lighten('#33A02C', 0.2)
MTE_GREEN_2 = '#33A02C'

BASELINE_MTE_HATCH = ''
MTE_HATCH = '///'
ASAN_HATCH = 'xx'
BASELINE_CHERI_HATCH = ''
CHERI_HATCH = '\\\\\\\\'

MTE_PALETTE = [
    BASELINE_MTE_COLOR,
    MTE_COLOR,
    MTE_GREEN_1,
    MTE_GREEN_2,
    ASAN_COLOR,
]

CHERI_PALETTE = [
    BASELINE_CHERI_COLOR,
    CHERI_COLOR,
]

def _cycle(values, n):
    if n <= 0:
        return []
    if not values:
        return [None] * n
    out = []
    idx = 0
    while len(out) < n:
        out.append(values[idx % len(values)])
        idx += 1
    return out

def get_palette(scheme, n):
    if scheme == "mte":
        base = MTE_PALETTE
    elif scheme == "non-mte":
        base = CHERI_PALETTE
    else:
        base = list(palette)
    return _cycle(base, n)

def get_hatches(n):
    return _cycle(hatch_def, n)

def get_markers(n):
    return _cycle(marker_def, n)


style_map = {
        'release-static': {'color': BASELINE_CHERI_COLOR, 'hatch': BASELINE_CHERI_HATCH, 'label': 'Baseline (CHERI)'},
        'release-dynamic': {'color': BASELINE_MTE_COLOR, 'hatch': BASELINE_MTE_HATCH, 'label': 'Baseline (MTE)'},
        'release-mte': {'color': MTE_COLOR, 'hatch': MTE_HATCH, 'label': 'MTE'},
        'release-asan': {'color': ASAN_COLOR, 'hatch': ASAN_HATCH, 'label': 'ASan'},
        'release-cheri': {'color': CHERI_COLOR, 'hatch': CHERI_HATCH, 'label': 'CHERI'},
}

def add_x_axis_label(ax, text):
    """Place an x-axis label in the empty bottom-left corner, to the left of
    and vertically aligned with the x-tick labels (so it costs no extra
    vertical/horizontal space). The vertical position is measured from the
    actual leftmost tick label, so it tracks pow2 (2^n) and plain (KiB) ticks
    alike instead of relying on a hand-tuned offset."""
    fig = ax.figure
    fig.canvas.draw()  # ensure tick labels have real extents
    labels = [t for t in ax.get_xticklabels() if t.get_text()]
    if labels:
        bb = labels[0].get_window_extent()
        y_frac = ax.transAxes.inverted().transform((0, bb.y0))[1]
    else:
        y_frac = 0
    ax.annotate(
        text,
        xy=(0.05, y_frac),
        xycoords="axes fraction",
        xytext=(0, -1),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=FONTSIZE,
        annotation_clip=False,
    )

lower_better_str = "Lower is better ↓"
higher_better_str = "Higher is better ↑"
left_better_str = "Lower is better ←"
right_better_str = "Higher is better →"

SINGLE_COL_SIZE=(6, 3)

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
mpl.use("Agg")
mpl.rcParams["text.latex.preamble"] = r"\usepackage{amsmath}"
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["font.family"] = "libertine"


mpl.rcParams.update({
       "text.usetex": True,
       "font.family": "serif",
       "font.serif": ["Linux Libertine O"],
       "text.latex.preamble": r"""
   \usepackage[tt=false, type1=true]{libertine}
   \usepackage[libertine]{newtxmath}
   """
})

# 3.3 inch for single column, 7 inch for double column
figwidth_third = 2
figwidth_half = 3.3
figwidth_full = 7
fig_height = 1.2
FONTSIZE=7

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

def darken(color):
    hue, saturation, value = rgb_to_hsv(to_rgb(color))
    return hsv_to_rgb((hue, saturation, value * 0.9))

hatch_def = [
    "//",
    '',
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

BASELINE_MTE_COLOR = 'tab:blue'
MTE_COLOR = 'tab:orange'
BASELINE_CHERI_COLOR = 'tab:green'
CHERI_COLOR = 'tab:red'
ASAN_COLOR = 'tab:purple'
BASELINE_MTE_HATCH = ''
MTE_HATCH = '///'
BASELINE_CHERI_HATCH = '\\\\'
CHERI_HATCH = '||||'
ASAN_HATCH = 'xx'

style_map = {
        'release-static': {'color': BASELINE_CHERI_COLOR, 'hatch': BASELINE_CHERI_HATCH, 'label': 'Baseline (CHERI)'},
        'release-dynamic': {'color': BASELINE_MTE_COLOR, 'hatch': BASELINE_MTE_HATCH, 'label': 'Baseline (MTE)'},
        'release-mte': {'color': MTE_COLOR, 'hatch': MTE_HATCH, 'label': 'MTE'},
        'release-asan': {'color': ASAN_COLOR, 'hatch': ASAN_HATCH, 'label': 'ASan'},
        'release-cheri': {'color': CHERI_COLOR, 'hatch': CHERI_HATCH, 'label': 'CHERI'},
}

lower_better_str = "Lower is better ↓"
higher_better_str = "Higher is better ↑"
left_better_str = "Lower is better ←"
right_better_str = "Higher is better →"

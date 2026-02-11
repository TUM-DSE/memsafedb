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
figwidth_column_third = 1
figwidth_third = 2
figwidth_half = 3.3
figwidth_full = 7
fig_height = 1.5
FONTSIZE=7

# Derived font sizes for consistency
FONTSIZE_AXIS_LABEL = FONTSIZE
FONTSIZE_TICK_LABEL = FONTSIZE
FONTSIZE_LEGEND = FONTSIZE - 1
FONTSIZE_TITLE = FONTSIZE - 1
FONTSIZE_ANNOTATION = FONTSIZE - 2

def format_big_numbers(x, pos):
    if x >= 1e9:
        return f'{x / 1e9:.0f}B'
    elif x >= 1e6:
        return f'{x / 1e6:.0f}M'
    elif x >= 1e3:
        return f'{x / 1e3:.0f}K'
    else:
        return f'{x:.0f}'

def format_big_numbers_tweaked(x, pos):
    if x >= 1e9:
        return f'{x / 1e9:.0f}B'
    elif x >= 1e6:
        return f'{x / 1e6:.0f}M'
    elif x >= 1e3:
        return f'{x / 1e6:.1f}M'
    else:
        return f'{x:.0f}'

palette = sns.color_palette("pastel")
#sns.set(rc={"figure.figsize": (5, 5)})
sns.set_style("whitegrid")
sns.set_style("ticks", {"xtick.major.size": FONTSIZE, "ytick.major.size": FONTSIZE})
sns.set_context("paper", rc={"font.size": FONTSIZE, "axes.titlesize": FONTSIZE, "axes.labelsize": FONTSIZE})

# must be done after sns styles, otherwise they force sans-serif
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

BASELINE_MTE_COLOR = '#1F78B4' # 'A6CEE3'  # Dark blue
MTE_COLOR = '#A6CEE3'          # Light blue
ASAN_COLOR = '#984EA3'          # Purple
BASELINE_CHERI_COLOR = '#FF7F00' # 'FDBF6F' # Dark Orange
CHERI_COLOR = '#FDBF6F'          # Light Orange

BASELINE_MTE_HATCH = ''
MTE_HATCH = '///'
ASAN_HATCH = 'xx'
BASELINE_CHERI_HATCH = ''
CHERI_HATCH = '\\\\\\\\'


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

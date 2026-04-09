#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import sys
import re
import numpy as np
from typing import Dict, Tuple, List, Optional

import common

# Regex to parse the output
# Format: mode,size,iterations,mean_time_ns,stddev_time_ns
CSV_PATTERN = re.compile(r"^\s*\d+,\s*(\d+),\s*\d+,\s*([\d\.]+),\s*([\d\.]+)")

def parse_file(filepath: str) -> Dict[int, Tuple[float, float]]:
    """
    Parses a file and returns a dict: { size_bytes: (mean_ns, stddev_ns) }
    """
    data = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                match = CSV_PATTERN.match(line)
                if match:
                    size = int(match.group(1))
                    time_ns = float(match.group(2))
                    stddev = float(match.group(3))
                    data[size] = (time_ns, stddev)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)
    
    return data

def format_size(bytes_val):
    """Simple formatter for bytes to KB/MB"""
    if bytes_val >= 1024**2:
        return f"{bytes_val / (1024**2):.1f}\\,MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.0f}\\,KB"
    return f"{bytes_val}B"

def format_power_of_two(val):
    if val <= 0:
        return f"{val}"
    if val & (val - 1) == 0:
        exp = int(np.log2(val))
        return f"$2^{{{exp}}}$"
    return f"{val}"

def main():
    parser = argparse.ArgumentParser(description="Plot benchmark overhead with grouped bars.")
    parser.add_argument("files", nargs='+', help="Input text files (First file is BASELINE)")
    parser.add_argument("--variants", required=True, help="Comma-separated list of variant names")
    parser.add_argument("-o", "--output", default="benchmark_overhead_grouped.pdf", help="Output filename")
    parser.add_argument("--title", default="Execution Time Overhead (Normalized)", help="Plot title")
    parser.add_argument("--x-axis", choices=["bytes", "pow2"], default="bytes",
                        help="X-axis label formatting")
    parser.add_argument(
        "--color-scheme",
        choices=["mte", "non-mte", "default"],
        default="default",
        help="Color palette selection"
    )
    parser.add_argument(
        "--show-legend",
        action="store_true",
        help="Show legend"
    )
    
    args = parser.parse_args()

    variant_names = [v.strip() for v in args.variants.split(',')]
    
    if len(variant_names) != len(args.files):
        print(f"Error: Variant count ({len(variant_names)}) != File count ({len(args.files)}).", file=sys.stderr)
        sys.exit(1)

    # 1. Parse all files
    # results[file_index] = { size: (mean, std) }
    results = []
    for filepath in args.files:
        results.append(parse_file(filepath))

    if not results:
        print("No data found.", file=sys.stderr)
        sys.exit(1)

    # 2. Determine common sizes (sorted)
    # We find the intersection of sizes across all files to ensure consistent plotting
    common_sizes = set(results[0].keys())
    for res in results[1:]:
        common_sizes &= set(res.keys())
    
    sorted_sizes = sorted(list(common_sizes))
    
    if not sorted_sizes:
        print("Error: No overlapping sizes found across the input files.", file=sys.stderr)
        sys.exit(1)

    # 3. Prepare data for plotting
    # X-axis labels
    if args.x_axis == "pow2":
        labels = [format_power_of_two(s) for s in sorted_sizes]
    else:
        labels = [format_size(s) for s in sorted_sizes]
    x = np.arange(len(labels))
    
    # Configuration for bar width
    total_width = 0.8
    num_variants = len(results)
    bar_width = total_width / num_variants
    max_tops = np.full(len(sorted_sizes), -np.inf)

    fig, ax = plt.subplots(figsize=(common.figwidth_third, common.fig_height))
    colors = common.get_palette(args.color_scheme, num_variants)
    hatches = common.get_hatches(num_variants)
    
    # Baseline dict for normalization (File index 0)
    baseline_data = results[0]

    for i, (variant_name, variant_data) in enumerate(zip(variant_names, results)):
        means = []
        errs = []

        for size in sorted_sizes:
            base_mean, base_std = baseline_data[size]
            var_mean, var_std = variant_data[size]

            norm_mean = var_mean / base_mean
            norm_err = var_std / base_mean

            means.append(norm_mean)
            errs.append(norm_err)

        for idx, (mean, err) in enumerate(zip(means, errs)):
            max_tops[idx] = max(max_tops[idx], mean + err)

        offset = (i - (num_variants - 1) / 2) * bar_width

        bars = ax.bar(
            x + offset,
            means,
            width=bar_width,
            yerr=errs,
            capsize=3,
            label=variant_name,
            color=colors[i],
            hatch=hatches[i],
            edgecolor='black',
            linewidth=0.5,
            zorder=3
        )

        # Annotate bars above the error bar
        if len(sorted_sizes) * num_variants < 20:
            for idx, (bar, val) in enumerate(zip(bars, means)):
                if i == 0:
                    continue

                bar_height = bar.get_height()
                err = errs[idx]
                pct = (val - 1.0) * 100
                sign = '+' if pct >= 0 else '-'

                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar_height + err,
                    f"${sign}{abs(pct):.0f}\\%$",
                    ha='center',
                    va='bottom',
                    fontsize=common.FONTSIZE_ANNOTATION
                )

    ymin = 1
    ymax = 1
    for result in results:
        for size in sorted_sizes:
            mean, std = result[size]
            norm_mean = mean / baseline_data[size][0]
            norm_std = std / baseline_data[size][0]
            if norm_mean - norm_std < ymin:
                ymin = norm_mean - norm_std
            if norm_mean + norm_std > ymax:
                ymax = norm_mean + norm_std
    pad = (ymax - ymin) * 0.1
    ax.set_ylim(max(0, ymin - pad), ymax + pad)

    # 4. Formatting
    ax.set_ylabel("")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    if args.show_legend:
        ax.legend(
            loc='upper center',
            bbox_to_anchor=(0.5, 0.9),
            ncols=6,
            fontsize=common.FONTSIZE_LEGEND,
            handlelength=0.8,  # shorter color boxes
            handleheight=0.8,  # smaller vertical box
            handletextpad=0.4,  # tighter gap between box and text
            columnspacing=0.8  # shrink per column width
        )
    ylim_low, ylim_high = ax.get_ylim()
    y_axes = 0.88
    y_data = ylim_low + (ylim_high - ylim_low) * y_axes
    side_span = max(1, int(np.ceil(len(sorted_sizes) * 0.2)))
    left_top = np.max(max_tops[:side_span])
    right_top = np.max(max_tops[-side_span:])
    left_clearance = y_data - left_top
    right_clearance = y_data - right_top
    place_right = right_clearance > left_clearance

    ax.annotate(
        common.lower_better_str,
        color="blue",
        xy=((0.98 if place_right else 0.02), y_axes),
        xycoords="axes fraction",
        annotation_clip=False,
        fontsize=common.FONTSIZE,
        ha=("right" if place_right else "left"),
    )
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.2f}"))
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    
    # Baseline line
    ax.axhline(y=1.0, color='black', linestyle='-', linewidth=1, zorder=2, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{args.output}.pdf")
    print(f"Chart saved to {args.output}.pdf")

if __name__ == "__main__":
    main()

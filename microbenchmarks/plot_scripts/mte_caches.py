#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any
import common
import seaborn as sns  # type: ignore

def _format_bytes(value):
    if value >= 1024**2:
        return f"{int(value // (1024**2))}\\,MiB"
    if value >= 1024:
        return f"{int(value // 1024)}\\,KiB"
    return f"{int(value)}\\,B"

def parse_file(path: str) -> Dict[str, Any]:
    data = {
        "mode1": {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: []},
        "mode2": {0: [], 1: []}
    }

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            parts = line.split(",")
            mode = int(parts[0])

            if mode == 1:
                # 1, submode, size, iters, mean_ns, stddev_ns
                sub = int(parts[1])
                size = int(parts[2])
                mean = float(parts[4])
                std = float(parts[5])
                data["mode1"][sub].append((size, mean, std))
            
            elif mode == 2:
                # 2, with_tagger, size, iters, mean_ns, stddev_ns
                tagger = int(parts[1])
                size = int(parts[2])
                mean = float(parts[4])
                std = float(parts[5])
                data["mode2"][tagger].append((size, mean, std))

    return data

def calc_bw_stats(points):
    """
    Returns (sizes, bandwidths, bandwidth_errors)
    
    Bandwidth (B) = Size / Time
    Error propagation: Sigma_B = B * (Sigma_Time / Time)
    """
    points.sort(key=lambda x: x[0])
    
    sizes = np.array([p[0] for p in points])
    means_ns = np.array([p[1] for p in points])
    stds_ns = np.array([p[2] for p in points])
    
    # Avoid div by zero
    means_ns[means_ns == 0] = 1e-9
    
    # Calculate GB/s
    bw_gbs = sizes / means_ns 
    
    # Calculate Error
    bw_err = bw_gbs * (stds_ns / means_ns)
    
    return sizes, bw_gbs, bw_err

def plot_mode1(data: Dict[int, List], out_prefix: str, color_scheme: str):
    if not any(data.values()):
        print("No Mode 1 data found.")
        return

    fig, ax = plt.subplots(figsize=(common.figwidth_half, common.fig_height * 1.4))
    
    labels = {
        0: "memset (MTE off)",
        1: "memset (MTE sync)",
        2: "stg",
        3: "stzg",
        4: "stz2g",
        5: "stgp",
        6: "memset + stg",
        7: "memset + st2g",
        8: "stp",
        9: "stnp",
    }
    sub_keys = [k for k in sorted(data.keys()) if data[k]]
    colors = sns.color_palette()
    markers = common.get_markers(len(sub_keys))

    for idx, sub in enumerate(sub_keys):
        
        sizes, bws, errs = calc_bw_stats(data[sub])
        
        ax.errorbar(
            sizes,
            bws,
            yerr=errs,
            color=colors[idx],
            marker=markers[idx],
            label=labels[sub],
            capsize=3,
            elinewidth=1,
        )

    ax.set_xscale("log", base=2)
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: _format_bytes(x))
    )
    ax.set_yscale("log")
    ax.set_ylabel("Throughput (GB/s)")
    ax.annotate(
        common.higher_better_str,
        color="blue",
        xy=(0.5, 0.95),
        xycoords="axes fraction",
        ha="center",
        va="top",
        annotation_clip=False,
        fontsize=common.FONTSIZE,
    )
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=common.FONTSIZE_LEGEND, loc='center left', bbox_to_anchor=(1.02, 0.5))

    out_file = f"{out_prefix}_mode1.pdf"
    fig.tight_layout()
    fig.savefig(out_file)
    print(f"Generated {out_file}")

def plot_mode2(data: Dict[int, List], out_prefix: str, color_scheme: str):
    if not data[0]:
        print("No Mode 2 data found.")
        return

    fig, ax = plt.subplots(figsize=(common.figwidth_half, common.fig_height))

    colors = common.get_palette(color_scheme, 2)
    markers = common.get_markers(2)

    # Baseline
    sz0, bw0, err0 = calc_bw_stats(data[0])
    ax.errorbar(
        sz0,
        bw0,
        yerr=err0,
        color=colors[0],
        marker=markers[0],
        label="Reader Only",
        capsize=3,
        elinewidth=1,
    )

    # Tagger
    if data[1]:
        sz1, bw1, err1 = calc_bw_stats(data[1])
        ax.errorbar(
            sz1,
            bw1,
            yerr=err1,
            color=colors[1],
            marker=markers[1],
            linestyle="--",
            label="Reader + Background Tagger",
            capsize=3,
            elinewidth=1,
        )

    ax.set_xscale("log", base=2)
    # ax.set_yscale("log")
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: _format_bytes(x))
    )
    
    ax.set_ylabel("Throughput (GB/s)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=common.FONTSIZE_LEGEND)
    ax.annotate(
        common.higher_better_str,
        color="blue",
        xy=(0.37, 0.83),
        xycoords="figure fraction",
        annotation_clip=False,
        fontsize=common.FONTSIZE,
    )

    out_file = f"{out_prefix}_mode2.pdf"
    fig.tight_layout()
    fig.savefig(out_file)
    print(f"Generated {out_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Input CSV file")
    parser.add_argument("-o", "--output-prefix", default="mte_bench", help="Output prefix")
    parser.add_argument(
        "--color-scheme",
        choices=["mte", "non-mte", "default"],
        default="default",
        help="Color palette selection"
    )
    args = parser.parse_args()

    data = parse_file(args.file)
    
    if any(data["mode1"].values()):
        plot_mode1(data["mode1"], args.output_prefix, args.color_scheme)
    
    if any(data["mode2"].values()):
        plot_mode2(data["mode2"], args.output_prefix, args.color_scheme)

if __name__ == "__main__":
    main()

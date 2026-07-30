#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
import sys
import re
import numpy as np
import common

# CSV:
# label,size_bytes,num_allocs,total_bytes,iterations,
# mean_time_ns,stddev_time_ns,min_time_ns,max_time_ns

CSV_PATTERN = re.compile(
    r"^\s*([^,]*),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d\.]+),\s*([\d\.]+)"
)

def parse_file(path):
    data = {}
    label_from_file = None

    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                m = CSV_PATTERN.match(line)
                if not m:
                    continue

                label = m.group(1)
                size_bytes = int(m.group(2))
                mean_ms = float(m.group(6)) / 10e6
                std_ms = float(m.group(7)) / 10e6

                if label and not label_from_file:
                    label_from_file = label

                data[size_bytes] = (mean_ms, std_ms)
    except FileNotFoundError:
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    return data, label_from_file

def main():
    parser = argparse.ArgumentParser(
        description="Plot malloc size benchmark as normalized line plot"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="CSV files. First file is baseline"
    )
    parser.add_argument(
        "--labels",
        help="Comma separated labels for variants (optional, overrides CSV labels)"
    )
    parser.add_argument(
        "-o", "--output",
        default="malloc_sizes_overhead.pdf",
        help="Output filename (PDF)"
    )

    args = parser.parse_args()

    parsed = [parse_file(f) for f in args.files]
    results = [p[0] for p in parsed]
    csv_labels = [p[1] for p in parsed]

    if args.labels:
        labels = [x.strip() for x in args.labels.split(",")]
        if len(labels) != len(results):
            print("Number of labels must match number of files", file=sys.stderr)
            sys.exit(1)
    else:
        # Fall back to labels from CSV, or filename if not present
        labels = []
        for (path, (_, lbl)) in zip(args.files, parsed):
            if lbl:
                labels.append(lbl)
            else:
                labels.append(path)

    baseline = results[0]

    # Common sizes across all runs
    common_sizes = sorted(set.intersection(*(set(r.keys()) for r in results)))
    if not common_sizes:
        print("No common sizes across files", file=sys.stderr)
        sys.exit(1)

    x = np.array(common_sizes, dtype=float)

    plt.figure(figsize=(common.figwidth_third, common.fig_height * 1.1))

    colors = common.get_palette("mte", len(results))
    markers = common.get_markers(len(results))
    for idx, (res, label, marker) in enumerate(zip(results, labels, markers)):
        means = []
        errs = []
        for s in common_sizes:
            # base_mean, base_std = baseline[s]
            mean, std = res[s]
            norm_mean = mean
            norm_err = std
            means.append(norm_mean)
            errs.append(norm_err)

        plt.errorbar(
            x,
            means,
            yerr=errs,
            color=colors[idx],
            marker=marker,
            linestyle="-",
            linewidth=1.2,
            markersize=4,
            capsize=3,
            label=label,
        )

    plt.xscale("log", base=2)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: fmt_size(v)))
    plt.yscale("log")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylabel(
        "Time (ms)",
        fontsize=common.FONTSIZE_TICK_LABEL,
        labelpad=0,
    )
    ax.tick_params(axis="y", pad=0, labelsize=common.FONTSIZE_TICK_LABEL)
    ax.tick_params(axis="x", pad=0, labelsize=common.FONTSIZE_TICK_LABEL)
    common.add_x_axis_label(ax, "Region size")
    ax.annotate(
        common.lower_better_str,
        color="blue",
        xy=(0.50, 0.90),
        xycoords="axes fraction",
        annotation_clip=False,
        fontsize=common.FONTSIZE,
        ha="center",
    )
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.legend(fontsize=common.FONTSIZE_LEGEND)

    out = args.output
    if not out.endswith(".pdf"):
        out += ".pdf"
    plt.savefig(out)
    print(f"Saved {out}")

def fmt_size(v):
    if v < 1024:
        return f"{int(v)}\,B"
    elif v < 1024**2:
        return f"{int(v // 1024)}\,KiB"
    else:
        return f"{int(v // (1024**2))}\,MiB"

if __name__ == "__main__":
    main()

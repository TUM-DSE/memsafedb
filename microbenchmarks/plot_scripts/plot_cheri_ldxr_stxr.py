#!/usr/bin/env python3
import argparse
import csv
import sys

import matplotlib.pyplot as plt

import common


def parse_csv(path):
    data = {}
    try:
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kind = row["kind"].strip()
                data[kind] = {
                    "mean": float(row["mean_ns_per_op"]),
                    "stddev": float(row["stddev_ns_per_op"]),
                }
    except FileNotFoundError:
        print(f"Error: File '{path}' not found.", file=sys.stderr)
        sys.exit(1)
    except KeyError as exc:
        print(f"Error: Missing column {exc} in '{path}'.", file=sys.stderr)
        sys.exit(1)
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Plot LDXR/STXR cost for normal vs capability pointers."
    )
    parser.add_argument("input", help="CSV input file")
    parser.add_argument("-o", "--output", default="ldxr_stxr_morello", help="Output name")
    parser.add_argument("--title", default="LDXR/STXR Cost (Morello Hybrid)", help="Plot title")
    args = parser.parse_args()

    data = parse_csv(args.input)
    if "normal" not in data or "capability" not in data:
        print("Error: Expected 'normal' and 'capability' rows.", file=sys.stderr)
        sys.exit(1)

    labels = ["Normal", "Capability"]
    means = [data["normal"]["mean"], data["capability"]["mean"]]
    errs = [data["normal"]["stddev"], data["capability"]["stddev"]]
    colors = common.get_palette("non-mte", len(labels))
    hatches = common.get_hatches(len(labels))

    fig, ax = plt.subplots(figsize=(4, 2.5))
    x = range(len(labels))
    bars = ax.bar(
        x,
        means,
        yerr=errs,
        capsize=3,
        color=colors,
        edgecolor="black",
        linewidth=0.6,
        zorder=3,
    )
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    for bar, val in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=common.FONTSIZE_ANNOTATION,
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("ns/op")
    ax.set_title(args.title)
    ax.annotate(
        common.lower_better_str,
        color="blue",
        xy=(0.05, 0.75),
        xycoords="figure fraction",
        annotation_clip=False,
        fontsize=common.FONTSIZE,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)

    plt.tight_layout()
    plt.savefig(f"{args.output}.pdf")
    print(f"Chart saved to {args.output}.pdf")


if __name__ == "__main__":
    main()

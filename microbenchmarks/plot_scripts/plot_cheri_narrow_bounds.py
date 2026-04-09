#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
import sys
import re
import numpy as np
import common

# Expected CSV: narrow_bounds,region_bytes,object_bytes,num_objects,iterations,
#               mean_time_ns,stddev_time_ns,min_time_ns,max_time_ns

CSV_PATTERN = re.compile(
    r"^\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d\.]+),\s*([\d\.]+)"
)

def parse_file(filepath):
    data = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                m = CSV_PATTERN.match(line)
                if not m:
                    continue

                narrow = int(m.group(1))
                region = int(m.group(2))
                obj = int(m.group(3))
                num_obj = int(m.group(4))
                mean = float(m.group(6))
                std = float(m.group(7))

                # group by region bytes
                data[num_obj] = (mean, std)
    except FileNotFoundError:
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    return data

def main():
    parser = argparse.ArgumentParser(
        description="Plot CHERI suballocation overhead line graph"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="CSV results. First entry is baseline"
    )
    parser.add_argument(
        "--labels",
        required=True,
        help="Comma separated names for each file"
    )
    parser.add_argument(
        "-o", "--output",
        default="cheri_suballoc_overhead.pdf",
        help="Output filename (PDF)"
    )
    args = parser.parse_args()

    labels = [s.strip() for s in args.labels.split(",")]
    if len(labels) != len(args.files):
        print("Error: number of labels must match number of files", file=sys.stderr)
        sys.exit(1)

    # Parse
    results = [parse_file(f) for f in args.files]
    baseline = results[0]

    # Intersection of object sizes
    common_sizes = sorted(set.intersection(*(set(r.keys()) for r in results)))
    if not common_sizes:
        print("No common object sizes found", file=sys.stderr)
        sys.exit(1)

    # Normalize
    x = np.array(common_sizes)

    plt.figure(figsize=(7, 3.5))
    colors = common.get_palette("non-mte", len(results))
    markers = common.get_markers(len(results))

    for idx, (res, label) in enumerate(zip(results, labels)):
        means = [res[s][0] / baseline[s][0] for s in common_sizes]
        errs = [res[s][1] / baseline[s][0] for s in common_sizes]

        plt.errorbar(
            x, means,
            yerr=errs,
            color=colors[idx],
            marker=markers[idx],
            linestyle="-",
            linewidth=1.2,
            markersize=4,
            capsize=3,
            label=label
        )

    # Horizontal baseline
    plt.axhline(y=1.0, color="black", linewidth=1, alpha=0.3)

    plt.xscale("log", base=2)
    plt.xlabel("Object size (bytes)")
    plt.ylabel("Normalized time")
    plt.title("CHERI Suballocation Cost (Normalized)")
    ax = plt.gca()
    ax.annotate(
        common.lower_better_str,
        color="blue",
        xy=(0.05, 0.75),
        xycoords="figure fraction",
        annotation_clip=False,
        fontsize=common.FONTSIZE,
    )
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.legend(fontsize=common.FONTSIZE_LEGEND)

    outfile = args.output
    if not outfile.endswith(".pdf"):
        outfile += ".pdf"
    plt.savefig(outfile)
    print(f"Saved {outfile}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import sys
from math import isnan

def fmt(x):
    if x is None:
        return "-"
    # Avoid scientific notation in LaTeX
    return f"{x:.2f}"

def print_table(benchmark, results):
    # Collect instruction entries, skip non instruction fields
    entries = []
    for name, val in results.items():
        if isinstance(val, dict) and "latency" in val and "throughput" in val:
            entries.append((name, val))

    print(f"% Benchmark: {benchmark}")
    print(r"\begin{tabular}{ccc}")
    print(r"\toprule")
    print(r"Instruction & Latency & Throughput \\")
    print(r"\midrule")
    for name, val in entries:
        lat = fmt(val.get("latency"))
        thr = fmt(val.get("throughput"))
        name = name.replace("_", r"\_")
        print(f"{name} & {lat} & {thr} \\\\")
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print()  # blank line between tables

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} PATH_TO_JSON", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r") as f:
        data = json.load(f)

    # Expect a list of { "benchmark": ..., "results": {...} }
    benchmark = data.get("benchmark", "unknown")
    results = data.get("results", {})
    print_table(benchmark, results)

if __name__ == "__main__":
    main()



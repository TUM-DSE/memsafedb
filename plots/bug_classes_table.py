#!/usr/bin/env python3
"""Generate the bug-class detection table (Sec. 6.4) from the bug_classes
runner CSVs (results/bug_classes/<config>.csv).

Each row is one memory-safety class of the bug-study classifier and summarizes
the test cases of that class (the `class` column, set in bug_classes/bugs.c)."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "results" / "bug_classes"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "bug_classes" / "bug_classes_table.tex"
DEFAULT_MACROS = PROJECT_ROOT / "results" / "bug_classes" / "bug_classes_macros.tex"

COLUMNS = [("baseline", "Baseline"), ("mte", "MTE"), ("cheri", "CHERI")]

# Table rows: (class name used in bugs.c, LaTeX label).
ROWS = [
    ("Heap buffer overflow", "Heap buffer overflow"),
    ("Stack/global buffer overflow", "Stack/global buffer overflow"),
    ("Out-of-bounds read/write", "Out-of-bounds read/write"),
    ("Integer overflow to corruption", "Integer overflow $\\to$ corruption"),
    ("Use-after-free", "Use-after-free"),
    ("Double/invalid free", "Double/invalid free"),
    ("Null pointer dereference", "Null pointer dereference"),
    ("Uninitialized memory access", "Uninitialized memory access"),
]

# Classes CHERI can detect only with capability revocation, which Morello
# Linux does not provide (CheriBSD does). Any crash or silence for these comes
# from the allocator (e.g., musl unmapping freed pages), not from CHERI.
CHERI_NEEDS_REVOCATION = {"Use-after-free"}

# Cases not counted for a configuration. With CHERI, a small overflow past a
# large object stays within the padding of its rounded-up bounds: it cannot
# reach another object, so it is not a vulnerability.
EXCLUDED = {("cheri", "heap_overflow_large")}

# In-cell annotations of partially detected cells; %s is replaced by the
# detection percentage(s) of the probabilistic cases.
PARTIAL_NOTES = {
    ("Heap buffer overflow", "mte"): "into next object",
    ("Out-of-bounds read/write", "mte"): "%s",
    ("Use-after-free", "mte"): "%s",
    ("Double/invalid free", "mte"): "double free only",
}

MACROS = r"""% Cell macros for the bug-class table (requires xcolor, colortbl, pifont).
\definecolor{bcgood}{RGB}{190,230,190}
\definecolor{bcprob}{RGB}{255,236,160}
\definecolor{bcother}{RGB}{255,212,170}
\definecolor{bcmiss}{RGB}{245,180,175}
\definecolor{bcos}{RGB}{220,220,220}
\newcommand{\BcTrap}{\cellcolor{bcgood}\ding{51}}                         % detected at the access
\newcommand{\BcPartial}[1]{\cellcolor{bcprob}\ding{51}\,{\scriptsize(#1)}} % detected for some cases (#1: which)
\newcommand{\BcLibc}{\cellcolor{bcother}libc}                             % allocator/libc check
\newcommand{\BcCrash}{\cellcolor{bcother}crash}                           % crash without detection
\newcommand{\BcSilent}{\cellcolor{bcmiss}\ding{55}}                       % undetected
\newcommand{\BcNoOS}{\cellcolor{bcos}OS}                                  % needs revocation (OS)
\newcommand{\BcLegend}[2]{\colorbox{#1}{\makebox[1.8em]{\strut #2}}}      % legend entry
"""

CELLS = {
    "trap": r"\BcTrap",
    "partial": r"\BcPartial{%s}",
    "libc": r"\BcLibc",
    "crash": r"\BcCrash",
    "miss": r"\BcSilent",
    "noos": r"\BcNoOS",
}


def load(input_dir: Path) -> dict[tuple[str, str], list[list[dict]]]:
    """Returns {(config, class): [rows of case 1, rows of case 2, ...]}, without
    the EXCLUDED cases."""
    data: dict[tuple[str, str], dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for config, _ in COLUMNS:
        path = input_dir / f"{config}.csv"
        if not path.exists():
            print(f"warning: missing {path}")
            continue
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                row["count"] = int(row["count"])
                row["runs"] = int(row["runs"])
                if (config, row["bug"]) not in EXCLUDED:
                    data[(config, row["class"])][row["bug"]].append(row)
    return {key: list(cases.values()) for key, cases in data.items()}


def classify_case(rows: list[dict]) -> tuple[str, int]:
    """Reduces the runs of one case to (outcome, detection percentage)."""
    runs = rows[0]["runs"]

    def total(pred) -> int:
        return sum(r["count"] for r in rows if pred(r))

    detected = total(lambda r: r["outcome"] == "hw_trap")
    at_access = total(lambda r: r["outcome"] == "hw_trap" and r["timing"] == "access")
    if detected == runs:
        return ("trap", 100) if at_access == runs else ("late", 100)
    if detected > 0:
        return "prob", round(100 * detected / runs)
    buckets = {
        "libc": total(lambda r: r["outcome"] == "runtime_abort"),
        "crash": total(lambda r: r["outcome"] in ("crash", "hang", "exit", "unknown")),
        "miss": total(lambda r: r["outcome"] == "silent"),
    }
    return max(buckets, key=lambda k: buckets[k]), 0


def aggregate(config: str, cls: str, cases: list[list[dict]]) -> tuple[str, list[int]]:
    """Reduces the cases of one class to (cell key, probabilistic percentages)."""
    if not cases:
        raise SystemExit(f"no results for class '{cls}' in config '{config}'")
    outcomes = [classify_case(rows) for rows in cases]
    kinds = [k for k, _ in outcomes]
    probs = sorted({p for k, p in outcomes if k == "prob"})
    if all(k == "trap" for k in kinds):
        return "trap", probs
    if config == "cheri" and cls in CHERI_NEEDS_REVOCATION and not any(k in ("trap", "prob") for k in kinds):
        return "noos", probs
    if any(k in ("trap", "late", "prob") for k in kinds):
        return "partial", probs
    if all(k == "libc" for k in kinds):
        return "libc", probs
    if all(k == "crash" for k in kinds):
        return "crash", probs
    return "miss", probs


def partial_note(cls: str, config: str, probs: list[int], latex: bool) -> str:
    text = PARTIAL_NOTES.get((cls, config), "some cases")
    if "%s" in text:
        text = text % ("--".join(str(p) for p in probs) + (r"\%" if latex else "%"))
    return text


def build_latex(data) -> str:
    lines = [
        r"\begin{tabular}{@{}l" + "c" * len(COLUMNS) + "@{}}",
        r"\toprule",
        r"\textbf{Bug class} & " + " & ".join(rf"\textbf{{{n}}}" for _, n in COLUMNS) + r" \\",
        r"\midrule",
    ]
    for cls, label in ROWS:
        cells = []
        for config, _ in COLUMNS:
            key, probs = aggregate(config, cls, data.get((config, cls), []))
            cell = CELLS[key]
            cells.append(cell % partial_note(cls, config, probs, latex=True) if key == "partial" else cell)
        lines.append(f"{label} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(lines)


def print_summary(data) -> None:
    print(f"{'class':<32}" + "".join(f"{c:>26}" for c, _ in COLUMNS))
    for cls, _ in ROWS:
        cells = []
        for config, _ in COLUMNS:
            key, probs = aggregate(config, cls, data.get((config, cls), []))
            cells.append(f"partial ({partial_note(cls, config, probs, latex=False)})"
                         if key == "partial" else key)
        print(f"{cls:<32}" + "".join(f"{c:>26}" for c in cells))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Directory with <config>.csv files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output LaTeX table path")
    parser.add_argument("--macros", type=Path, default=DEFAULT_MACROS, help="Output LaTeX macro definitions")
    args = parser.parse_args()

    data = load(args.input)
    unknown = sorted({cls for (_, cls) in data} - {cls for cls, _ in ROWS})
    if unknown:
        print(f"warning: classes not in the table: {', '.join(unknown)}")
    print_summary(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_latex(data))
    args.macros.write_text(MACROS)
    print(f"Wrote LaTeX table to {args.output} (macros: {args.macros})")


if __name__ == "__main__":
    main()

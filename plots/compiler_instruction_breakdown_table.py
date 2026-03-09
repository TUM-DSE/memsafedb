#!/usr/bin/env python3
"""Generate a LaTeX instruction-breakdown table."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import cast


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "results" / "compiler_instruction_breakdown.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "compiler_instruction_breakdown.tex"

SECTION_SPECS = [
    ("cheri", ("binary",), "capability-operand", "CHERI capability operands", "warn"),
    ("cheri", ("binary",), "new-instruction", "CHERI new instructions", "warn"),
    ("mte", ("binary", "glibc"), "new-instruction", "MTE instructions", "good"),
]


def parse_top(value: str) -> int | None:
    if value == "all":
        return None
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--top must be a positive integer or 'all'")
    return parsed


def latex_escape(text: str) -> str:
    return text.replace("_", r"\_")


def color_intensity(share: float) -> int:
    return max(12, min(82, int(round(12 + 70 * share))))


def format_count_cell(count: int, share: float, color: str) -> str:
    intensity = color_intensity(share)
    return rf"\cellcolor{{{color}!{intensity}!white}} {count:,} ({share * 100:.1f}\%)"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def format_combined_label(mnemonics: list[str]) -> str:
    return ", ".join(rf"\texttt{{{latex_escape(mnemonic)}}}" for mnemonic in mnemonics)


def aggregate_section(
    rows: list[dict[str, str]],
    mechanism: str,
    components: tuple[str, ...],
    category: str,
    top_n: int | None,
) -> tuple[list[tuple[str, int, str | None]], int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["mechanism"] != mechanism:
            continue
        if row["component"] not in components:
            continue
        if row["category"] != category:
            continue
        counts[row["mnemonic"]] += int(row["count"])

    ordered_pairs = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    total = sum(count for _, count in ordered_pairs)
    ordered: list[tuple[str, int, str | None]]

    if top_n is not None and len(ordered_pairs) > top_n:
        kept: list[tuple[str, int, str | None]] = [(mnemonic, count, None) for mnemonic, count in ordered_pairs[:top_n]]
        remaining = ordered_pairs[top_n:]
        other_sum = sum(count for _, count in remaining)
        if other_sum:
            kept.append(("__combined__", other_sum, format_combined_label([mnemonic for mnemonic, _ in remaining])))
        ordered = kept
    else:
        ordered = [(mnemonic, count, None) for mnemonic, count in ordered_pairs]

    return cast(list[tuple[str, int, str | None]], ordered), total


def build_table(rows: list[dict[str, str]], top_n: int | None) -> str:
    lines = [
        r"\begin{table}[t]",
        r"    \centering",
        r"    \footnotesize",
        r"    \begin{tabularx}{\columnwidth}{@{}Xr@{}}",
        r"        \toprule",
        r"        \textbf{Instruction} & \textbf{Count} \\",
        r"        \midrule",
    ]

    emitted_sections = 0
    for mechanism, components, category, title, color in SECTION_SPECS:
        section_rows, total = aggregate_section(rows, mechanism, components, category, top_n)
        if not section_rows or total == 0:
            continue
        if emitted_sections > 0:
            lines.append(r"        \midrule")
        lines.append(rf"        \multicolumn{{2}}{{@{{}}l}}{{\textbf{{{title}}}}} \\")
        lines.append(r"        \midrule")
        for mnemonic, count, combined_label in section_rows:
            share = count / total
            cell = format_count_cell(count, share, color)
            mnemonic_tex = combined_label if mnemonic == "__combined__" else rf"\texttt{{{latex_escape(mnemonic)}}}"
            lines.append(rf"        {mnemonic_tex} & {cell} \\")
        emitted_sections += 1

    lines.extend(
        [
            r"        \bottomrule",
            r"    \end{tabularx}",
            r"    \caption{Instruction breakdown aggregated across evaluated systems. When a top-$N$ cutoff is used, remaining instructions are summed into \texttt{Other}.}",
            r"    \label{tab:compiler-instruction-breakdown}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LaTeX instruction-breakdown table")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input CSV produced by count_new_instructions.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output LaTeX table path")
    parser.add_argument("--top", type=parse_top, default=None, help="Top instructions per section to keep, or 'all'")
    args = parser.parse_args()

    rows = load_rows(args.input)
    table = build_table(rows, args.top)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(table)
    print(f"Wrote LaTeX table to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

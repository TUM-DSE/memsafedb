#!/usr/bin/env python3
"""
Generate LaTeX table from perf counter results for academic papers.
"""

import argparse
import re
import sys
from typing import Dict, List, Tuple, Optional

def parse_perf_results(filepath: str) -> Dict[str, Dict[str, float]]:
    """Parse perf counter output file"""
    results = {}
    current_op = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            # Detect operation sections [name]
            if line.startswith('[') and line.endswith(']'):
                current_op = line[1:-1]
                results[current_op] = {}
                continue

            if not current_op:
                continue

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse metric lines (handle numbers with commas like 1,234,567)
            # Format: "value     metric"
            line = re.sub(r'#.*$', '', line).strip()  # Remove comments

            # Use regex to parse - handles numbers with commas correctly
            match = re.match(r'([\d,\.]+)\s+(.+?)(?:\s|$)', line)
            if match:
                value_str = match.group(1).replace(',', '')
                metric = match.group(2).strip()
            else:
                continue

            try:
                value = float(value_str)
                results[current_op][metric] = value
            except ValueError:
                continue

    return results

def calculate_derived_metrics(results: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Calculate derived metrics like IPC, normalized performance, etc."""
    metrics = {}

    for op, counters in results.items():
        metrics[op] = counters.copy()

        # Calculate IPC if not present
        if 'IPC' not in metrics[op] and 'cycles' in counters and 'instructions' in counters:
            if counters['cycles'] > 0:
                metrics[op]['IPC'] = counters['instructions'] / counters['cycles']

        # Calculate cache miss rate if not present
        if 'cache-miss-rate' not in metrics[op]:
            if 'cache-references' in counters and 'cache-misses' in counters:
                if counters['cache-references'] > 0:
                    metrics[op]['cache-miss-rate'] = (counters['cache-misses'] /
                                                     counters['cache-references']) * 100

    # Normalize cycles to memset baseline
    if 'memset' in metrics and 'cycles' in metrics['memset']:
        baseline = metrics['memset']['cycles']
        for op in metrics:
            if 'cycles' in metrics[op]:
                metrics[op]['normalized-cycles'] = metrics[op]['cycles'] / baseline

    return metrics

def format_value(value: float, metric: str, is_best: bool = False,
                 format_type: str = 'standard') -> str:
    """Format value based on metric type and whether it's the best"""

    # Format the number
    if metric in ['cycles', 'instructions', 'cache-references', 'cache-misses',
                  'L1-dcache-loads', 'L1-dcache-load-misses', 'branches']:
        # Large numbers - use G/M/K suffix with \, separator
        if value >= 1e9:
            formatted = f"{value/1e9:.2f}\\,G"
        elif value >= 1e6:
            formatted = f"{value/1e6:.0f}\\,M"
        elif value >= 1e3:
            formatted = f"{value/1e3:.0f}\\,K"
        else:
            formatted = f"{value:.0f}"
    elif metric in ['IPC']:
        formatted = f"{value:.2f}"
    elif 'rate' in metric or 'normalized' in metric:
        formatted = f"{value:.2f}"
    elif metric == 'seconds':
        formatted = f"{value:.3f}"
    else:
        formatted = f"{value:.2f}"

    # Add formatting for best values
    if is_best and format_type == 'standard':
        return f"\\textbf{{{formatted}}}"
    elif is_best and format_type == 'color':
        return f"\\textbf{{\\color{{ForestGreen}}{formatted}}}"
    else:
        return formatted

def generate_latex_table(metrics: Dict[str, Dict[str, float]],
                         format_type: str = 'standard',
                         caption: str = None,
                         label: str = None) -> str:
    """Generate LaTeX table from metrics"""

    # Define operation order and display names
    op_order = ['memset', 'stzg', 'stgp', 'stnp', 'stp']
    op_names = {
        'memset': 'memset',
        'stzg': 'STZG',
        'stgp': 'STGP',
        'stnp': 'STNP',
        'stp': 'STP'
    }

    # Filter to operations that exist in the data
    ops = [op for op in op_order if op in metrics]

    # Key metrics for the paper
    key_metrics = [
        ('cycles', 'Cycles', 'lower'),
        ('instructions', 'Instructions', 'lower'),
        ('IPC', 'IPC', 'higher'),
        ('cache-miss-rate', 'Cache Miss Rate (\\%)', 'lower'),
        ('normalized-cycles', 'Normalized Runtime', 'lower'),
    ]

    # Start building the table
    latex = []

    if format_type == 'color':
        latex.append("\\usepackage{xcolor}  % Add to preamble if not present")
        latex.append("")

    latex.append("\\begin{table}[t]")
    latex.append("\\centering")

    if caption:
        latex.append(f"\\caption{{{caption}}}")
    else:
        latex.append("\\caption{Performance characteristics of memory zeroing operations on Ampere-1a (32MB buffer)}")

    if label:
        latex.append(f"\\label{{{label}}}")
    else:
        latex.append("\\label{tab:perf-counters}")

    # Table header
    col_spec = 'l' + 'r' * len(ops)
    latex.append(f"\\begin{{tabular}}{{{col_spec}}}")
    latex.append("\\toprule")

    # Column headers
    header = "Metric & " + " & ".join([op_names.get(op, op) for op in ops]) + " \\\\"
    latex.append(header)
    latex.append("\\midrule")

    # Add each metric row
    for metric_key, metric_name, better in key_metrics:
        # Check if metric exists for any operation
        if not any(metric_key in metrics[op] for op in ops):
            continue

        values = []
        for op in ops:
            if metric_key in metrics[op]:
                values.append((op, metrics[op][metric_key]))
            else:
                values.append((op, None))

        # Find best value
        valid_values = [(op, v) for op, v in values if v is not None]
        if valid_values:
            if better == 'lower':
                best_op, best_val = min(valid_values, key=lambda x: x[1])
            else:  # 'higher'
                best_op, best_val = max(valid_values, key=lambda x: x[1])
        else:
            best_op, best_val = None, None

        # Format row
        row_values = []
        for op, val in values:
            if val is not None:
                is_best = (op == best_op)
                row_values.append(format_value(val, metric_key, is_best, format_type))
            else:
                row_values.append("---")

        row = f"{metric_name} & " + " & ".join(row_values) + " \\\\"
        latex.append(row)

    latex.append("\\bottomrule")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    return "\n".join(latex)

def generate_compact_table(metrics: Dict[str, Dict[str, float]]) -> str:
    """Generate a more compact table focusing on key results"""

    ops = ['memset', 'stzg', 'stgp', 'stp', 'stnp']
    op_names = {
        'memset': '\\texttt{memset}',
        'stzg': '\\texttt{STZG}',
        'stgp': '\\texttt{STGP}',
        'stp': '\\texttt{STP}',
        'stnp': '\\texttt{STNP}'
    }

    # Filter to operations that exist
    ops = [op for op in ops if op in metrics]

    latex = []
    latex.append("\\begin{table}[t]")
    latex.append("\\centering")
    latex.append("\\caption{Memory zeroing performance on Ampere Altra (32MB buffer)}")
    latex.append("\\label{tab:perf-compact}")
    latex.append("\\begin{tabular}{lrrr}")
    latex.append("\\toprule")
    latex.append("Operation & Cycles & IPC & Miss Rate (\\%) \\\\")
    latex.append("\\midrule")

    # Find best values for highlighting
    best_cycles = min([metrics[o].get('cycles', 1e99) for o in ops if o in metrics])
    best_ipc = max([metrics[o].get('IPC', 0) for o in ops if o in metrics])
    best_miss_rate = min([metrics[o].get('cache-miss-rate', 100) for o in ops if o in metrics])

    for op in ops:
        if op not in metrics:
            continue

        m = metrics[op]
        cycles = m.get('cycles', 0)
        ipc = m.get('IPC', 0)
        miss_rate = m.get('cache-miss-rate', 0)

        # Format cycles using G/M/K suffix with \, separator
        if cycles >= 1e9:
            cycles_str = f"{cycles/1e9:.2f}\\,G"
        elif cycles >= 1e6:
            cycles_str = f"{cycles/1e6:.0f}\\,M"
        else:
            cycles_str = f"{cycles:.0f}"

        # Bold the best values
        is_best_cycles = (cycles == best_cycles)
        is_best_ipc = (ipc == best_ipc)
        is_best_miss = (miss_rate == best_miss_rate)

        if is_best_cycles:
            cycles_str = f"\\textbf{{{cycles_str}}}"
        if is_best_ipc:
            ipc_str = f"\\textbf{{{ipc:.2f}}}"
        else:
            ipc_str = f"{ipc:.2f}"
        if is_best_miss:
            miss_str = f"\\textbf{{{miss_rate:.2f}}}"
        else:
            miss_str = f"{miss_rate:.2f}"

        row = f"{op_names[op]} & {cycles_str} & {ipc_str} & {miss_str} \\\\"
        latex.append(row)

    latex.append("\\bottomrule")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    return "\n".join(latex)

def main():
    parser = argparse.ArgumentParser(
        description='Generate LaTeX table from perf counter results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s results/mte/perf_ctrs.txt
  %(prog)s results/mte/perf_ctrs.txt --format color
  %(prog)s results/mte/perf_ctrs.txt --compact
  %(prog)s results/mte/perf_ctrs.txt --caption "My custom caption"
        """
    )

    parser.add_argument('input_file', help='Path to perf counter results file')
    parser.add_argument('--format', choices=['standard', 'color'], default='standard',
                       help='Format style (standard or color for best values)')
    parser.add_argument('--compact', action='store_true',
                       help='Generate compact table with key metrics only')
    parser.add_argument('--caption', help='Custom table caption')
    parser.add_argument('--label', help='Custom LaTeX label')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')

    args = parser.parse_args()

    try:
        # Parse input file
        results = parse_perf_results(args.input_file)

        if not results:
            print(f"Error: No data found in {args.input_file}", file=sys.stderr)
            sys.exit(1)

        # Calculate derived metrics
        metrics = calculate_derived_metrics(results)

        # Generate table
        if args.compact:
            latex = generate_compact_table(metrics)
        else:
            latex = generate_latex_table(metrics, args.format, args.caption, args.label)

        # Output
        if args.output:
            with open(args.output, 'w') as f:
                f.write(latex)
                f.write('\n')
            print(f"LaTeX table written to {args.output}")
        else:
            print(latex)

    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

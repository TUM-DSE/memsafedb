#!/usr/bin/env python3
"""Run DBMS benchmarks and collect results."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

from parsers import (
    parse_duckdb_output,
    parse_leveldb_output,
    parse_leveldb_bench_output,
    parse_redis_output,
    parse_sqlite_output,
    parse_mysql_output,
    parse_ladybug_output,
)

DBMS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = DBMS_DIR.parent
RESULTS_FILE = PROJECT_ROOT / "results" / "dbms_results.csv"

DATABASES = ['duckdb', 'leveldb', 'leveldb_motiv', 'redis', 'sqlite', 'mysql', 'ladybug']

# Mapping from database name to just target
DB_TO_TARGET = {
    'duckdb': 'run_duckdb',
    'leveldb': 'run_leveldb',
    'leveldb_motiv': 'run_leveldb_bench',
    'redis': 'run_redis',
    'sqlite': 'run_sqlite',
    'mysql': 'run_mysql',
    'ladybug': 'run_ladybug',
}

# Mapping from database name to parser function
DB_TO_PARSER = {
    'duckdb': parse_duckdb_output,
    'leveldb': parse_leveldb_output,
    'leveldb_motiv': parse_leveldb_bench_output,
    'redis': parse_redis_output,
    'sqlite': parse_sqlite_output,
    'mysql': parse_mysql_output,
    'ladybug': parse_ladybug_output,
}

CSV_FIELDNAMES = [
    'database', 'variant', 'benchmark', 'workload',
    'metric_name', 'metric_value', 'unit', 'repetition'
]


def run_benchmark(db: str, repetition: int) -> list[dict]:
    """Run benchmark for a database and return parsed results."""
    target = DB_TO_TARGET.get(db)
    if not target:
        print(f"Unknown database: {db}", file=sys.stderr)
        return []

    cmd = f"just dbms::{target}"
    print(f"  Running: {cmd}")

    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT,
    )

    if result.returncode != 0:
        print(f"  Warning: {db} benchmark exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}", file=sys.stderr)

    # Preserve stream ordering for parsers that rely on benchmark markers.
    combined_output = result.stdout or ""

    parser = DB_TO_PARSER.get(db)
    if not parser:
        print(f"No parser for database: {db}", file=sys.stderr)
        return []

    return list(parser(combined_output, repetition))


def main():
    parser = argparse.ArgumentParser(description='Run DBMS benchmarks and collect results.')
    parser.add_argument(
        '--db',
        default='all',
        help=f'Database to benchmark (all, {", ".join(DATABASES)})'
    )
    parser.add_argument(
        '--repetitions',
        type=int,
        default=1,
        help='Number of repetitions for each benchmark'
    )
    parser.add_argument(
        '--append',
        action='store_true',
        help='Append to existing results file instead of overwriting'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=RESULTS_FILE,
        help='Output CSV file path'
    )
    args = parser.parse_args()

    # Determine which databases to run
    if args.db == 'all':
        dbs = DATABASES
    elif args.db in DATABASES:
        dbs = [args.db]
    else:
        print(f"Unknown database: {args.db}", file=sys.stderr)
        print(f"Available: all, {', '.join(DATABASES)}", file=sys.stderr)
        sys.exit(1)

    # Ensure results directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Open output file
    mode = 'a' if args.append else 'w'
    write_header = not args.append or not args.output.exists()

    all_results = []

    for db in dbs:
        for rep in range(args.repetitions):
            print(f"Running {db} (rep {rep + 1}/{args.repetitions})...")
            results = run_benchmark(db, rep)
            all_results.extend(results)
            print(f"  Collected {len(results)} metrics")

    # Write results to CSV
    with open(args.output, mode, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(all_results)

    print(f"\nResults written to {args.output}")
    print(f"Total metrics collected: {len(all_results)}")


if __name__ == '__main__':
    main()

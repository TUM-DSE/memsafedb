#!/usr/bin/env python3
"""Output parsers for DBMS benchmarks."""
import re
from typing import Iterator


def parse_duckdb_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse DuckDB TPC-H output.

    Output format from run_duckdb: all release, all mte, all release-cold, all mte-cold:
    q1,1.234  (release warm)
    q2,2.345  (release warm)
    ...
    q22,0.163 (release warm)
    q1,1.456  (release-mte warm)
    q2,2.567  (release-mte warm)
    ...
    q22,0.124 (release-mte warm)
    q1,1.789  (release-cold)
    ...
    q22,0.999 (release-cold)
    q1,1.888  (release-mte-cold)
    ...
    q22,0.777 (release-mte-cold)
    """
    lines = [line.strip() for line in output.strip().split('\n') if line.strip()]

    # Filter lines to only those matching the query format
    query_lines = []
    for line in lines:
        if re.match(r'q\d+,[\d.]+', line):
            query_lines.append(line)

    # Split into four quarters: release, mte, release-cold, mte-cold
    if len(query_lines) < 4:
        return

    quarter = len(query_lines) // 4
    release_lines = query_lines[:quarter]
    mte_lines = query_lines[quarter:quarter*2]
    release_cold_lines = query_lines[quarter*2:quarter*3]
    mte_cold_lines = query_lines[quarter*3:]

    # Parse release queries (warm cache)
    for line in release_lines:
        match = re.match(r'(q\d+),([\d.]+)', line)
        if match:
            query = match.group(1)
            query_time = float(match.group(2))
            yield {
                'database': 'duckdb',
                'variant': 'release',
                'benchmark': 'tpch',
                'workload': query,
                'metric_name': 'query_time',
                'metric_value': query_time,
                'unit': 'seconds',
                'repetition': repetition,
            }

    # Parse MTE queries (warm cache)
    for line in mte_lines:
        match = re.match(r'(q\d+),([\d.]+)', line)
        if match:
            query = match.group(1)
            query_time = float(match.group(2))
            yield {
                'database': 'duckdb',
                'variant': 'release-mte',
                'benchmark': 'tpch',
                'workload': query,
                'metric_name': 'query_time',
                'metric_value': query_time,
                'unit': 'seconds',
                'repetition': repetition,
            }

    # Parse release queries (cold cache)
    for line in release_cold_lines:
        match = re.match(r'(q\d+),([\d.]+)', line)
        if match:
            query = match.group(1)
            query_time = float(match.group(2))
            yield {
                'database': 'duckdb',
                'variant': 'release-cold',
                'benchmark': 'tpch',
                'workload': query,
                'metric_name': 'query_time',
                'metric_value': query_time,
                'unit': 'seconds',
                'repetition': repetition,
            }

    # Parse MTE queries (cold cache)
    for line in mte_cold_lines:
        match = re.match(r'(q\d+),([\d.]+)', line)
        if match:
            query = match.group(1)
            query_time = float(match.group(2))
            yield {
                'database': 'duckdb',
                'variant': 'release-mte-cold',
                'benchmark': 'tpch',
                'workload': query,
                'metric_name': 'query_time',
                'metric_value': query_time,
                'unit': 'seconds',
                'repetition': repetition,
            }


def parse_ycsb_java_output(output: str, database: str, repetition: int) -> Iterator[dict]:
    """Parse Java YCSB output (used by Redis).

    YCSB output includes lines like:
    [OVERALL], Throughput(ops/sec), 12345.67
    [READ], AverageLatency(us), 123.45
    [READ], 95thPercentileLatency(us), 234
    [UPDATE], AverageLatency(us), 456.78

    The output alternates between variants (release, release-mte) and workloads (a-f).
    """
    # Split by workload markers
    workload_pattern = re.compile(r'=== Running workload([a-f]) \(([^)]*)\) ===')

    current_workload = None
    current_variant = None

    for line in output.split('\n'):
        line = line.strip()

        # Check for workload marker
        marker_match = workload_pattern.search(line)
        if marker_match:
            current_workload = marker_match.group(1)
            variant_str = marker_match.group(2)
            current_variant = 'release-mte' if '-mte' in variant_str or 'mte' in variant_str.lower() else 'release'
            continue

        # Parse YCSB metrics
        if line.startswith('[OVERALL], Throughput'):
            match = re.match(r'\[OVERALL\], Throughput\(ops/sec\), ([\d.]+)', line)
            if match and current_workload and current_variant:
                yield {
                    'database': database,
                    'variant': current_variant,
                    'benchmark': 'ycsb',
                    'workload': current_workload,
                    'metric_name': 'throughput',
                    'metric_value': float(match.group(1)),
                    'unit': 'ops/sec',
                    'repetition': repetition,
                }

        elif line.startswith('[READ], AverageLatency'):
            match = re.match(r'\[READ\], AverageLatency\(us\), ([\d.]+)', line)
            if match and current_workload and current_variant:
                yield {
                    'database': database,
                    'variant': current_variant,
                    'benchmark': 'ycsb',
                    'workload': current_workload,
                    'metric_name': 'read_latency_avg',
                    'metric_value': float(match.group(1)),
                    'unit': 'us',
                    'repetition': repetition,
                }

        elif line.startswith('[UPDATE], AverageLatency'):
            match = re.match(r'\[UPDATE\], AverageLatency\(us\), ([\d.]+)', line)
            if match and current_workload and current_variant:
                yield {
                    'database': database,
                    'variant': current_variant,
                    'benchmark': 'ycsb',
                    'workload': current_workload,
                    'metric_name': 'update_latency_avg',
                    'metric_value': float(match.group(1)),
                    'unit': 'us',
                    'repetition': repetition,
                }


def parse_redis_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse Redis YCSB output.

    Redis uses ycsb.sh which has standard YCSB output format.
    Runs in order: (release, workloads a-f), (mte, workloads a-f)
    """
    # Redis doesn't have explicit workload markers in the output,
    # need to track based on order
    workloads = ['a', 'b', 'c', 'd', 'e', 'f']
    variants = ['release', 'release-mte']

    # Split output into sections by looking for YCSB run markers
    # The pattern "[OVERALL]" marks start of results for each run
    sections = re.split(r'(?=\[OVERALL\])', output)
    sections = [s for s in sections if s.strip() and '[OVERALL]' in s]

    # Each variant runs load+run for each workload
    # So we have: 12 runs per variant (6 load + 6 run), and we only care about run phase
    # Actually looking at the just file: load then run for each workload
    # So order is: load_a, run_a, load_b, run_b, ... for release, then same for mte

    run_idx = 0
    for section in sections:
        # Determine which workload and variant based on index
        # 12 sections per variant (6 workloads x 2 phases)
        variant_idx = run_idx // 12
        within_variant_idx = run_idx % 12
        workload_idx = within_variant_idx // 2
        is_run_phase = within_variant_idx % 2 == 1

        if variant_idx < len(variants) and workload_idx < len(workloads):
            variant = variants[variant_idx]
            workload = workloads[workload_idx]

            # Only record run phase results
            if is_run_phase:
                for line in section.split('\n'):
                    line = line.strip()

                    if line.startswith('[OVERALL], Throughput'):
                        match = re.match(r'\[OVERALL\], Throughput\(ops/sec\), ([\d.]+)', line)
                        if match:
                            yield {
                                'database': 'redis',
                                'variant': variant,
                                'benchmark': 'ycsb',
                                'workload': workload,
                                'metric_name': 'throughput',
                                'metric_value': float(match.group(1)),
                                'unit': 'ops/sec',
                                'repetition': repetition,
                            }

                    elif line.startswith('[READ], AverageLatency'):
                        match = re.match(r'\[READ\], AverageLatency\(us\), ([\d.]+)', line)
                        if match:
                            yield {
                                'database': 'redis',
                                'variant': variant,
                                'benchmark': 'ycsb',
                                'workload': workload,
                                'metric_name': 'read_latency_avg',
                                'metric_value': float(match.group(1)),
                                'unit': 'us',
                                'repetition': repetition,
                            }

        run_idx += 1


def parse_leveldb_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse LevelDB YCSB-cpp output.

    YCSB-cpp output format:
    === Running workloada (release) ===
    ...
    Run throughput(ops/sec): 12345.67
    ...
    === Running workloada (-mte) ===
    ...
    Run throughput(ops/sec): 11234.56

    The workload marker shows (release) or (-mte) based on the suffix variable.
    """
    # Pattern for workload markers: === Running workloadX (variant) ===
    workload_pattern = re.compile(r'=== Running workload([a-f]) \(([^)]*)\) ===')

    # Pattern for throughput: Run throughput(ops/sec): VALUE
    throughput_pattern = re.compile(r'Run throughput\(ops/sec\):\s+([\d.]+)')

    # Pattern for latency stats: [READ: Count=N Max=X Min=Y Avg=Z]
    read_stats_pattern = re.compile(r'\[READ:\s+Count=(\d+)\s+Max=([\d.]+)\s+Min=([\d.]+)\s+Avg=([\d.]+)')
    update_stats_pattern = re.compile(r'\[UPDATE:\s+Count=(\d+)\s+Max=([\d.]+)\s+Min=([\d.]+)\s+Avg=([\d.]+)')

    current_workload = None
    current_variant = None

    for line in output.split('\n'):
        line = line.strip()

        # Check for workload marker
        marker_match = workload_pattern.search(line)
        if marker_match:
            current_workload = marker_match.group(1)
            variant_str = marker_match.group(2)
            # variant_str is "release" or "-mte"
            if variant_str == '-mte' or 'mte' in variant_str.lower():
                current_variant = 'release-mte'
            else:
                current_variant = 'release'
            continue

        if current_workload is None or current_variant is None:
            continue

        # Parse throughput
        throughput_match = throughput_pattern.search(line)
        if throughput_match:
            yield {
                'database': 'leveldb',
                'variant': current_variant,
                'benchmark': 'ycsb',
                'workload': current_workload,
                'metric_name': 'throughput',
                'metric_value': float(throughput_match.group(1)),
                'unit': 'ops/sec',
                'repetition': repetition,
            }

        # Parse READ latency stats
        read_match = read_stats_pattern.search(line)
        if read_match:
            yield {
                'database': 'leveldb',
                'variant': current_variant,
                'benchmark': 'ycsb',
                'workload': current_workload,
                'metric_name': 'read_latency_avg',
                'metric_value': float(read_match.group(4)),
                'unit': 'us',
                'repetition': repetition,
            }

        # Parse UPDATE latency stats
        update_match = update_stats_pattern.search(line)
        if update_match:
            yield {
                'database': 'leveldb',
                'variant': current_variant,
                'benchmark': 'ycsb',
                'workload': current_workload,
                'metric_name': 'update_latency_avg',
                'metric_value': float(update_match.group(4)),
                'unit': 'us',
                'repetition': repetition,
            }


def parse_sqlite_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse SQLite TPC-C (py-tpcc) output.

    py-tpcc outputs a summary table with:
    Execution Results after 60 seconds
    ...
      TOTAL           39579                 58.409
    """
    duration_pattern = re.compile(r'Execution Results after\s+(\d+)\s+seconds', re.IGNORECASE)
    total_pattern = re.compile(r'^\s*TOTAL\s+(\d+)\b', re.IGNORECASE)
    variants = ['release', 'release-mte']

    results = []
    current_duration = None

    for line in output.split('\n'):
        line = line.strip()

        duration_match = duration_pattern.search(line)
        if duration_match:
            current_duration = int(duration_match.group(1))
            continue

        total_match = total_pattern.match(line)
        if total_match and current_duration:
            total_txn = int(total_match.group(1))
            results.append((current_duration, total_txn))
            current_duration = None

    for var_idx, variant in enumerate(variants):
        if var_idx < len(results):
            duration, total_txn = results[var_idx]
            tps_value = total_txn / duration if duration > 0 else 0.0
            yield {
                'database': 'sqlite',
                'variant': variant,
                'benchmark': 'tpcc',
                'workload': 'tpcc',
                'metric_name': 'tps',
                'metric_value': float(tps_value),
                'unit': 'txn/sec',
                'repetition': repetition,
            }


def parse_mysql_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse MySQL sysbench output.

    Sysbench outputs lines like:
        transactions:                        10000  (166.50 per sec.)
        queries:                             200000 (3330.00 per sec.)
        Latency (ms):
             min:                                  1.23
             avg:                                  4.56
             max:                                  78.90
             95th percentile:                      12.34
    """
    tps_pattern = re.compile(r'transactions:\s+\d+\s+\(([\d.]+) per sec\.\)')
    qps_pattern = re.compile(r'queries:\s+\d+\s+\(([\d.]+) per sec\.\)')
    lat_avg_pattern = re.compile(r'^\s*avg:\s+([\d.]+)', re.IGNORECASE)
    lat_95_pattern = re.compile(r'^\s*95th percentile:\s+([\d.]+)', re.IGNORECASE)
    lat_99_pattern = re.compile(r'^\s*99th percentile:\s+([\d.]+)', re.IGNORECASE)
    marker_pattern = re.compile(r'^=== Running mysql \(([^)]+)\) ===$', re.IGNORECASE)

    variants = ['release', 'release-mte']

    # Prefer explicit run markers if present.
    runs = []
    current_label = None
    current_lines = []

    for line in output.split('\n'):
        marker_match = marker_pattern.match(line.strip())
        if marker_match:
            if current_lines:
                runs.append((current_label, '\n'.join(current_lines)))
                current_lines = []
            current_label = marker_match.group(1).strip().lower()
            continue
        current_lines.append(line)

    if current_lines:
        runs.append((current_label, '\n'.join(current_lines)))

    if not any(label for label, _ in runs):
        # Fallback: split output by sysbench runs (look for "SQL statistics:" marker)
        chunks = re.split(r'SQL statistics:', output)
        chunks = [c for c in chunks if c.strip()]
        runs = [(None, chunk) for chunk in chunks]

    for var_idx, (label, run_output) in enumerate(runs):
        if var_idx >= len(variants):
            break

        variant = variants[var_idx]
        if label:
            if 'mte' in label:
                variant = 'release-mte'
            elif 'release' in label:
                variant = 'release'

        tps_match = tps_pattern.search(run_output)
        if tps_match:
            yield {
                'database': 'mysql',
                'variant': variant,
                'benchmark': 'sysbench',
                'workload': 'oltp_read_write',
                'metric_name': 'tps',
                'metric_value': float(tps_match.group(1)),
                'unit': 'txn/sec',
                'repetition': repetition,
            }

        qps_match = qps_pattern.search(run_output)
        if qps_match:
            yield {
                'database': 'mysql',
                'variant': variant,
                'benchmark': 'sysbench',
                'workload': 'oltp_read_write',
                'metric_name': 'qps',
                'metric_value': float(qps_match.group(1)),
                'unit': 'queries/sec',
                'repetition': repetition,
            }

        in_latency = False
        for line in run_output.split('\n'):
            line = line.rstrip()
            if line.strip().startswith('Latency (ms):'):
                in_latency = True
                continue
            if in_latency and (not line.strip() or line.strip().startswith('Threads fairness:')):
                in_latency = False
                continue
            if not in_latency:
                continue

            lat_avg_match = lat_avg_pattern.match(line)
            if lat_avg_match:
                yield {
                    'database': 'mysql',
                    'variant': variant,
                    'benchmark': 'sysbench',
                    'workload': 'oltp_read_write',
                    'metric_name': 'latency_avg',
                    'metric_value': float(lat_avg_match.group(1)),
                    'unit': 'ms',
                    'repetition': repetition,
                }
                continue

            lat_95_match = lat_95_pattern.match(line)
            if lat_95_match:
                yield {
                    'database': 'mysql',
                    'variant': variant,
                    'benchmark': 'sysbench',
                    'workload': 'oltp_read_write',
                    'metric_name': 'latency_p95',
                    'metric_value': float(lat_95_match.group(1)),
                    'unit': 'ms',
                    'repetition': repetition,
                }
                continue

            lat_99_match = lat_99_pattern.match(line)
            if lat_99_match:
                yield {
                    'database': 'mysql',
                    'variant': variant,
                    'benchmark': 'sysbench',
                    'workload': 'oltp_read_write',
                    'metric_name': 'latency_p99',
                    'metric_value': float(lat_99_match.group(1)),
                    'unit': 'ms',
                    'repetition': repetition,
                }


def parse_ladybug_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse Ladybug LSQB benchmark output.

    The benchmark_runner.py logs per-query lines like:
    INFO:root:Running query 1
    INFO:root:Execution time (s): 1.9726
    """
    query_pattern = re.compile(r'Running query\s+(\d+)', re.IGNORECASE)
    time_pattern = re.compile(r'Execution time \(s\):\s+([\d.]+)', re.IGNORECASE)
    variants = ['release', 'release-mte']

    run_idx = 0
    current_query = None
    seen_queries = set()

    for line in output.split('\n'):
        line = line.strip()

        query_match = query_pattern.search(line)
        if query_match:
            query_num = int(query_match.group(1))
            if query_num == 1 and seen_queries:
                run_idx += 1
                seen_queries = set()
            current_query = query_num
            seen_queries.add(query_num)
            continue

        time_match = time_pattern.search(line)
        if time_match and current_query is not None and run_idx < len(variants):
            query_time = float(time_match.group(1))
            variant = variants[run_idx]

            yield {
                'database': 'ladybug',
                'variant': variant,
                'benchmark': 'lsqb',
                'workload': f'q{current_query}',
                'metric_name': 'query_time',
                'metric_value': query_time,
                'unit': 'seconds',
                'repetition': repetition,
            }

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

    Redis uses ycsb.sh; run_redis emits explicit separators per workload/phase.
    """
    marker_pattern = re.compile(
        r'REDIS_YCSB\s+workload=([a-f])\s+variant=([a-z0-9-]+)\s+phase=(load|run)',
        re.IGNORECASE,
    )
    throughput_pattern = re.compile(r'operations;\s*([0-9.]+)\s+current ops/sec;')

    markers = list(marker_pattern.finditer(output))
    for idx, marker in enumerate(markers):
        workload = marker.group(1).lower()
        variant = marker.group(2).lower()
        phase = marker.group(3).lower()
        if phase != "run":
            continue

        start = marker.end()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(output)
        segment = output[start:end]
        matches = throughput_pattern.findall(segment)
        if not matches:
            continue

        yield {
            'database': 'redis',
            'variant': variant,
            'benchmark': 'ycsb',
            'workload': workload,
            'metric_name': 'throughput',
            'metric_value': float(matches[-1]),
            'unit': 'ops/sec',
            'repetition': repetition,
        }

def parse_leveldb_bench_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse LevelDB db_bench benchmark output.
    
    Output format includes markers like:
    === Running threads 1 - MTE ===
    fillseq      :       1.234 micros/op;   12.3 MB/s
    ...
    === Running threads 4 - Dynamic ===
    ...
    """
    marker_pattern = re.compile(r'^===\s+Running threads\s+(\d+)\s+-\s+([a-zA-Z0-9_-]+)\s+===$', re.IGNORECASE)
    # db_bench output line: "fillseq      :       3.013 micros/op;  374.9 MB/s"
    data_pattern = re.compile(r'^([a-zA-Z0-9_]+)\s*:\s+([0-9.]+)\s+micros/op;\s+([0-9.]+)\s+MB/s')
    
    stat_avg_pattern = re.compile(r'Average:\s+([0-9.]+)')
    stat_std_pattern = re.compile(r'StdDev:\s+([0-9.]+)')
    stat_min_pattern = re.compile(r'Min:\s+([0-9.]+)')
    stat_med_pattern = re.compile(r'Median:\s+([0-9.]+)')
    stat_max_pattern = re.compile(r'Max:\s+([0-9.]+)')

    current_threads = 1
    current_variant = None
    
    # Track the last benchmark seen to attach stats to it
    last_benchmark_info = None

    lines = output.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Check for marker
        marker_match = marker_pattern.match(line)
        if marker_match:
            current_threads = int(marker_match.group(1))
            current_variant_str = marker_match.group(2).lower()
            
            # Map simplified variant names to full names if needed
            # mte -> release-mte
            # dynamic -> release-dynamic or baseline-dynamic? 
            # In dbms.just: release-mte, release-dynamic, release-asan, release-static, release-cheri
            # The markers are: MTE, Dynamic, ASan, Static, Cheri
            if current_variant_str == "mte":
                current_variant = "release-mte"
            elif current_variant_str == "dynamic":
                current_variant = "release-dynamic"
            elif current_variant_str == "asan":
                current_variant = "release-asan"
            elif current_variant_str == "static":
                current_variant = "release-static"
            elif current_variant_str == "cheri":
                current_variant = "release-cheri"
            else:
                current_variant = f"release-{current_variant_str}"
            continue

        # Check for data line
        data_match = data_pattern.match(line)
        if data_match and current_variant:
            benchmark = data_match.group(1)
            micros_op = float(data_match.group(2))
            throughput_mb = float(data_match.group(3))
            
            # Yield Throughput
            yield {
                'database': 'leveldb_motiv',
                'variant': current_variant,
                'benchmark': 'db_bench',
                'workload': f"{benchmark}_t{current_threads}",
                'metric_name': 'throughput',
                'metric_value': throughput_mb,
                'unit': 'MB/s',
                'repetition': repetition,
            }
            
            # Yield Latency (micros/op) as avg_latency (default if no detailed stats)
            yield {
                'database': 'leveldb_motiv',
                'variant': current_variant,
                'benchmark': 'db_bench',
                'workload': f"{benchmark}_t{current_threads}",
                'metric_name': 'latency_avg',
                'metric_value': micros_op,
                'unit': 'us',
                'repetition': repetition,
            }
            
            last_benchmark_info = {
                'variant': current_variant,
                'workload': f"{benchmark}_t{current_threads}",
            }
            continue

        # Check for detailed stats if we have a last benchmark
        if last_benchmark_info:
            if "Average:" in line:
                avg_m = stat_avg_pattern.search(line)
                std_m = stat_std_pattern.search(line)
                if avg_m:
                     # This might overwrite the micros/op value if they differ, but usually they are similar.
                     # micros/op is often the mean.
                     pass
                if std_m:
                    yield {
                        'database': 'leveldb_motiv',
                        'variant': last_benchmark_info['variant'],
                        'benchmark': 'db_bench',
                        'workload': last_benchmark_info['workload'],
                        'metric_name': 'latency_stddev',
                        'metric_value': float(std_m.group(1)),
                        'unit': 'us',
                        'repetition': repetition,
                    }
            elif "Min:" in line:
                min_m = stat_min_pattern.search(line)
                med_m = stat_med_pattern.search(line)
                max_m = stat_max_pattern.search(line)
                
                if min_m:
                    yield {
                        'database': 'leveldb_motiv',
                        'variant': last_benchmark_info['variant'],
                        'benchmark': 'db_bench',
                        'workload': last_benchmark_info['workload'],
                        'metric_name': 'latency_min',
                        'metric_value': float(min_m.group(1)),
                        'unit': 'us',
                        'repetition': repetition,
                    }
                if med_m:
                    yield {
                        'database': 'leveldb_motiv',
                        'variant': last_benchmark_info['variant'],
                        'benchmark': 'db_bench',
                        'workload': last_benchmark_info['workload'],
                        'metric_name': 'latency_median',
                        'metric_value': float(med_m.group(1)),
                        'unit': 'us',
                        'repetition': repetition,
                    }
                if max_m:
                    yield {
                        'database': 'leveldb_motiv',
                        'variant': last_benchmark_info['variant'],
                        'benchmark': 'db_bench',
                        'workload': last_benchmark_info['workload'],
                        'metric_name': 'latency_max',
                        'metric_value': float(max_m.group(1)),
                        'unit': 'us',
                        'repetition': repetition,
                    }


def parse_leveldb_output(output: str, repetition: int) -> Iterator[dict]:
    """Parse LevelDB YCSB-cpp output.

    Output format from run_leveldb:
    === Running workload(a-f) - threads (N) - (suffix) ===
    ...
    [READ: Count=... Max=... Min=... Avg=...] [UPDATE: ...]
    ...
    Run throughput(ops/sec): 12345.67
    """
    marker_pattern = re.compile(r'^===\s+Running workload([a-f])\s+-\s+threads:\s+(\d+)\s+-\s+([a-zA-Z0-9_-]+)\s+===$', re.IGNORECASE)
    throughput_pattern = re.compile(r'Run throughput\(ops/sec\):\s+([\d.]+)')
    op_pattern = re.compile(r'\[([A-Z]+): Count=(\d+) Max=[0-9.]+ Min=[0-9.]+ Avg=([0-9.]+)\]')
    
    lines = output.split('\n')
    
    current_workload = None
    current_threads = 1
    current_variant = None
    
    # Store lines for current block to search backwards for stats
    current_block_lines = []

    for line in lines:
        line = line.strip()
        
        # Check for start of new block
        marker_match = marker_pattern.match(line)
        if marker_match:
            # If we were in a block, we're detecting a new one, but we process within the loop
            # Reset state for new block
            current_workload = marker_match.group(1)
            current_threads = int(marker_match.group(2))
            current_variant_str = marker_match.group(3).lower()
            
            if current_variant_str == "mte":
                current_variant = "release-mte"
            elif current_variant_str == "dynamic":
                current_variant = "release-dynamic"
            elif current_variant_str == "asan":
                current_variant = "release-asan"
            elif current_variant_str == "static":
                current_variant = "release-static"
            elif current_variant_str == "cheri":
                current_variant = "release-cheri"
            else:
                current_variant = f"release-{current_variant_str}"
            
            current_block_lines = []
            continue

        current_block_lines.append(line)

        # check for throughput line which usually signifies end of run phase output
        throughput_match = throughput_pattern.search(line)
        if throughput_match and current_variant and current_workload:
            throughput = float(throughput_match.group(1))
            
            yield {
                'database': 'leveldb',
                'variant': current_variant,
                'benchmark': 'ycsb',
                'workload': f"{current_workload}_t{current_threads}",
                'metric_name': 'throughput',
                'metric_value': throughput,
                'unit': 'ops/sec',
                'repetition': repetition,
            }
            
            # Look backwards for status line to calculate average latency
            last_status_line = None
            # Search backwards in current_block_lines
            for j in range(len(current_block_lines) - 2, -1, -1):
                prev = current_block_lines[j].strip()
                if "operations;" in prev and "[" in prev and "]" in prev:
                    last_status_line = prev
                    break
            
            if last_status_line:
                ops = op_pattern.findall(last_status_line)
                total_count = 0
                total_weighted_sum = 0.0
                
                for op_name, count_str, avg_str in ops:
                    count = int(count_str)
                    avg = float(avg_str)
                    total_count += count
                    total_weighted_sum += (count * avg)
                
                if total_count > 0:
                    avg_latency = total_weighted_sum / total_count
                    yield {
                        'database': 'leveldb',
                        'variant': current_variant,
                        'benchmark': 'ycsb',
                        'workload': f"{current_workload}_t{current_threads}",
                        'metric_name': 'latency_avg',
                        'metric_value': f"{avg_latency:.3f}",
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
    variants = ['release-dynamic', 'release-mte', 'release-static', 'release-cheri']

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

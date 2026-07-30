#!/usr/bin/env python3
"""Run DBMS benchmarks and collect results (sweep-driven)."""
import argparse
import csv
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

import ycsb_runner
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
RESULTS_FILE = PROJECT_ROOT / "results" / "dbms_sweep_results.csv"
LOG_DIR = PROJECT_ROOT / "results" / "dbms"

DATABASES = ['duckdb', 'leveldb', 'leveldb_motiv', 'redis', 'sqlite', 'mysql', 'ladybug']

DB_TO_TARGET = {
    'duckdb': 'run_duckdb',
    'leveldb': 'run_leveldb',
    'leveldb_motiv': 'run_leveldb_bench',
    'redis': 'run_redis',
    'sqlite': 'run_sqlite',
    'mysql': 'run_mysql',
    'ladybug': 'run_ladybug',
}

DB_TO_PARSER = {
    'duckdb': parse_duckdb_output,
    'leveldb': parse_leveldb_output,
    'leveldb_motiv': parse_leveldb_bench_output,
    'redis': parse_redis_output,
    'sqlite': parse_sqlite_output,
    'mysql': parse_mysql_output,
    'ladybug': parse_ladybug_output,
}

BASE_FIELDNAMES = [
    'database', 'variant', 'benchmark', 'workload',
    'metric_name', 'metric_value', 'unit', 'repetition',
]
SWEEP_FIELDNAMES = ['persistence', 'working_set', 'threads']
CSV_FIELDNAMES = BASE_FIELDNAMES + SWEEP_FIELDNAMES

# Two 1-D sweeps around a pivot; thread lists are per-host (ace=4 cores, eliza=192).
ELIZA_THREADS, ELIZA_TPIVOT = [1, 8, 64], 64
ACE_THREADS, ACE_TPIVOT = [1, 2, 4], 4
# redis-server is single-threaded: throughput saturates immediately, so we fix
# concurrency (no sweep) and sweep only the working set, using smaller points
# than the others (10M is too heavy for a single-threaded KV store). One client:
# the CHERI build wedges under concurrent load (server stops answering), while
# a single client runs all six workloads cleanly.
REDIS_THREADS, REDIS_TPIVOT = [1], 1
REDIS_WS_VALUES, REDIS_WS_PIVOT = [10_000, 100_000, 1_000_000], 1_000_000
LEVELDB_OP_COUNT = 1_000_000
LEVELDB_WS_PIVOT = 1_000_000
REDIS_OP_COUNT = 100_000
SQLITE_DURATION = 60


def _eliza(recipe):
    return {'name': 'eliza', 'recipe': recipe, 'threads': ELIZA_THREADS, 'thread_pivot': ELIZA_TPIVOT}


def _ace(recipe):
    return {'name': 'ace', 'recipe': recipe, 'threads': ACE_THREADS, 'thread_pivot': ACE_TPIVOT}


# LevelDB and Redis run directly from Python (ycsb_runner) with load reuse, not
# via just recipes: load once per (working-set, persistence), reuse across thread
# counts and read-only workloads (a/b/c/f); insert workloads (d/e) reload.
# ace variants carry their nix devshell; eliza variants are bare strings.
YCSB_SPECS = {
    'leveldb': {
        'op_count': LEVELDB_OP_COUNT,
        'ws_values': [100_000, 1_000_000, 10_000_000], 'ws_pivot': LEVELDB_WS_PIVOT,
        'persistence': ['memory', 'disk'],
        'hosts': [
            {'name': 'eliza', 'variants': ['dynamic', 'mte'],
             'threads': ELIZA_THREADS, 'thread_pivot': ELIZA_TPIVOT},
            {'name': 'ace', 'variants': [('static', 'ace-aarch64'), ('cheri', 'ace-cheri')],
             'threads': ACE_THREADS, 'thread_pivot': ACE_TPIVOT, 'ws_values': [100_000, 1_000_000]},
        ],
    },
    'redis': {
        'op_count': REDIS_OP_COUNT,
        'ws_values': REDIS_WS_VALUES, 'ws_pivot': REDIS_WS_PIVOT,
        'persistence': [None],
        'hosts': [
            {'name': 'eliza', 'variants': ['dynamic', 'mte'],
             'threads': REDIS_THREADS, 'thread_pivot': REDIS_TPIVOT},
            {'name': 'ace', 'variants': [('static', 'ace-aarch64'), ('cheri', 'ace-cheri')],
             'threads': REDIS_THREADS, 'thread_pivot': REDIS_TPIVOT},
        ],
    },
}


# recipe positional args are host-recipe specific; make_args(ws, threads, persistence) matches each signature.
SWEEP_SPECS = {
    'duckdb': {
        'parser': parse_duckdb_output,
        'hosts': [_eliza('run_duckdb')],
        'ws_values': [1, 10, 100], 'ws_pivot': 10,
        'make_args': lambda ws, t, p: [ws, t, 'false'],
    },
    'sqlite': {
        'parser': parse_sqlite_output,
        # SQLite is single-writer, so multi-client TPC-C exits immediately without
        # producing a result; only the single-client working-set sweep is run.
        'hosts': [{**_eliza('run_sqlite_eliza'), 'threads': [1], 'thread_pivot': 1},
                  {**_ace('run_sqlite_ace_remote'), 'threads': [1], 'thread_pivot': 1}],
        'ws_values': [1, 10, 50], 'ws_pivot': 10,
        'make_args': lambda ws, t, p: [ws, SQLITE_DURATION, t, 'false'],
    },
    'mysql': {
        'parser': parse_mysql_output,
        'hosts': [_eliza('run_mysql')],
        'ws_values': [10_000, 1_000_000, 10_000_000], 'ws_pivot': 1_000_000,
        'make_args': lambda ws, t, p: [t, ws, 'false'],
    },
    'ladybug': {
        'parser': parse_ladybug_output,
        # no ldbc-sf1 query set exists in benchmark/queries, so SF1 yields no metrics
        'hosts': [_eliza('run_ladybug_eliza'),
                  {**_ace('run_ladybug_ace_remote'), 'ws_values': [10]}],
        'ws_values': [10, 100], 'ws_pivot': 10,
        'make_args': lambda ws, t, p: [t, ws, 'false'],
    },
}


def build_sweep_runs(db: str, spec: dict) -> list[dict]:
    runs: list[dict] = []
    seen: set[tuple] = set()
    persistences = spec.get('persistence', [None])

    def add(host, threads, working_set, persistence):
        key = (host['recipe'], persistence, working_set, threads)
        if key in seen:
            return
        seen.add(key)
        plabel = f"_{persistence}" if persistence is not None else ""
        runs.append({
            'recipe': host['recipe'],
            'host': host['name'],
            'args': spec['make_args'](working_set, threads, persistence),
            'parser': spec['parser'],
            'tags': {
                'persistence': persistence if persistence is not None else 'na',
                'working_set': working_set,
                'threads': threads,
            },
            'label': f"{db}_{host['name']}_ws{working_set}_t{threads}{plabel}",
        })

    for persistence in persistences:
        for host in spec['hosts']:
            ws_values = host.get('ws_values', spec['ws_values'])
            ws_pivot = host.get('ws_pivot', spec['ws_pivot'])
            for threads in host['threads']:
                add(host, threads, ws_pivot, persistence)
            for working_set in ws_values:
                add(host, host['thread_pivot'], working_set, persistence)
    return runs


def build_baseline_run(db: str) -> dict:
    target = DB_TO_TARGET[db]
    if db == 'leveldb':
        args = [LEVELDB_WS_PIVOT, LEVELDB_OP_COUNT, 1, 'memory', 'false']
        tags = {'persistence': 'memory', 'working_set': LEVELDB_WS_PIVOT, 'threads': 1}
    else:
        args = []
        tags = {'persistence': 'baseline', 'working_set': 'baseline', 'threads': 'baseline'}
    return {'recipe': target, 'host': 'both', 'args': args, 'parser': DB_TO_PARSER[db],
            'tags': tags, 'label': db}


def build_ycsb_runs(db: str, spec: dict) -> list[dict]:
    """One run per (host, working-set, persistence); each loads once and reuses
    across thread counts + read-only workloads. thread_set is the full thread
    list at the pivot working-set (thread sweep) and just the pivot elsewhere."""
    runs: list[dict] = []
    for persistence in spec['persistence']:
        for host in spec['hosts']:
            ws_values = host.get('ws_values', spec['ws_values'])
            for ws in ws_values:
                thread_set = sorted(host['threads']) if ws == spec['ws_pivot'] else [host['thread_pivot']]
                plabel = f"_{persistence}" if persistence is not None else ""
                runs.append({
                    'host': host['name'],
                    'persistence': persistence,
                    'label': f"{db}_{host['name']}_ws{ws}{plabel}",
                    'py_exec': ycsb_runner.make_exec(db, host, ws, persistence, thread_set, spec['op_count']),
                })
    return runs


def build_runs(db: str, sweep: str) -> list[dict]:
    if sweep == 'full' and db in YCSB_SPECS:
        return build_ycsb_runs(db, YCSB_SPECS[db])
    if sweep == 'full' and db in SWEEP_SPECS:
        return build_sweep_runs(db, SWEEP_SPECS[db])
    return [build_baseline_run(db)]


# Live CLI panel: redraws a fixed status block in place on the controlling
# terminal. Detail lines go to LOG_FH so the panel stays clean.
LIVE = False
LOG_FH = None
_tty = None
_panel_lines = 0


def log_detail(msg: str):
    if LOG_FH:
        LOG_FH.write(msg + "\n")
        LOG_FH.flush()
    if not LIVE:
        print(msg, flush=True)


def render_panel(block: str):
    global _tty, _panel_lines
    if not LIVE:
        return
    if _tty is None:
        try:
            _tty = open('/dev/tty', 'w')
        except OSError:
            _tty = False
    if not _tty:
        return
    try:
        if _panel_lines:
            _tty.write(f"\x1b[{_panel_lines}A")  # cursor up
        _tty.write("\x1b[0J")  # clear to end of screen
        _tty.write(block)
        _tty.flush()
    except OSError:
        _tty = False
        return
    _panel_lines = block.count("\n")


def write_status(path: Path, done: int, total: int, t_start: float, current: dict,
                 last=None, warnings=0):
    elapsed = time.monotonic() - t_start
    rate = elapsed / done if done else 0.0
    eta = rate * (total - done)
    block = "\n".join([
        f"progress: {done}/{total} config points ({100 * done / total:.0f}%)",
        f"elapsed:  {elapsed / 60:.1f} min",
        f"eta:      {eta / 60:.1f} min (naive, assumes uniform points)",
        f"warnings: {warnings}",
        f"eliza:    {current.get('eliza', '-')}",
        f"ace:      {current.get('ace', '-')}",
        f"last:     {last or '-'}",
        f"updated:  {time.strftime('%Y-%m-%d %H:%M:%S')}",
    ]) + "\n"
    path.write_text(block)
    render_panel(block)


def execute_run(run: dict, repetition: int) -> tuple[list[dict], float, bool]:
    if 'py_exec' in run:   # LevelDB/Redis: Python-driven load-reuse; rows are fully tagged
        log_detail(f"  [{run['label']}] rep {repetition}: (python ycsb, load-reuse)")
        t0 = time.monotonic()
        rows, ok, output = run['py_exec'](repetition)
        elapsed = time.monotonic() - t0
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / f"{run['label']}_rep{repetition}.txt", "w") as f:
            f.write(output)
        if not ok:
            log_detail(f"  Warning: {run['label']} incomplete (missing throughput rows)")
        log_detail(f"    -> {len(rows)} metrics in {elapsed:.1f}s")
        return rows, elapsed, ok

    args_str = " ".join(shlex.quote(str(a)) for a in run['args'])
    cmd = f"just dbms::{run['recipe']}" + (f" {args_str}" if args_str else "")
    log_detail(f"  [{run['label']}] rep {repetition}: {cmd}")

    t0 = time.monotonic()
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=PROJECT_ROOT,
    )
    elapsed = time.monotonic() - t0
    ok = result.returncode == 0
    if not ok:
        log_detail(f"  Warning: {run['label']} exited with code {result.returncode}")

    output = result.stdout or ""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"{run['label']}_rep{repetition}.txt", "w") as f:
        f.write(output)

    rows = list(run['parser'](output, repetition))
    for row in rows:
        row.update(run['tags'])
    log_detail(f"    -> {len(rows)} metrics in {elapsed:.1f}s")
    return rows, elapsed, ok


# ace runs over `ssh ace "..."` without a PTY, so a local Ctrl-C never reaches
# the remote process tree. On abort we ssh back in and SIGKILL them by name.
ACE_BENCH_PATTERNS = ("run_sqlite_ace|run_ladybug_ace|run_leveldb_local|run_redis_local|"
                      "ladybug|pytpcc|db_bench|ycsb|sysbench|redis-server|redis-cli")


def cleanup_ace():
    try:
        subprocess.run(["ssh", "ace", f"pkill -9 -f '{ACE_BENCH_PATTERNS}' 2>/dev/null; true"],
                       timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='Run DBMS benchmarks and collect results.')
    parser.add_argument('--db', default='all',
                        help=f'Database to benchmark (all, {", ".join(DATABASES)})')
    parser.add_argument('--repetitions', type=int, default=3,
                        help='Number of repetitions for each benchmark')
    parser.add_argument('--sweep', choices=['full', 'none'], default='full',
                        help="'full' expands the sweep matrix; 'none' runs one baseline point per DB")
    parser.add_argument('--append', action='store_true',
                        help='Append to existing results file instead of overwriting')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print the planned invocations without running anything')
    parser.add_argument('--host', choices=['eliza', 'ace'], default=None,
                        help='Only run config points for this host (e.g. to redo one '
                             'side without repeating the other)')
    parser.add_argument('--persistence', choices=['memory', 'disk'], default=None,
                        help='Only run YCSB config points with this persistence mode '
                             '(e.g. redo the disk sweep without repeating in-memory)')
    parser.add_argument('--sequential', action='store_true',
                        help='Run eliza and ace queues sequentially instead of concurrently')
    parser.add_argument('--no-live', action='store_true',
                        help='Disable the in-place CLI status panel (stream detail lines instead)')
    parser.add_argument('--log', type=Path, default=None,
                        help='Detail log file (default: <output>.log)')
    parser.add_argument('--output', type=Path, default=RESULTS_FILE, help='Output CSV file path')
    args = parser.parse_args()

    if args.db == 'all':
        dbs = DATABASES
    elif args.db in DATABASES:
        dbs = [args.db]
    else:
        print(f"Unknown database: {args.db}", file=sys.stderr)
        print(f"Available: all, {', '.join(DATABASES)}", file=sys.stderr)
        sys.exit(1)

    plan = [(db, build_runs(db, args.sweep)) for db in dbs]

    if args.host:
        plan = [(db, [r for r in runs if r.get('host') == args.host]) for db, runs in plan]
        plan = [(db, runs) for db, runs in plan if runs]
        if not plan:
            print(f"No config points for host {args.host}", file=sys.stderr)
            sys.exit(1)

    if args.persistence:
        plan = [(db, [r for r in runs if r.get('persistence') == args.persistence])
                for db, runs in plan]
        plan = [(db, runs) for db, runs in plan if runs]
        if not plan:
            print(f"No config points with persistence {args.persistence}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        total = 0
        for db, runs in plan:
            print(f"\n# {db}: {len(runs)} config point(s) × {args.repetitions} rep(s)")
            for run in runs:
                if 'py_exec' in run:
                    invocation = f"[{run['host']}] python ycsb load-reuse"
                else:
                    args_str = " ".join(shlex.quote(str(a)) for a in run['args'])
                    invocation = f"just dbms::{run['recipe']} {args_str}"
                print(f"  {run['label']:<44} {invocation}".rstrip())
                total += 1
        print(f"\nTotal: {total} config points, {total * args.repetitions} invocations")
        return

    # Split into per-host queues: eliza-local recipes and ace-ssh recipes run on
    # different machines, so the two queues execute concurrently (each internally
    # sequential). 'both' (baseline combined recipes) go on the eliza queue.
    queues = {'eliza': [], 'ace': []}
    for db, runs in plan:
        for rep in range(args.repetitions):
            for run in runs:
                key = 'ace' if run.get('host') == 'ace' else 'eliza'
                queues[key].append((rep, run))

    global LIVE, LOG_FH, _tty
    args.output.parent.mkdir(parents=True, exist_ok=True)
    LOG_FH = open(args.log or args.output.with_suffix('.log'), 'w')
    if not args.no_live:
        try:
            _tty = open('/dev/tty', 'w')
            LIVE = True
        except OSError:
            _tty = False

    mode = 'a' if args.append else 'w'
    write_header = not args.append or not args.output.exists()

    total = sum(len(runs) for _, runs in plan) * args.repetitions
    status_path = args.output.with_suffix('.status.txt')
    t_start = time.monotonic()
    state = {'done': 0, 'current': {}, 'last': None, 'warnings': 0}
    lock = threading.Lock()
    write_status(status_path, 0, total, t_start, current={})

    with open(args.output, mode, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
            f.flush()

        def run_queue(host_key, queue):
            for rep, run in queue:
                label = f"{run['label']} (rep {rep})"
                with lock:
                    state['current'][host_key] = label
                    write_status(status_path, state['done'], total, t_start,
                                 state['current'], state['last'], state['warnings'])
                rows, elapsed, ok = execute_run(run, rep)
                with lock:
                    writer.writerows(rows)
                    f.flush()
                    state['done'] += 1
                    if not ok:
                        state['warnings'] += 1
                    state['current'][host_key] = '-'
                    state['last'] = f"{label} in {elapsed:.0f}s"
                    write_status(status_path, state['done'], total, t_start,
                                 state['current'], state['last'], state['warnings'])

        try:
            if args.sequential:
                run_queue('eliza', queues['eliza'] + queues['ace'])
            else:
                threads = [threading.Thread(target=run_queue, args=(k, queues[k]), daemon=True)
                           for k in ('eliza', 'ace')]
                for t in threads:
                    t.start()
                while any(t.is_alive() for t in threads):
                    for t in threads:
                        t.join(timeout=0.5)
        except KeyboardInterrupt:
            print("\nInterrupted — killing remote (ace) benchmark processes...",
                  file=sys.stderr, flush=True)
            cleanup_ace()
            LOG_FH.close()
            raise SystemExit(130)

    LOG_FH.close()
    print(f"\nCompleted: {state['done']}/{total} config points, {state['warnings']} warnings")
    print(f"Results: {args.output}   detail log: {args.log or args.output.with_suffix('.log')}")


if __name__ == '__main__':
    main()

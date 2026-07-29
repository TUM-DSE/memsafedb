"""Recipe-free YCSB runner for LevelDB and Redis, with load reuse.

The dataset is loaded once per (working-set, persistence) and reused across
thread counts and the read-only workloads (a/b/c/f, which don't change the
record count); insert workloads (d/e) reload since they grow the DB. Eliza runs
the generated script locally; ace runs the identical script over ssh inside the
per-variant nix devshell (one session per variant, so redis' server stays up).
"""
import getpass
import re
import subprocess

RO_WORKLOADS = ['a', 'b', 'c', 'f']   # read/update/RMW: record count stable -> reuse the load
INS_WORKLOADS = ['d', 'e']            # insert/scan+insert: size grows -> reload per run
ALL_WORKLOADS = RO_WORKLOADS + INS_WORKLOADS

DBMS_BASE = str(__import__('pathlib').Path(__file__).parent.parent)   # .../dbms
DATA_DIR = f"/scratch/{getpass.getuser()}/memsafedb/data"

_REDIS_SUFFIX = {'dynamic': '', 'mte': '-mte', 'static': '-static', 'cheri': '-cheri'}


def _cpus(t):
    t = int(t)
    return "0" if t == 1 else f"0-{t - 1}"


def _mte_env(variant):
    return "GLIBC_TUNABLES=glibc.mem.tagging=3 " if variant == 'mte' else ""


# ---------------------------------------------------------------- script gen

def _leveldb_script(variant, ws, persistence, thread_set, op_count):
    ycsb = f"{DBMS_BASE}/ycsb-cpp/build/release-{variant}/ycsb"
    wl = f"{DBMS_BASE}/ycsb-cpp/workloads"
    props = f"{DBMS_BASE}/ycsb-cpp/leveldb/leveldb.properties"
    db_dir = f"{DATA_DIR}/leveldb" if persistence == 'disk' else "/tmp"
    db = f"{db_dir}/ycsb-leveldb-{variant}"
    env = _mte_env(variant)
    load_t = max(thread_set)
    # ~1 KB per record (YCSB default 10x100 B fields + key). For the disk config
    # cap LevelDB's block cache to force in-DBMS (block cache) replacement; the
    # in-memory config sizes it to hold the whole set. -p after -P overrides the
    # cache_size in leveldb.properties.
    # Measured on the real 718MB/1M-record dataset with workload C (zipfian,
    # theta=0.99, YCSB default): avg latency vs cache fraction of dataset -
    #   0.1%->21.9us  1%->14.0us  5%->9.7us  10%->9.4us  25%->8.8us  100%->5.8us
    # The hit-rate curve saturates hard by ~5% (Zipfian skew concentrates most
    # requests on a small hot subset), so 10% (1.6x over fully-cached) barely
    # differs from 5% and looks nearly as good as fully cached. 1% sits in the
    # steep part of the curve (2.4x over fully-cached) and gives real eviction
    # pressure instead of being absorbed by the hot-set skew.
    datasize = int(ws) * 1024
    cache = int(datasize * 0.01) if persistence == 'disk' else datasize
    cache_opt = f'-p leveldb.cache_size={cache}'
    s = ["set -uo pipefail", f'mkdir -p "{db_dir}"', f'rm -rf "{db}"',
         # one shared load serves every read-only workload/thread
         f'{env}{ycsb} -load -db leveldb -P {wl}/workloada -P {props} {cache_opt} '
         f'-p threadcount={load_t} -p recordcount={ws} -p leveldb.dbname={db} -p leveldb.destroy=true -s']
    for w in RO_WORKLOADS:
        for t in thread_set:
            s.append(f'echo "=== LDB workload={w} threads={t} variant={variant} ==="')
            # env before taskset: `taskset VAR=val prog` makes taskset try to exec
            # "VAR=val"; the assignment must prefix the whole command so ycsb inherits it.
            s.append(f'{env}taskset -c {_cpus(t)} {ycsb} -run -db leveldb -P {wl}/workload{w} -P {props} {cache_opt} '
                     f'-p threadcount={t} -p recordcount={ws} -p operationcount={op_count} '
                     f'-p leveldb.dbname={db} -p leveldb.destroy=false -s')
    for w in INS_WORKLOADS:
        for t in thread_set:
            s.append(f'rm -rf "{db}"')
            s.append(f'{env}{ycsb} -load -db leveldb -P {wl}/workload{w} -P {props} {cache_opt} '
                     f'-p threadcount={load_t} -p recordcount={ws} -p leveldb.dbname={db} -p leveldb.destroy=true -s')
            s.append(f'echo "=== LDB workload={w} threads={t} variant={variant} ==="')
            s.append(f'{env}taskset -c {_cpus(t)} {ycsb} -run -db leveldb -P {wl}/workload{w} -P {props} {cache_opt} '
                     f'-p threadcount={t} -p recordcount={ws} -p operationcount={op_count} '
                     f'-p leveldb.dbname={db} -p leveldb.destroy=false -s')
    s.append(f'rm -rf "{db}"')
    return "\n".join(s)


def _redis_script(variant, ws, thread_set, op_count):
    suffix = _REDIS_SUFFIX[variant]
    server = f"{DBMS_BASE}/redis/src/redis-server{suffix}"
    cli = f"{DBMS_BASE}/redis/src/redis-cli{suffix}"
    wl = f"{DATA_DIR}/workloads/YCSB"
    env = _mte_env(variant)
    load_t = max(thread_set)
    conn = "redis -s -p redis.host=127.0.0.1 -p redis.port=6379"
    s = ["set -uo pipefail",
         # A wedged server from a previous variant keeps port 6379, so our own
         # start would fail and we'd talk to the stale one; reap it first.
         f'for p in $(pgrep -f "redis-server.*--dir {DATA_DIR}" 2>/dev/null); do '
         f'[ "$p" = "$$" ] || kill -9 "$p" 2>/dev/null; done',
         # drop any stale RDB and disable persistence, else the server spends
         # startup loading a leftover dump.rdb and returns "LOADING" to every op.
         f'rm -f {DATA_DIR}/dump.rdb',
         f'{env}{server} --dir {DATA_DIR} --save "" --appendonly no --ignore-warnings ARM64-COW-BUG &>/dev/null &',
         'SPID=$!',
         # timeout the ping: a wedged server accepts the connection but never
         # replies, which would block this wait loop forever.
         f'for i in $(seq 1 60); do timeout 3 {cli} -p 6379 ping 2>/dev/null | grep -q PONG && break; sleep 0.5; done',
         # one shared load for the read-only workloads
         f'taskset -c {_cpus(load_t)} ycsb.sh load {conn} -P {wl}/workloada '
         f'-p recordcount={ws} -p threadcount={load_t}']
    for w in RO_WORKLOADS:
        for t in thread_set:
            s.append(f'echo "=== REDIS workload={w} threads={t} variant={variant} ==="')
            s.append(f'taskset -c {_cpus(t)} ycsb.sh run {conn} -P {wl}/workload{w} '
                     f'-p recordcount={ws} -p operationcount={op_count} -p threadcount={t}')
    for w in INS_WORKLOADS:
        for t in thread_set:
            # timeout: a wedged server (e.g. CHERI fork bug) would block this forever
            s.append(f'timeout 60 {cli} -p 6379 flushall >/dev/null 2>&1 || true')
            s.append(f'taskset -c {_cpus(load_t)} ycsb.sh load {conn} -P {wl}/workload{w} '
                     f'-p recordcount={ws} -p threadcount={load_t}')
            s.append(f'echo "=== REDIS workload={w} threads={t} variant={variant} ==="')
            s.append(f'taskset -c {_cpus(t)} ycsb.sh run {conn} -P {wl}/workload{w} '
                     f'-p recordcount={ws} -p operationcount={op_count} -p threadcount={t}')
    # cheri's shutdown hangs on the ARM64/Morello COW fork bug even with nosave;
    # best-effort short timeout, then force-kill by PID + pattern sweep so an
    # orphan can't keep port 6379 and poison the next workload's server.
    s += [f'timeout 5 {cli} shutdown nosave >/dev/null 2>&1 || true',
          'kill -9 $SPID >/dev/null 2>&1 || true',
          # NB: skip $$ -- on eliza the script runs as `bash -c <script>`, so the
          # pattern also matches this shell's own argv and would kill the script.
          f'for p in $(pgrep -f "redis-server{suffix} --dir {DATA_DIR}" 2>/dev/null); do '
          f'[ "$p" = "$$" ] || kill -9 "$p" 2>/dev/null; done',
          f'rm -f {DATA_DIR}/dump.rdb', 'wait $SPID 2>/dev/null || true']
    return "\n".join(s)


# ---------------------------------------------------------------- execution

def _run_script(host, devshell, script):
    if host == 'eliza':
        p = subprocess.run(['bash', '-c', script], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
    else:  # ace: same script inside the per-variant nix devshell over ssh
        remote = (f'mkdir -p /var/tmp/nixbuild && cd {DBMS_BASE} && '
                  f'TMPDIR=/var/tmp/nixbuild nix --extra-experimental-features flakes '
                  f'--extra-experimental-features nix-command develop .#{devshell} -c bash -s')
        p = subprocess.run(['ssh', 'ace', remote], input=script, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
    return p.stdout, p.returncode


# ---------------------------------------------------------------- parsing

_LDB_MARKER = re.compile(r'^=== LDB workload=([a-f]) threads=(\d+) variant=(\w+) ===$')
_LDB_TP = re.compile(r'Run throughput\(ops/sec\):\s+([\d.]+)')
_LDB_OP = re.compile(r'\[([A-Z]+): Count=(\d+) Max=[0-9.]+ Min=[0-9.]+ Avg=([0-9.]+)\]')
_REDIS_MARKER = re.compile(r'^=== REDIS workload=([a-f]) threads=(\d+) variant=(\w+) ===$')
_REDIS_OVERALL = re.compile(r'\[OVERALL\],\s*Throughput\(ops/sec\),\s*([0-9.]+)', re.IGNORECASE)
_REDIS_CUR = re.compile(r'operations;\s*([0-9.]+)\s+current ops/sec;')


def _blocks(output, marker):
    cur = None
    for line in output.split('\n'):
        m = marker.match(line.strip())
        if m:
            if cur:
                yield cur[0], "\n".join(cur[1])
            cur = [m.groups(), []]
        elif cur is not None:
            cur[1].append(line)
    if cur:
        yield cur[0], "\n".join(cur[1])


def _row(db, variant, workload, persistence, ws, threads, rep):
    return {'database': db, 'variant': f'release-{variant}', 'benchmark': 'ycsb',
            'workload': workload, 'repetition': rep,
            'persistence': persistence if persistence is not None else 'na',
            'working_set': ws, 'threads': threads}


def _parse_leveldb(output, ws, persistence, rep):
    rows = []
    for (wl, t, variant), text in _blocks(output, _LDB_MARKER):
        tp = _LDB_TP.search(text)
        if not tp:
            continue
        base = _row('leveldb', variant, f'{wl}_t{t}', persistence, ws, int(t), rep)
        rows.append({**base, 'metric_name': 'throughput', 'metric_value': float(tp.group(1)), 'unit': 'ops/sec'})
        stat = next((ln for ln in reversed(text.split('\n'))
                     if 'operations;' in ln and '[' in ln and ']' in ln), None)
        if stat:
            ops = _LDB_OP.findall(stat)
            tot = sum(int(c) for _, c, _ in ops)
            wsum = sum(int(c) * float(a) for _, c, a in ops)
            if tot > 0:
                rows.append({**base, 'metric_name': 'latency_avg',
                             'metric_value': f'{wsum / tot:.3f}', 'unit': 'us'})
    return rows


def _parse_redis(output, ws, persistence, rep):
    rows = []
    for (wl, t, variant), text in _blocks(output, _REDIS_MARKER):
        m = _REDIS_OVERALL.search(text)
        if m:
            tp = float(m.group(1))
        else:
            cur = _REDIS_CUR.findall(text)
            if not cur:
                continue
            tp = float(cur[-1])
        rows.append({**_row('redis', variant, wl, persistence, ws, int(t), rep),
                     'metric_name': 'throughput', 'metric_value': tp, 'unit': 'ops/sec'})
    return rows


# ---------------------------------------------------------------- entry point

def make_exec(db, host, ws, persistence, thread_set, op_count):
    """Return exec(repetition) -> (rows, ok, output) for one (host, ws, persistence)."""
    def _exec(repetition):
        outputs, rc_ok = [], True
        for v in host['variants']:
            variant, devshell = v if isinstance(v, tuple) else (v, None)
            if db == 'leveldb':
                script = _leveldb_script(variant, ws, persistence, thread_set, op_count)
            else:
                script = _redis_script(variant, ws, thread_set, op_count)
            out, rc = _run_script(host['name'], devshell, script)
            outputs.append(out)
            if rc != 0:
                rc_ok = False
        full = "\n".join(outputs)
        rows = (_parse_leveldb if db == 'leveldb' else _parse_redis)(full, ws, persistence, repetition)
        expected = len(host['variants']) * len(ALL_WORKLOADS) * len(thread_set)
        got = sum(1 for r in rows if r['metric_name'] == 'throughput')
        return rows, (rc_ok and got == expected), full
    return _exec

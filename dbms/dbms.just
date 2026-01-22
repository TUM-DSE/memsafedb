dbms_basedir := source_dir()
TPCH_SF := "10" # ~~2.5GB according to DuckDB website

help:
  just -l dbms

# Run benchmarks and collect results to CSV
benchmark db="all" repetitions="1":
  python3 {{dbms_basedir}}/benchmark/run_benchmarks.py --db "{{db}}" --repetitions "{{repetitions}}"

# Generate plots from results
plot:
  python3 {{dbms_basedir}}/../plots/dbms.py

build_duckdb arch="aarch64":
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/duckdb
  if [[ "{{arch}}" = "cheri" ]] then
    ARCH="{{arch}}" DUCKDB_PLATFORM=linux_arm64_musl EXTENSION_STATIC_BUILD=1 DISABLE_PARQUET=1 DISABLE_CPP_UNITTESTS=1 make -j release
    # cmake ../.. -DCMAKE_TOOLCHAIN_FILE=../../../../utils/morello-toolchain.cmake -DCMAKE_BUILD_TYPE=Release -DDISABLE_UNITY=1 -DBUILD_EXTENSIONS="" -DBUILD_UNITTESTS=OFF -DBUILD_SHELL=ON -DENABLE_SANITIZER=OFF -DENABLE_UBSAN=OFF
  else
    ARCH="aarch64" make -j release
    ARCH="{{arch}}" make -j release
  fi

setup_duckdb sf="10":
  #!/usr/bin/env bash
  # Note: this only works for 1, 3, 10, 30, 100, 300, 1000 and 3000 (refer to https://duckdb.org/docs/stable/core_extensions/tpch#pre-generated-datasets)
  # otherwise we need to generate them ourselves
  if [[ ! -e tpch-sf{{sf}}.db ]]; then
    wget https://blobs.duckdb.org/data/tpch-sf{{sf}}.db
  fi

# Run TPC-H for duckdb
run_duckdb sf="10":
  #!/usr/bin/env bash
  set -eu pipefail
  for q in `seq 1 22`
  do
    {{dbms_basedir}}/duckdb/build/release/duckdb {{dbms_basedir}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
    GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/duckdb/build/release-mte/duckdb {{dbms_basedir}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
  done

clean_duckdb:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/duckdb
  make clean

build_redis:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/redis
  ARCH="aarch64" make -j persist-settings
  ARCH="aarch64" make -j
  ARCH="mte" make -j persist-settings
  ARCH="mte" make -j
  make -j

# Run YCSB for redis
run_redis:
  #!/usr/bin/env bash
  for suffix in "" "-mte"; do
    for l in a b c d e f
    do
      {{dbms_basedir}}/redis/src/redis-server${suffix} &> /dev/null &

      ycsb.sh load redis -s -P {{dbms_basedir}}/workloads/YCSB/workload$l -p "redis.host=127.0.0.1" -p "redis.port=6379"
      ycsb.sh run redis -s -P {{dbms_basedir}}/workloads/YCSB/workload$l -p "redis.host=127.0.0.1" -p "redis.port=6379"

      {{dbms_basedir}}/redis/src/redis-cli${suffix} shutdown
      rm -f {{dbms_basedir}}/redis/dump.rdb
    done
  done

build_leveldb:
  #!/usr/bin/env bash
  set -euo pipefail
  cd {{dbms_basedir}}/leveldb

  # Build LevelDB (release and MTE variants)
  cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DLEVELDB_BUILD_BENCHMARKS=ON -DBUILD_SHARED_LIBS=OFF -DHAVE_TCMALLOC=OFF -DCMAKE_C_FLAGS="-march=armv8.5-a" -DCMAKE_CXX_FLAGS="-march=armv8.5-a"
  cmake --build build/release -j
  cmake -S . -B build/release-mte -DCMAKE_BUILD_TYPE=Release -DLEVELDB_BUILD_BENCHMARKS=ON -DBUILD_SHARED_LIBS=OFF -DHAVE_TCMALLOC=OFF -DCMAKE_C_FLAGS="-march=armv8.5-a+memtag -DMTE" -DCMAKE_CXX_FLAGS="-march=armv8.5-a+memtag -DMTE"
  cmake --build build/release-mte -j

  # Build YCSB-cpp for LevelDB (linked against both variants)
  cd {{dbms_basedir}}/ycsb-cpp

  make BIND_LEVELDB=1 \
    EXTRA_CXXFLAGS="-I{{dbms_basedir}}/leveldb/include" \
    EXTRA_LDFLAGS="-L{{dbms_basedir}}/leveldb/build/release -lsnappy"
  cp ycsb {{dbms_basedir}}/leveldb/build/release/ycsb

  make BIND_LEVELDB=1 \
    EXTRA_CXXFLAGS="-I{{dbms_basedir}}/leveldb/include" \
    EXTRA_LDFLAGS="-L{{dbms_basedir}}/leveldb/build/release-mte -lsnappy"
  cp ycsb {{dbms_basedir}}/leveldb/build/release-mte/ycsb

# Run leveldb db_bench
run_leveldb_bench:
  #!/usr/bin/env bash
  set -eu pipefail
  for suffix in "" "-mte"; do
    db_path="{{dbms_basedir}}/leveldb/dbbench${suffix}"
    rm -rf "${db_path}"
    tunables=""
    if [[ "${suffix}" == "-mte" ]]; then
      tunables="glibc.mem.tagging=3"
    fi
    GLIBC_TUNABLES="$tunables" {{dbms_basedir}}/leveldb/build/release"${suffix}"/db_bench --db="${db_path}"
    rm -rf "${db_path}"
  done

# Run YCSB workloads against LevelDB
run_leveldb recordcount="100000" operationcount="100000" threads="1":
  #!/usr/bin/env bash
  set -euo pipefail

  ycsb_dir="{{dbms_basedir}}/ycsb-cpp"
  workloads_dir="${ycsb_dir}/workloads"
  leveldb_props="${ycsb_dir}/leveldb/leveldb.properties"

  for suffix in "" "-mte"; do
    build_root="{{dbms_basedir}}/leveldb/build/release${suffix}"
    ycsb_bin="${build_root}/ycsb"
    db_path="${build_root}/ycsb-leveldb"

    tunables=""
    preload=""
    if [[ "${suffix}" == "-mte" ]]; then
      tunables="glibc.mem.tagging=3"
      preload="${MTE_MALLOC}"
    fi

    for workload in a b c d e f; do
      echo "=== Running workload${workload} (${suffix:-release}) ==="
      rm -rf "${db_path}"

      # Load phase
      LD_PRELOAD="${preload}" GLIBC_TUNABLES="${tunables}" "${ycsb_bin}" -load -db leveldb \
        -P "${workloads_dir}/workload${workload}" \
        -P "${leveldb_props}" \
        -p leveldb.dbname="${db_path}" \
        -p leveldb.destroy=true \
        -p recordcount="{{recordcount}}" \
        -p threadcount="{{threads}}" \
        -s

      # Run phase
      LD_PRELOAD="${preload}" GLIBC_TUNABLES="${tunables}" "${ycsb_bin}" -run -db leveldb \
        -P "${workloads_dir}/workload${workload}" \
        -P "${leveldb_props}" \
        -p leveldb.dbname="${db_path}" \
        -p operationcount="{{operationcount}}" \
        -p threadcount="{{threads}}" \
        -s

      rm -rf "${db_path}"
    done
  done

build_sqlite:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/sqlite
  mkdir -p build/release build/release-mte
  (
    cd build/release
    ../../configure CFLAGS="-O2 -DSQLITE_ENABLE_RTREE -march=armv8.5-a"
    make -j sqlite3 speedtest1 libsqlite3.so
  )
  (
    cd build/release-mte
    ../../configure CFLAGS="-O2 -DSQLITE_ENABLE_RTREE -march=armv8.5-a+memtag -DMTE"
    make -j sqlite3 speedtest1 libsqlite3.so
  )

# Run the sqlite speedtest1
run_sqlite_speedtest size="100":
  #!/usr/bin/env bash
  set -eu pipefail
  for suffix in "" "-mte"; do
    db_path="{{dbms_basedir}}/sqlite/build/release${suffix}/speedtest1.db"
    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm" "${db_path}-vacuum"
    tunables=""
    if [[ "${suffix}" == "-mte" ]]; then
      tunables="glibc.mem.tagging=3"
    fi
    SQLITE_TMPDIR="/tmp" GLIBC_TUNABLES="$tunables" {{dbms_basedir}}/sqlite/build/release"${suffix}"/speedtest1 --size "{{size}}" "${db_path}"
    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm" "${db_path}-vacuum"
  done

# Run TPC-C for sqlite
run_sqlite warehouses="1" duration="60" clients="1":
  #!/usr/bin/env bash
  set -euo pipefail

  ddl_path="{{dbms_basedir}}/sqlite/tpcc.sql"

  # Copy DDL file if not present
  if [[ ! -f "${ddl_path}" ]]; then
    cp "$(dirname "$(which py-tpcc)")/../lib/py-tpcc/tpcc.sql" "${ddl_path}"
  fi

  for suffix in "" "-mte"; do
    run_root="{{dbms_basedir}}/sqlite/build/release${suffix}"
    db_path="${run_root}/tpcc.db"
    config_path="${run_root}/tpcc.config"

    # Cleanup previous run
    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm"
    rm -f "${run_root}/results.log"

    tunables=""
    preload="${run_root}/libsqlite3.so"
    if [[ "${suffix}" == "-mte" ]]; then
      tunables="glibc.mem.tagging=3"
      preload="${run_root}/libsqlite3.so:${MTE_MALLOC}"
    fi

    # Create config file
    printf "[sqlite]\ndatabase = ${db_path}\n" > "${config_path}"

    # Ensure we use the correct sqlite3 binary and library
    export PATH="${run_root}:${PATH}"
    export LD_PRELOAD="${preload}"

    # Run TPC-C benchmark
    cd "${run_root}"
    GLIBC_TUNABLES="${tunables}" py-tpcc \
      --warehouses "{{warehouses}}" \
      --duration "{{duration}}" \
      --clients "{{clients}}" \
      --ddl "${ddl_path}" \
      --config "${config_path}" \
      sqlite

    # Cleanup
    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm"
  done

build_ladybug:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/ladybug
  ARCH=aarch64 make -j release
  ARCH=aarch64 make -j python
  ARCH=mte make -j release
  ARCH=mte make -j python

run_ladybug threads="":
  #!/usr/bin/env bash
  set -eu pipefail
  dataset_dir="{{dbms_basedir}}/ladybug/dataset/lsqb-sf01"
  csv_root="{{dbms_basedir}}/ladybug/build/lsqb-data"
  mkdir -p "${csv_root}/lsqb-datasets"
  ln -sfn "${dataset_dir}" "${csv_root}/lsqb-datasets/social-network-sf0.1-projected-fk"
  export CSV_DIR="${csv_root}"
  export SCALE_FACTOR="0.1"
  if [[ -n "{{threads}}" ]]; then
    export NUM_THREADS="{{threads}}"
  fi
  for suffix in "" "-mte"; do
    tunables=""
    if [[ "${suffix}" == "-mte" ]]; then
      tunables="glibc.mem.tagging=3"
    fi
    build_root="{{dbms_basedir}}/ladybug/build${suffix}"
    serialized_root="${build_root}/lsqb-serialized"
    rm -rf "${serialized_root}"
    mkdir -p "${serialized_root}"
    export SERIALIZED_DIR="${serialized_root}"
    PYTHONPATH="{{dbms_basedir}}/ladybug/tools/python_api/tools/python_api/build${suffix}:${PYTHONPATH:-}" GLIBC_TUNABLES="${tunables}" \
      python3 {{dbms_basedir}}/ladybug/benchmark/lsqb/benchmark_runner.py
    rm lsqb.log
  done

build_mysql:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/mysql
  cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-march=armv8.5-a" -DCMAKE_CXX_FLAGS="-march=armv8.5-a"
  cmake --build build/release -j
  cmake -S . -B build/release-mte -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-march=armv8.5-a+memtag -DMTE -isystem {{dbms_basedir}}/../utils" -DCMAKE_CXX_FLAGS="-march=armv8.5-a+memtag -DMTE -isystem {{dbms_basedir}}/../utils"
  cmake --build build/release-mte -j

# Run TPC-C for mysql
run_mysql:
  #!/usr/bin/env bash
  set -euo pipefail

  # Sysbench config
  sysbench_bin="${SYSBENCH_BIN:-sysbench}"
  sysbench_path="${SYSBENCH_PATH:-/usr}"
  oltp_script="${SYSBENCH_OLTP_SCRIPT:-${sysbench_path}/share/sysbench/oltp_read_write.lua}"

  command -v "${sysbench_bin}" >/dev/null 2>&1 || { echo "sysbench not found" >&2; exit 1; }
  [[ -f "${oltp_script}" ]] || { echo "OLTP script not found: ${oltp_script}" >&2; exit 1; }

  # Benchmark parameters
  port="${MYSQL_PORT:-3307}"
  db="${MYSQL_DB:-sbtest}"
  user="${MYSQL_USER:-root}"
  pass="${MYSQL_PASS:-}"
  table_size="${OLTP_TABLE_SIZE:-10000}"
  tables="${OLTP_TABLES:-1}"
  threads="${OLTP_THREADS:-4}"
  duration="${OLTP_DURATION:-60}"
  report_interval="${OLTP_REPORT_INTERVAL:-10}"

  for suffix in "" "-mte"; do
    label="release"
    [[ "${suffix}" == "-mte" ]] && label="release-mte"
    echo "=== Running mysql (${label}) ==="
    build_root="{{dbms_basedir}}/mysql/build/release${suffix}"
    run_root="{{dbms_basedir}}/mysql/build/run${suffix}"
    data_dir="${run_root}/data"
    pid_path="${run_root}/mysqld.pid"
    log_path="${run_root}/mysqld.log"

    mysql_cmd="${build_root}/bin/mysql --protocol=tcp --port=${port} --user=${user}"
    mysqladmin_cmd="${build_root}/bin/mysqladmin --protocol=tcp --port=${port} --user=${user}"

    sysbench_opts="--db-driver=mysql --mysql-host=127.0.0.1 --mysql-port=${port}"
    sysbench_opts+=" --mysql-user=${user} --mysql-password=${pass} --mysql-db=${db}"
    sysbench_opts+=" --tables=${tables} --table-size=${table_size}"

    # Cleanup any previous instance
    [[ -f "${pid_path}" ]] && ${mysqladmin_cmd} shutdown &>/dev/null || true
    rm -rf "${data_dir}"
    mkdir -p "${data_dir}"

    tunables=""
    [[ "${suffix}" == "-mte" ]] && tunables="glibc.mem.tagging=3"

    # Initialize and start MySQL
    GLIBC_TUNABLES="${tunables}" "${build_root}/bin/mysqld" \
      --initialize-insecure \
      --basedir="${build_root}" \
      --datadir="${data_dir}" \
      --lc-messages-dir="${build_root}/share" \
      --plugin-dir="${build_root}/lib/plugin" \
      --log-error="${log_path}"

    GLIBC_TUNABLES="${tunables}" "${build_root}/bin/mysqld" \
      --basedir="${build_root}" \
      --datadir="${data_dir}" \
      --socket="${run_root}/mysql.sock" \
      --pid-file="${pid_path}" \
      --port="${port}" \
      --bind-address=127.0.0.1 \
      --plugin-dir="${build_root}/lib/plugin" \
      --log-error="${log_path}" &>"${log_path}" &
    mysqld_pid=$!

    trap 'echo "Terminated, stopping mysql"; ${mysqladmin_cmd} shutdown &>/dev/null || kill ${mysqld_pid} &>/dev/null || true' EXIT

    # Wait for MySQL to be ready
    for _ in {1..50}; do
      ${mysqladmin_cmd} ping &>/dev/null && break
      sleep 0.2
    done

    # Run benchmark
    ${mysql_cmd} -e "DROP DATABASE IF EXISTS ${db}; CREATE DATABASE ${db};"

    ${sysbench_bin} ${oltp_script} ${sysbench_opts} prepare

    ${sysbench_bin} ${oltp_script} ${sysbench_opts} \
      --threads="${threads}" \
      --time="${duration}" \
      --report-interval="${report_interval}" \
      --mysql-ignore-errors=1213 \
      run

    ${sysbench_bin} ${oltp_script} ${sysbench_opts} cleanup

    ${mysqladmin_cmd} shutdown
    trap - EXIT
  done

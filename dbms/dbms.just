dbms_basedir := source_dir()
TPCH_SF := "10" # ~~2.5GB according to DuckDB website

build_duckdb:
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
  cd {{dbms_basedir}}/leveldb
  cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DLEVELDB_BUILD_BENCHMARKS=ON -DBUILD_SHARED_LIBS=OFF -DHAVE_TCMALLOC=OFF
  cmake --build build/release -j
  cmake -S . -B build/release-mte -DCMAKE_BUILD_TYPE=Release -DLEVELDB_BUILD_BENCHMARKS=ON -DBUILD_SHARED_LIBS=OFF -DHAVE_TCMALLOC=OFF -DCMAKE_C_FLAGS="-march=armv8.5-a+memtag -DMTE" -DCMAKE_CXX_FLAGS="-march=armv8.5-a+memtag -DMTE"
  cmake --build build/release-mte -j

run_leveldb:
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

build_sqlite:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/sqlite
  mkdir -p build/release build/release-mte
  (
    cd build/release
    ../../configure CFLAGS="-O2 -DSQLITE_ENABLE_RTREE"
    make -j sqlite3 speedtest1
  )
  (
    cd build/release-mte
    ../../configure CFLAGS="-O2 -DSQLITE_ENABLE_RTREE -march=armv8.5-a+memtag -DMTE"
    make -j sqlite3 speedtest1
  )

run_sqlite size="100":
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


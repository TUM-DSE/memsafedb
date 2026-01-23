dbms_basedir := source_dir()
TPCH_SF := "10" # ~~2.5GB according to DuckDB website

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
  # make distclean && make CC="${MORELLO_CLANG_DIR}/bin/clang" AR="${MORELLO_CLANG_DIR}/bin/ar" RANLIB="${MORELLO_CLANG_DIR}/bin/ranlib" MALLOC=libc USE_SYSTEMD=no BUILD_TLS=no OPTIMIZATION="-O3 -g" CFLAGS="-march=morello -mabi=purecap --target=aarch64-linux-musl_purecap --sysroot=${MORELLO_SYSROOT} -Wno-error" LDFLAGS="-L${MORELLO_LLVM_DIR}/lib -L${MORELLO_SYSROOT}/lib -static" -j

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
  set -eu pipefail
  cd {{dbms_basedir}}/leveldb
  rm -rf build/release-cheri build/release-static build/release-mte build/release-dynamic build/release-asan
  # Clean YCSB builds
  rm -rf ../workloads/ycsb_leveldb_loadgenerator/build
  # Apply YCSB patch
  (cd {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator && git checkout . && git apply {{dbms_basedir}}/workloads/ycsb.patch)
  
  # Function to build LevelDB and YCSB for a specific target
  # Usage: build_target <dir_suffix> <leveldb_cmake_flags> <ycsb_cmake_flags>
  build_target() {
    local suffix="$1"
    local leveldb_flags="$2"
    local ycsb_flags="$3"
    local log_file="/tmp/build_leveldb_${suffix}.log"
    
    echo -n "Building Target: $suffix ... "
    
    # 1. Build LevelDB
    cd {{dbms_basedir}}/leveldb
    if ! eval cmake -S . -B "build/release-$suffix" \
      -DCMAKE_BUILD_TYPE=Release \
      -DLEVELDB_BUILD_BENCHMARKS=ON \
      -DLEVELDB_BUILD_TESTS=OFF \
      -DBUILD_SHARED_LIBS=OFF \
      -DHAVE_TCMALLOC=OFF \
      -DHAVE_CRC32C=OFF \
      -DHAVE_SNAPPY=OFF \
      -DHAVE_STD_REGEX=ON \
      -DBENCHMARK_ENABLE_WERROR=OFF \
      $leveldb_flags > "$log_file" 2>&1; then
        echo "FAILED (LevelDB Config). Output:"
        cat "$log_file"
        rm -f "$log_file"
        return 1
    fi
      
    if ! cmake --build "build/release-$suffix" -j > "$log_file" 2>&1; then
        echo "FAILED (LevelDB Build). Output:"
        cat "$log_file"
        rm -f "$log_file"
        return 1
    fi

    # 2. Build YCSB
    mkdir -p "{{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-$suffix"
    cd "{{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-$suffix"
    
    if ! eval cmake ../.. \
      -DBIND_LEVELDB=1 \
      -DLEVELDB_INCLUDE_DIR="{{dbms_basedir}}/leveldb/include" \
      -DLEVELDB_LIB="{{dbms_basedir}}/leveldb/build/release-$suffix/libleveldb.a" \
      -DWITH_SNAPPY=0 \
      -DWITH_LZ4=0 \
      -DWITH_ZSTD=0 \
      $ycsb_flags > "$log_file" 2>&1; then
        echo "FAILED (YCSB Config). Output:"
        cat "$log_file"
        rm -f "$log_file"
        return 1
    fi
      
    if ! make -j > "$log_file" 2>&1; then
        echo "FAILED (YCSB Build). Output:"
        cat "$log_file"
        rm -f "$log_file"
        return 1
    fi
    
    echo "SUCCESS"
    rm -f "$log_file"
  }

  # 1. CHERI Purecap
  build_target "cheri" \
    "-DCMAKE_TOOLCHAIN_FILE=../../utils/morello-toolchain.cmake" \
    "-DCMAKE_TOOLCHAIN_FILE=../../../../../utils/morello-toolchain.cmake -DWITH_ZLIB=0"

  # 2. AArch64 Static (CHERI Baseline)
  build_target "static" \
    "-DCMAKE_TOOLCHAIN_FILE=../../utils/aarch64-static-toolchain.cmake" \
    "-DCMAKE_TOOLCHAIN_FILE=../../../../../utils/aarch64-static-toolchain.cmake -DWITH_ZLIB=0"

  # 3. MTE
  build_target "mte" \
    "-DCMAKE_C_FLAGS='-march=armv8.5-a+memtag -DMTE' -DCMAKE_CXX_FLAGS='-march=armv8.5-a+memtag -DMTE'" \
    "-DCMAKE_C_FLAGS='-march=armv8.5-a+memtag -DMTE' -DCMAKE_CXX_FLAGS='-march=armv8.5-a+memtag -DMTE' -DWITH_ZLIB=0"

  # 4. AArch64 Dynamic (MTE Baseline)
  build_target "dynamic" "" "-DWITH_ZLIB=0"

  # 5. AArch64 Dynamic (ASan)
  asan_flags="-fsanitize=address"
  build_target "asan" \
    "-DCMAKE_C_FLAGS=\"$asan_flags\" -DCMAKE_CXX_FLAGS=\"$asan_flags\"" \
    "-DCMAKE_C_FLAGS=\"$asan_flags\" -DCMAKE_CXX_FLAGS=\"$asan_flags\" -DWITH_ZLIB=0"

run_leveldb:
  #!/usr/bin/env bash
  set -eu pipefail
  
  OUT_DIR="{{dbms_basedir}}/../results/leveldb"
  mkdir -p "${OUT_DIR}"
  
  threads="1 4"
  workloads="a b c d e f"
  
  for t in $threads; do
    if [ "$t" -eq 1 ]; then
      cpus="0"
    else
      cpus="0-3"
    fi
    
    bench_params="--threads=$t --histogram=1 --benchmarks=fillseq,fillsync,fillrandom,overwrite,readrandom,readseq,readreverse,compact,fill100K,crc32c"

    taskset -c $cpus env GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/leveldb/build/release-mte/db_bench ${bench_params} > "${OUT_DIR}/bench_mte_t${t}.log" 2>&1 || echo "MTE db_bench failed"
    taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-dynamic/db_bench ${bench_params} > "${OUT_DIR}/bench_baseline-dynamic_t${t}.log" 2>&1 || echo "Dynamic db_bench failed"
    taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-asan/db_bench ${bench_params} > "${OUT_DIR}/bench_asan_t${t}.log" 2>&1 || echo "ASan db_bench failed"
    ssh ace "taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-static/db_bench ${bench_params}" > "${OUT_DIR}/bench_baseline-static_t${t}.log" 2>&1 || echo "Static db_bench failed"
    ssh ace "taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-cheri/db_bench ${bench_params}" > "${OUT_DIR}/bench_cheri-purecap_t${t}.log" 2>&1 || echo "CHERI db_bench failed"
    
    for w in $workloads; do
        taskset -c $cpus env GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-mte/ycsb -load -run -db leveldb -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/workloads/workload${w} -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/leveldb/leveldb.properties -p threadcount=${t} -s > "${OUT_DIR}/ycsb_${w}_mte_t${t}.log" 2>&1 || echo "MTE YCSB $w failed"
        taskset -c $cpus {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-dynamic/ycsb -load -run -db leveldb -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/workloads/workload${w} -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/leveldb/leveldb.properties -p threadcount=${t} -s > "${OUT_DIR}/ycsb_${w}_dynamic_t${t}.log" 2>&1 || echo "Dynamic YCSB $w failed"
        #taskset -c $cpus {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-asan/ycsb -load -run -db leveldb -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/workloads/workload${w} -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/leveldb/leveldb.properties -p threadcount=${t} -s > "${OUT_DIR}/ycsb_${w}_asan_t${t}.log" 2>&1 || echo "ASan YCSB $w failed"
        ssh ace "taskset -c $cpus {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-static/ycsb -load -run -db leveldb -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/workloads/workload${w} -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/leveldb/leveldb.properties -p threadcount=${t} -s" > "${OUT_DIR}/ycsb_${w}_static_t${t}.log" 2>&1 || echo "Static YCSB $w failed"
        ssh ace "taskset -c $cpus {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/build/release-cheri/ycsb -load -run -db leveldb -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/workloads/workload${w} -P {{dbms_basedir}}/workloads/ycsb_leveldb_loadgenerator/leveldb/leveldb.properties -p threadcount=${t} -s" > "${OUT_DIR}/ycsb_${w}_cheri_t${t}.log" 2>&1 || echo "CHERI YCSB $w failed"
    done
  done
  
  python3 {{dbms_basedir}}/parse_results_db_bench.py "${OUT_DIR}"
  python3 {{dbms_basedir}}/parse_results_ycsb.py "${OUT_DIR}"

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
    # ../../configure --host=aarch64-linux-musl_purecap --disable-tcl --disable-readline --disable-shared --enable-static CC="clang" CFLAGS="-O2 -g -DSQLITE_ENABLE_RTREE -march=morello -mabi=purecap --target=aarch64-linux-musl_purecap --sysroot=$MUSL_HOME" LDFLAGS="-L$MORELLO_HOME/llvm/lib -L$MUSL_HOME/lib -static"
    # make -j sqlite3 speedtest1
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


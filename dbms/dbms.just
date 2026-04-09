dbms_basedir := source_dir()

CHERI_HOST := "[redacted]"
user := `whoami`
DATA_DIR := "/scratch/"+user+"/memsafedb/data"

help:
  just -l dbms

# Run benchmarks and collect results to CSV
benchmark db="all" repetitions="1":
  python3 {{dbms_basedir}}/benchmark/run_benchmarks.py --db "{{db}}" --repetitions "{{repetitions}}" --append

# Generate plots from results
plot:
  python3 {{dbms_basedir}}/../plots/dbms.py

# Count MTE/CHERI instructions in DBMS binaries
instruction_counts db="all":
  python3 {{dbms_basedir}}/benchmark/count_new_instructions.py --db "{{db}}"

# Generate compiler instruction-count plot
plot_instruction_counts:
  python3 {{dbms_basedir}}/../plots/compiler_instructions.py

# Generate compiler instruction breakdown LaTeX table
instruction_breakdown_table top="all":
  python3 {{dbms_basedir}}/../plots/compiler_instruction_breakdown_table.py --top "{{top}}"

# Load data to local SSDs of this and remote hosts
prepare_local_data:
  #!/usr/bin/env bash
  mkdir -p {{DATA_DIR}}
  rsync -av {{dbms_basedir}}/tpch-sf*.db {{DATA_DIR}}
  rsync -rav {{dbms_basedir}}/workloads {{DATA_DIR}}/
  ssh {{CHERI_HOST}} "mkdir -p {{DATA_DIR}}"
  rsync -av {{dbms_basedir}}/tpch-sf*.db {{CHERI_HOST}}:{{DATA_DIR}}
  rsync -rav {{dbms_basedir}}/workloads {{CHERI_HOST}}:{{DATA_DIR}}/

build_duckdb:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/duckdb
  #  ARCH="cheri" DUCKDB_PLATFORM=linux_arm64_musl EXTENSION_STATIC_BUILD=1 DISABLE_PARQUET=1 DISABLE_CPP_UNITTESTS=1 make -j release
  #  # cmake ../.. -DCMAKE_TOOLCHAIN_FILE=../../../../utils/morello-toolchain.cmake -DCMAKE_BUILD_TYPE=Release -DDISABLE_UNITY=1 -DBUILD_EXTENSIONS="" -DBUILD_UNITTESTS=OFF -DBUILD_SHELL=ON -DENABLE_SANITIZER=OFF -DENABLE_UBSAN=OFF
  ARCH="mte" make -j release
  ARCH="aarch64" make -j release

setup_duckdb sf="100":
  #!/usr/bin/env bash
  # Note: this only works for 1, 3, 10, 30, 100, 300, 1000 and 3000 (refer to https://duckdb.org/docs/stable/core_extensions/tpch#pre-generated-datasets)
  # otherwise we need to generate them ourselves
  if [[ ! -e tpch-sf{{sf}}.db ]]; then
    wget https://blobs.duckdb.org/data/tpch-sf{{sf}}.db
  fi
  mv tpch-sf{{sf}}.db {{DATA_DIR}}

# Run TPC-H for duckdb
run_duckdb sf="100" monitor="false": #(setup_duckdb sf)
  #!/usr/bin/env bash
  set -eu pipefail

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    PAGE_SIZE=$(getconf PAGESIZE)
    echo "variant,phase,query,peak_rss_bytes" > "${result_dir}/duckdb_mem_footprint.csv"
  fi

  run_cmd() {
    local phase_label="$1"
    local variant_label="$2"
    local query_num="$3"
    shift 3

    if [[ "{{monitor}}" == "true" ]]; then
      local csv_output="${result_dir}/duckdb_mem_footprint.csv"
      
      # Launch command
      "$@" &
      local server_pid=$!
      
      # RSS monitor background process to track peak
      local temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        local peak_rss_pages=0
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -r "/proc/$server_pid/statm" ]]; then
            local rss_pages=$(awk '{print $2}' "/proc/$server_pid/statm" 2>/dev/null || true)
            if [[ -n "$rss_pages" ]] && [ "$rss_pages" -gt "$peak_rss_pages" ]; then
              peak_rss_pages=$rss_pages
            fi
          fi
          sleep 0.1
        done
        local peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      local monitor_pid=$!
      
      wait $server_pid || true

      wait $monitor_pid 2>/dev/null || true
      
      local final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "${variant_label},${phase_label},q${query_num},${final_peak}" >> "${csv_output}"
    else
      "$@"
    fi
  }

  if [[ "{{monitor}}" != "true" ]]; then
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    # Run all release queries (warm cache)
    echo "=== Running dynamic variant ===" >&2
    for q in `seq 1 22`
    do
      run_cmd "warm" "dynamic" "$q" {{dbms_basedir}}/duckdb/build/release-dynamic/duckdb {{DATA_DIR}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" > /dev/null 2>&1
    done
    for q in `seq 1 22`
    do
      run_cmd "hot" "dynamic" "$q" {{dbms_basedir}}/duckdb/build/release-dynamic/duckdb {{DATA_DIR}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
    done

    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    # Run all MTE queries (warm cache)
    echo "=== Running mte variant ===" >&2
    for q in `seq 1 22`
    do
      run_cmd "warm" "mte" "$q" env GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/duckdb/build/release-mte/duckdb {{DATA_DIR}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" > /dev/null 2>&1
    done
    for q in `seq 1 22`
    do
      run_cmd "hot" "mte" "$q" env GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/duckdb/build/release-mte/duckdb {{DATA_DIR}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
    done
  fi

  # Run all release queries (cold cache - drop caches before each query)
  echo "=== Running dynamic-cold variant ===" >&2
  for q in `seq 1 22`
  do
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    run_cmd "cold" "dynamic" "$q" {{dbms_basedir}}/duckdb/build/release-dynamic/duckdb {{DATA_DIR}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
  done

  # Run all MTE queries (cold cache - drop caches before each query)
  echo "=== Running mte-cold variant ===" >&2
  for q in `seq 1 22`
  do
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    run_cmd "cold" "mte" "$q" env GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/duckdb/build/release-mte/duckdb {{DATA_DIR}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
  done


clean_duckdb:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/duckdb
  make clean

build_redis:
  #!/usr/bin/env bash
  set -euo pipefail
  cd {{dbms_basedir}}/redis

  # Clean previous builds
  make distclean &> /dev/null || true

  # Function to build Redis for a specific target
  # Usage: build_target <suffix> <arch_flag> <extra_make_flags>
  build_target() {
    local suffix="$1"
    local arch_flag="$2"
    local extra_flags="$3"
    local log_file="/tmp/build_redis_${suffix}.log"

    echo -n "Building Target: $suffix ... "

    # Clean build state
    make distclean &> /dev/null || true

    # Build with specified architecture
    if ! eval ARCH="$arch_flag" make -j persist-settings $extra_flags > "$log_file" 2>&1; then
      echo "FAILED (persist-settings). Output:"
      cat "$log_file"
      rm -f "$log_file"
      return 1
    fi

    if ! eval ARCH="$arch_flag" make -j $extra_flags > "$log_file" 2>&1; then
      echo "FAILED (build). Output:"
      cat "$log_file"
      rm -f "$log_file"
      return 1
    fi

    echo "SUCCESS"
    rm -f "$log_file"
  }

  # AArch64 Static (CHERI baseline) - Uses environment variables from flake.nix
  build_target "static" "static" ""

  # CHERI Purecap - Uses environment variables from flake.nix
  build_target "cheri" "cheri" ""

  # MTE - Uses ARCH flag
  build_target "mte" "mte" ""

  # AArch64 Dynamic (MTE baseline) - Uses ARCH flag
  build_target "dynamic" "aarch64" ""

# Run YCSB for redis
run_redis recordcount="100000" operationcount="100000" monitor="false":
  #!/usr/bin/env bash
  set -euo pipefail

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    echo "variant,workload,rss_bytes" > "${result_dir}/redis_mem_footprint.csv"
  fi

  for variant in "dynamic" "mte" "static" "cheri"; do
    case "$variant" in
      "dynamic" | "mte")
        just dbms run_redis_local "$variant" "{{recordcount}}" "{{operationcount}}" "{{monitor}}"
        ;;
      "static" | "cheri")
        if [[ "$variant" == "static" ]]; then
          devshell="ace-aarch64"
        else
          devshell="ace-cheri"
        fi
        ssh ace "cd {{dbms_basedir}} && nix --extra-experimental-features flakes --extra-experimental-features nix-command develop .#${devshell} -c just dbms run_redis_local '$variant' '{{recordcount}}' '{{operationcount}}' '{{monitor}}'"
        ;;
    esac
  done

run_redis_local variant recordcount operationcount monitor:
  #!/usr/bin/env bash
  set -euo pipefail

  workloads_dir="{{DATA_DIR}}/workloads/YCSB"

  case "{{variant}}" in
    "dynamic")
      suffix=""
      ;;
    "mte")
      suffix="-mte"
      ;;
    "static")
      suffix="-static"
      ;;
    "cheri")
      suffix="-cheri"
      ;;
  esac

  if [[ "{{variant}}" == "mte" ]]; then
    server_env="GLIBC_TUNABLES=glibc.mem.tagging=3"
  else
    server_env=""
  fi
  redis_server="{{dbms_basedir}}/redis/src/redis-server${suffix}"
  redis_cli="{{dbms_basedir}}/redis/src/redis-cli${suffix}"
  
  if [[ "{{monitor}}" == "true" ]]; then
    PAGE_SIZE=$(getconf PAGESIZE)
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    csv_output="${result_dir}/redis_mem_footprint.csv"
  fi

  for workload in a b c d e f; do
    echo "=== Running workload${workload} - {{variant}} ==="

    eval ${server_env} ${redis_server} --dir {{DATA_DIR}} --ignore-warnings ARM64-COW-BUG &> /dev/null &
    server_pid=$!

    if [[ "{{monitor}}" == "true" ]]; then
      # RSS monitor background process to track peak
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -r "/proc/$server_pid/statm" ]]; then
            rss_pages=$(awk '{print $2}' "/proc/$server_pid/statm" 2>/dev/null || true)
            if [[ -n "$rss_pages" ]] && [ "$rss_pages" -gt "$peak_rss_pages" ]; then
              peak_rss_pages=$rss_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi

    sleep 1

    echo "=== REDIS_YCSB workload=${workload} variant={{variant}} phase=load ==="
    ycsb.sh load redis -s -P ${workloads_dir}/workload${workload} \
      -p "redis.host=127.0.0.1" \
      -p "redis.port=6379" \
      -p "recordcount={{recordcount}}"

    echo "=== REDIS_YCSB workload=${workload} variant={{variant}} phase=run ==="
    ycsb.sh run redis -s -P ${workloads_dir}/workload${workload} \
      -p "redis.host=127.0.0.1" \
      -p "redis.port=6379" \
      -p "recordcount={{recordcount}}" \
      -p "operationcount={{operationcount}}"

    ${redis_cli} shutdown || kill ${server_pid} &> /dev/null || true
    rm -f {{DATA_DIR}}/dump.rdb

    wait ${server_pid} 2> /dev/null || true

    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "{{variant}},${workload},${final_peak}" >> "${csv_output}"
    fi
  done


build_leveldb:
  #!/usr/bin/env bash
  set -eu pipefail
  cd {{dbms_basedir}}/leveldb
  rm -rf build/release-cheri build/release-static build/release-mte build/release-dynamic build/release-asan
  # Clean YCSB builds
  rm -rf {{dbms_basedir}}/ycsb-cpp/build
  # Apply YCSB patch
  (cd {{dbms_basedir}}/ycsb-cpp && git checkout . && git apply {{dbms_basedir}}/workloads/ycsb.patch) &> /dev/null
  
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
    mkdir -p "{{dbms_basedir}}/ycsb-cpp/build/release-$suffix"
    cd "{{dbms_basedir}}/ycsb-cpp/build/release-$suffix"
    
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
    "-DCMAKE_TOOLCHAIN_FILE=../../utils/morello-toolchain.cmake -DWITH_ZLIB=0"

  # 2. AArch64 Static (CHERI Baseline)
  build_target "static" \
    "-DCMAKE_TOOLCHAIN_FILE=../../utils/aarch64-static-toolchain.cmake" \
    "-DCMAKE_TOOLCHAIN_FILE=../../utils/aarch64-static-toolchain.cmake -DWITH_ZLIB=0"

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

run_leveldb_bench threads="1":
  #!/usr/bin/env bash
  set -eu pipefail
  threads={{threads}}
  
  if [ "$threads" -eq 1 ]; then
    cpus="0"
  else
    cpus="0-$(($threads - 1))"
  fi
  bench_params="--threads=$threads --histogram=1 --benchmarks=fillrandom,readrandom"

  echo "=== Running threads $threads - MTE ==="
  taskset -c $cpus env GLIBC_TUNABLES="glibc.mem.tagging=3" {{dbms_basedir}}/leveldb/build/release-mte/db_bench ${bench_params}
  echo "=== Running threads $threads - Dynamic ==="
  taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-dynamic/db_bench ${bench_params}
  echo "=== Running threads $threads - ASan ==="
  taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-asan/db_bench ${bench_params}
  echo "=== Running threads $threads - Static ==="
  ssh ace "taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-static/db_bench ${bench_params}"
  echo "=== Running threads $threads - Cheri ==="
  ssh ace "taskset -c $cpus {{dbms_basedir}}/leveldb/build/release-cheri/db_bench ${bench_params}"

# Run YCSB workloads against LevelDB
run_leveldb recordcount="100000" operationcount="100000" threads="1" monitor="false":
  #!/usr/bin/env bash
  set -euo pipefail

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    echo "variant,workload,peak_rss_bytes" > "${result_dir}/leveldb_mem_footprint.csv"
  fi

  for variant in "dynamic" "mte" "static" "cheri"; do
    case "$variant" in
      "dynamic" | "mte")
        just dbms::run_leveldb_local "$variant" "{{threads}}" "{{monitor}}"
        ;;
      "static" | "cheri")
        if [[ "$variant" == "static" ]]; then
          devshell="ace-aarch64"
        else
          devshell="ace-cheri"
        fi
        ssh ace "cd {{dbms_basedir}} && nix --extra-experimental-features flakes --extra-experimental-features nix-command develop .#${devshell} -c just dbms::run_leveldb_local '$variant' '{{threads}}' '{{monitor}}'"
        ;;
    esac
  done

run_leveldb_local suffix threads monitor:
  #!/usr/bin/env bash
  set -euo pipefail

  ycsb_dir="{{dbms_basedir}}/ycsb-cpp"
  workloads_dir="${ycsb_dir}/workloads"
  leveldb_props="${ycsb_dir}/leveldb/leveldb.properties"
  build_root="${ycsb_dir}/build/release-{{suffix}}"
  ycsb_bin="${build_root}/ycsb"
  
  if [[ "{{suffix}}" == "mte" ]]; then
    ycsb_bin="env GLIBC_TUNABLES=\"glibc.mem.tagging=3\" $ycsb_bin"
  fi
  
  if [ "{{threads}}" -eq 1 ]; then
    cpus="0"
  else
    cpus="0-$(({{threads}} - 1))"
  fi

  if [[ "{{monitor}}" == "true" ]]; then
    PAGE_SIZE=$(getconf PAGESIZE)
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    csv_output="${result_dir}/leveldb_mem_footprint.csv"
  fi

  for workload in a b c d e f; do
    echo "=== Running workload${workload} - threads: {{threads}} - {{suffix}} ==="
    
    # Run workload in background to gather RSS 
    taskset -c $cpus ${ycsb_bin} -load -run -db leveldb -P $workloads_dir/workload${workload} -P $leveldb_props -p threadcount={{threads}} -s &
    server_pid=$!
    
    if [[ "{{monitor}}" == "true" ]]; then
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -r "/proc/$server_pid/statm" ]]; then
            rss_pages=$(awk '{print $2}' "/proc/$server_pid/statm" 2>/dev/null || true)
            if [[ -n "$rss_pages" ]] && [ "$rss_pages" -gt "$peak_rss_pages" ]; then
              peak_rss_pages=$rss_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi
    
    wait $server_pid || true
    
    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "{{suffix}},${workload},${final_peak}" >> "${csv_output}"
    fi
  done

build_sqlite:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/sqlite
  rm -rf build/release-dynamic build/release-mte build/release-cheri build/release-static
  mkdir -p build/release-dynamic build/release-mte build/release-cheri build/release-static
  (
    cd build/release-dynamic
    ../../configure CFLAGS="-O2 -DSQLITE_ENABLE_RTREE -march=armv8.5-a"
    make -j sqlite3 libsqlite3.so
  )
  (
    cd build/release-mte
    ../../configure CFLAGS="-O2 -DSQLITE_ENABLE_RTREE -march=armv8.5-a+memtag -DMTE"
    make -j sqlite3 libsqlite3.so
  )
  (
    cd build/release-cheri
    ../../configure --host=aarch64-linux-musl_purecap --disable-tcl --disable-readline --disable-shared --enable-static CC="$MORELLO_CLANG_DIR/bin/clang -nostartfiles -nodefaultlibs" CFLAGS="-O2 -g -DSQLITE_ENABLE_RTREE -march=morello -mabi=purecap --target=aarch64-linux-musl_purecap -D__SIZEOF_POINTER__=16 --sysroot=$MORELLO_SYSROOT" LDFLAGS="$MORELLO_SYSROOT/lib/crt1.o $MORELLO_SYSROOT/lib/crti.o -L$MORELLO_LLVM_DIR/lib -L$MORELLO_LLVM_DIR/lib/linux -L$MORELLO_SYSROOT/lib -static -fuse-ld=lld -lc -lunwind -lclang_rt.builtins-aarch64 $MORELLO_SYSROOT/lib/crtn.o"
    make -j sqlite3
  )
  (
    cd build/release-static
    CLANG="$BASE_CLANG_DIR/bin/clang"
    TARGET_FLAGS="--target=aarch64-unknown-linux-musl"
    CRT_BEGIN=$($CLANG $TARGET_FLAGS -print-file-name=crtbeginT.o)
    CRT_END=$($CLANG $TARGET_FLAGS -print-file-name=crtend.o)
    BUILTINS_LIB=$($CLANG $TARGET_FLAGS -print-file-name=libclang_rt.builtins-aarch64.a)
    BUILTINS_DIR=$(dirname $BUILTINS_LIB)
    LDFLAGS_CONF="$BASE_SYSROOT/crt1.o $BASE_SYSROOT/crti.o $CRT_BEGIN -L$BASE_SYSROOT -L$BASE_LIBCXX_DIR/lib -L$BASE_UNWIND_DIR/lib -L$BUILTINS_DIR -static"
    LIBS_CONF="-Wl,--start-group -lc -lm -lunwind -lclang_rt.builtins-aarch64 -Wl,--end-group $CRT_END $BASE_SYSROOT/crtn.o"
    ../../configure --host=aarch64-unknown-linux-musl --disable-tcl --disable-readline --disable-shared --enable-static CC="$CLANG -nostartfiles -nodefaultlibs" CFLAGS="-O2 -DSQLITE_ENABLE_RTREE $TARGET_FLAGS --unwindlib=libunwind -I$BASE_HDRS/include" LDFLAGS="$LDFLAGS_CONF" LIBS="$LIBS_CONF"
    make -j sqlite3 "LDFLAGS.configure=$LDFLAGS_CONF $LIBS_CONF"
  )

run_sqlite_ace warehouses="1" duration="60" clients="1" monitor="false":
  #!/usr/bin/env bash
  set -euo pipefail

  ddl_path="{{dbms_basedir}}/sqlite/tpcc.sql"
  if [[ ! -f "${ddl_path}" ]]; then
    cp "$(dirname "$(which py-tpcc)")/../lib/py-tpcc/tpcc.sql" "${ddl_path}"
  fi

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    PAGE_SIZE=$(getconf PAGESIZE)
    csv_output="${result_dir}/sqlite_mem_footprint.csv"
  fi

  mkdir -p "{{DATA_DIR}}/sqlite"
  for suffix in "static" "cheri"; do
    echo "=== Executing $suffix ==="
    run_root="{{dbms_basedir}}/sqlite/build/release-${suffix}"
    db_path="{{DATA_DIR}}/sqlite/tpcc-${suffix}.db"
    config_path="${run_root}/tpcc.config"

    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm"
    rm -f "${run_root}/results.log"

    printf "[sqlite]\ndatabase = ${db_path}\n" > "${config_path}"

    export PATH="${run_root}:${PATH}"
    cd "${run_root}"
    
    # Run py-tpcc in background if monitoring
    py-tpcc --warehouses "{{warehouses}}" --duration "{{duration}}" --clients "{{clients}}" --ddl "${ddl_path}" --config "${config_path}" sqlite &
    server_pid=$!
    
    if [[ "{{monitor}}" == "true" ]]; then
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -r "/proc/$server_pid/statm" ]]; then
            rss_pages=$(awk '{print $2}' "/proc/$server_pid/statm" 2>/dev/null || true)
            if [[ -n "$rss_pages" ]] && [ "$rss_pages" -gt "$peak_rss_pages" ]; then
              peak_rss_pages=$rss_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi
    
    wait $server_pid || true
    
    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "${suffix},tpcc,${final_peak}" >> "${csv_output}"
    fi

    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm"
  done

run_sqlite_eliza warehouses="1" duration="60" clients="1" monitor="false":
  #!/usr/bin/env bash
  set -euo pipefail

  ddl_path="{{dbms_basedir}}/sqlite/tpcc.sql"

  if [[ ! -f "${ddl_path}" ]]; then
    cp "$(dirname "$(which py-tpcc)")/../lib/py-tpcc/tpcc.sql" "${ddl_path}"
  fi

  if [[ -z "$GLIBC_MTE" ]]; then
    echo "Error: MTE-enabled glibc not found. GLIBC_MTE must be set" >&2
    exit 1
  fi

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    PAGE_SIZE=$(getconf PAGESIZE)
    csv_output="${result_dir}/sqlite_mem_footprint.csv"
  fi

  mkdir -p "{{DATA_DIR}}/sqlite"
  for suffix in "dynamic" "mte"; do
    echo "=== Executing $suffix ==="
    run_root="{{dbms_basedir}}/sqlite/build/release-${suffix}"
    db_path="{{DATA_DIR}}/sqlite/tpcc-${suffix}.db"
    config_path="${run_root}/tpcc.config"
    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm"
    rm -f "${run_root}/results.log"

    tunables=""
    preload="${run_root}/libsqlite3.so"
    ld_library_path=""
    if [[ "${suffix}" == "mte" ]]; then
      tunables="glibc.mem.tagging=3"
      ld_library_path="${GLIBC_MTE}/lib"
    fi

    printf "[sqlite]\ndatabase = ${db_path}\n" > "${config_path}"

    export PATH="${run_root}:${PATH}"

    cd "${run_root}"
    
    LD_LIBRARY_PATH="${ld_library_path}" LD_PRELOAD="${preload}" GLIBC_TUNABLES="${tunables}" py-tpcc --warehouses "{{warehouses}}" --duration "{{duration}}" --clients "{{clients}}" --ddl "${ddl_path}" --config "${config_path}" sqlite &
    server_pid=$!
    
    if [[ "{{monitor}}" == "true" ]]; then
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -r "/proc/$server_pid/statm" ]]; then
            rss_pages=$(awk '{print $2}' "/proc/$server_pid/statm" 2>/dev/null || true)
            if [[ -n "$rss_pages" ]] && [ "$rss_pages" -gt "$peak_rss_pages" ]; then
              peak_rss_pages=$rss_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi
    
    wait $server_pid || true
    
    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "${suffix},tpcc,${final_peak}" >> "${csv_output}"
    fi

    rm -f "${db_path}" "${db_path}-journal" "${db_path}-wal" "${db_path}-shm"
  done

run_sqlite warehouses="1" duration="60" clients="1" monitor="false":
  #!/usr/bin/env bash
  set -euo pipefail
  
  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    echo "variant,workload,peak_rss_bytes" > "${result_dir}/sqlite_mem_footprint.csv"
  fi
  
  just dbms::run_sqlite_eliza "{{warehouses}}" "{{duration}}" "{{clients}}" "{{monitor}}"
  ssh ace "nix develop {{dbms_basedir}}/..#ace-cheri --command just -f {{dbms_basedir}}/dbms.just run_sqlite_ace '{{warehouses}}' '{{duration}}' '{{clients}}' '{{monitor}}'"

setup_ladybug sf="10":
  #!/usr/bin/env python
  import os
  import shutil
  import glob
  import subprocess
  import gzip

  sf = "{{sf}}"
  base_dir = "{{DATA_DIR}}/ladybug/dataset"
  target_dir = os.path.join(base_dir, f"ldbc-sf{sf}")

  if os.path.exists(target_dir) and os.listdir(target_dir):
    print(f"Dataset for SF{sf} already exists in {target_dir}")
    exit(0)

  url = f"https://datasets.ldbcouncil.org/snb-interactive-v1/social_network-sf{sf}-CsvBasic-StringDateFormatter.tar.zst"
  archive = f"social_network-sf{sf}-CsvBasic-StringDateFormatter.tar.zst"

  print(f"Downloading {url}...")
  subprocess.run(["wget", "-q", "--show-progress", url], check=True)

  print(f"Extracting {archive}...")
  subprocess.run(["tar", "--use-compress-program=unzstd", "-xf", archive], check=True)

  extracted_dir = archive.replace(".tar.zst", "")
  os.makedirs(target_dir, exist_ok=True)

  print("Organizing files...")

  for section in ["dynamic", "static"]:
    section_path = os.path.join(extracted_dir, section)
    if not os.path.exists(section_path):
      continue

    for item in os.listdir(section_path):
      source_path = os.path.join(section_path, item)
      if os.path.isfile(source_path):
        shutil.move(source_path, os.path.join(target_dir, item))

  # Cleanup
  shutil.rmtree(extracted_dir)
  os.remove(archive)

build_ladybug:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/ladybug
  export EXTRA_CMAKE_FLAGS="-DBUILD_BENCHMARK=TRUE"
  ARCH=dynamic make clean
  ARCH=dynamic make -j release
  ARCH=dynamic make -j python
  ARCH=mte make clean
  ARCH=mte make -j release
  ARCH=mte make -j python
  ARCH=cheri make clean
  ARCH=cheri make -j release
  ARCH=cheri make -j python
  ARCH=static make clean
  ARCH=static make -j release
  ARCH=static make -j python

run_ladybug_ace threads="4" sf="10" monitor="false":
  #!/usr/bin/env bash
  set -eu pipefail
  export CSV_DIR="{{DATA_DIR}}/ladybug/dataset/"
  export SCALE_FACTOR="{{sf}}"

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    PAGE_SIZE=$(getconf PAGESIZE)
    csv_output="${result_dir}/ladybug_mem_footprint.csv"
  fi

  for suffix in "static" "cheri"; do
    build_root="{{dbms_basedir}}/ladybug/build-${suffix}"
    serialized_root="${build_root}/ldbc-serialized"
    rm -rf "${serialized_root}"
    mkdir -p "${serialized_root}"
    export SERIALIZED_DIR="${serialized_root}"
    echo "=== Executing $suffix - threads: {{threads}} ==="
    
    PYTHONPATH="{{dbms_basedir}}/ladybug/tools/python_api/tools/python_api/build-${suffix}:${PYTHONPATH:-}" \
      DRY_RUN=true python3 {{dbms_basedir}}/ladybug/benchmark/benchmark_runner.py --dataset ldbc-sf{{sf}} --thread {{threads}} &
    server_pid=$!
    
    if [[ "{{monitor}}" == "true" ]]; then
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        pgid=$(ps -o pgid= -p $server_pid 2>/dev/null | tr -d ' ')
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -n "$pgid" ]]; then
            total_pages=0
            for pid in $(pgrep -g $pgid 2>/dev/null); do
              if [[ -r "/proc/$pid/statm" ]]; then
                rss_pages=$(awk '{print $2}' "/proc/$pid/statm" 2>/dev/null || true)
                if [[ -n "$rss_pages" ]]; then
                  total_pages=$((total_pages + rss_pages))
                fi
              fi
            done
            if [[ "$total_pages" -gt "$peak_rss_pages" ]]; then
              peak_rss_pages=$total_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi
    
    wait $server_pid || true
    
    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "${suffix},ldbc-sf{{sf}},${final_peak}" >> "${csv_output}"
    fi
  done

run_ladybug_eliza threads="4" sf="10" monitor="false":
  #!/usr/bin/env bash
  set -eu pipefail
  export CSV_DIR="{{DATA_DIR}}/ladybug/dataset/"
  export SCALE_FACTOR="{{sf}}"

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    PAGE_SIZE=$(getconf PAGESIZE)
    csv_output="${result_dir}/ladybug_mem_footprint.csv"
  fi

  for suffix in "dynamic" "mte"; do
    tunables=""
    if [[ "${suffix}" == "mte" ]]; then
      tunables="glibc.mem.tagging=3"
    fi
    build_root="{{dbms_basedir}}/ladybug/build-${suffix}"
    serialized_root="${build_root}/ldbc-serialized"
    rm -rf "${serialized_root}"
    mkdir -p "${serialized_root}"
    export SERIALIZED_DIR="${serialized_root}"
    echo "=== Executing $suffix - threads: {{threads}} ==="
    
    PYTHONPATH="{{dbms_basedir}}/ladybug/tools/python_api/tools/python_api/build-${suffix}:${PYTHONPATH:-}" GLIBC_TUNABLES="${tunables}" \
      DRY_RUN=true python3 {{dbms_basedir}}/ladybug/benchmark/benchmark_runner.py --dataset ldbc-sf{{sf}} --thread {{threads}} &
    server_pid=$!
    
    if [[ "{{monitor}}" == "true" ]]; then
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        pgid=$(ps -o pgid= -p $server_pid 2>/dev/null | tr -d ' ')
        while kill -0 $server_pid 2>/dev/null; do
          if [[ -n "$pgid" ]]; then
            total_pages=0
            for pid in $(pgrep -g $pgid 2>/dev/null); do
              if [[ -r "/proc/$pid/statm" ]]; then
                rss_pages=$(awk '{print $2}' "/proc/$pid/statm" 2>/dev/null || true)
                if [[ -n "$rss_pages" ]]; then
                  total_pages=$((total_pages + rss_pages))
                fi
              fi
            done
            if [[ "$total_pages" -gt "$peak_rss_pages" ]]; then
              peak_rss_pages=$total_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi
    
    wait $server_pid || true
    
    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      echo "${suffix},ldbc-sf{{sf}},${final_peak}" >> "${csv_output}"
    fi
  done

run_ladybug threads="4" sf="10" monitor="false":
  #!/usr/bin/env bash
  
  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    echo "variant,workload,peak_rss_bytes" > "${result_dir}/ladybug_mem_footprint.csv"
  fi
  
  just dbms::setup_ladybug "{{sf}}"
  just dbms::run_ladybug_eliza "{{threads}}" "{{sf}}" "{{monitor}}"
  ssh ace "nix develop {{dbms_basedir}}/..#ace-aarch64 --command  just -f {{dbms_basedir}}/dbms.just setup_ladybug {{sf}}"
  ssh ace "nix develop {{dbms_basedir}}/..#ace-aarch64 --command just -f {{dbms_basedir}}/dbms.just run_ladybug_ace '{{threads}}' '{{sf}}' '{{monitor}}'"

build_mysql:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/mysql
  cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-march=armv8.5-a" -DCMAKE_CXX_FLAGS="-march=armv8.5-a"
  cmake --build build/release -j
  cmake -S . -B build/release-mte -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-march=armv8.5-a+memtag -DMTE -isystem {{dbms_basedir}}/../utils" -DCMAKE_CXX_FLAGS="-march=armv8.5-a+memtag -DMTE -isystem {{dbms_basedir}}/../utils"
  cmake --build build/release-mte -j

# Run TPC-C for mysql
run_mysql monitor="false":
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

  if [[ "{{monitor}}" == "true" ]]; then
    result_dir="{{dbms_basedir}}/../results/dbms_rss"
    mkdir -p "${result_dir}"
    PAGE_SIZE=$(getconf PAGESIZE)
    csv_output="${result_dir}/mysql_mem_footprint.csv"
    echo "variant,workload,peak_rss_bytes" > "${csv_output}"
  fi

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

    if [[ "{{monitor}}" == "true" ]]; then
      temp_peak=$(mktemp)
      echo 0 > "$temp_peak"
      
      (
        peak_rss_pages=0
        while kill -0 $mysqld_pid 2>/dev/null; do
          if [[ -r "/proc/$mysqld_pid/statm" ]]; then
            rss_pages=$(awk '{print $2}' "/proc/$mysqld_pid/statm" 2>/dev/null || true)
            if [[ -n "$rss_pages" ]] && [ "$rss_pages" -gt "$peak_rss_pages" ]; then
              peak_rss_pages=$rss_pages
            fi
          fi
          sleep 0.1
        done
        peak_bytes=$(( peak_rss_pages * PAGE_SIZE ))
        echo "$peak_bytes" > "$temp_peak"
      ) &
      monitor_pid=$!
    fi

    ${sysbench_bin} ${oltp_script} ${sysbench_opts} \
      --threads="${threads}" \
      --time="${duration}" \
      --report-interval="${report_interval}" \
      --mysql-ignore-errors=1213 \
      run

    ${sysbench_bin} ${oltp_script} ${sysbench_opts} cleanup

    ${mysqladmin_cmd} shutdown
    trap - EXIT

    if [[ "{{monitor}}" == "true" ]]; then

      wait $monitor_pid 2>/dev/null || true
      
      final_peak=$(cat "$temp_peak")
      rm -f "$temp_peak"
      variant_name="dynamic"
      [[ "${suffix}" == "-mte" ]] && variant_name="mte"
      echo "${variant_name},sysbench,${final_peak}" >> "${csv_output}"
    fi
  done

run_all_rss:
  #!/usr/bin/env bash
  just dbms::run_duckdb 100 true
  just dbms::run_redis 100000 100000 true
  just dbms::run_leveldb 100000 100000 1 true
  just dbms::run_sqlite 1 60 1 true
  just dbms::run_mysql true
  just dbms::run_ladybug 4 10 true

dbms_basedir := source_dir()
TPCH_SF := "10" # ~~2.5GB according to DuckDB website

build_duckdb arch="aarch64":
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/duckdb
  ARCH="{{arch}}" make -j release

setup_duckdb sf="10":
  #!/usr/bin/env bash
  # Note: this only works for 1, 3, 10, 30, 100, 300, 1000 and 3000 (refer to https://duckdb.org/docs/stable/core_extensions/tpch#pre-generated-datasets)
  # otherwise we need to generate them ourselves
  if [[ ! -e tpch-sf{{sf}}.db ]]; then
    wget https://blobs.duckdb.org/data/tpch-sf{{sf}}.db
  fi

run_duckdb sf="10" mte="false":
  #!/usr/bin/env bash
  if [[ "{{mte}}" = "true" ]] then
    export GLIBC_TUNABLES="glibc.mem.tagging=3"
  fi
  for q in `seq 1 2`
  do
    {{dbms_basedir}}/duckdb/build/release/duckdb {{dbms_basedir}}/tpch-sf{{sf}}.db -no-stdin -c 'set enable_progress_bar=false' -c '.timer on' -c ".read {{dbms_basedir}}/workloads/TPCH/q$q.sql" | grep "Run Time" | awk -v query=$q '{printf "q%s,%s\n", query, $5}'
  done

build_redis:
  #!/usr/bin/env bash
  cd {{dbms_basedir}}/redis
  make -j

run_redis:
  #!/usr/bin/env bash
  for l in "a b c d e f"
  do
    {{dbms_basedir}}/redis/src/redis-server > /dev/null 2> /dev/null &

    ycsb.sh load redis -s -P dbms/workloads/YCSB/workload$l -p "redis.host=127.0.0.1" -p "redis.port=6379"
    ycsb.sh run redis -s -P dbms/workloads/YCSB/workload$l -p "redis.host=127.0.0.1" -p "redis.port=6379"

    {{dbms_basedir}}/redis/src/redis-cli shutdown
    rm -f {{dbms_basedir}}/redis/dump.rdb
  done

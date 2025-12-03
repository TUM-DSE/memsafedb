structs_basedir := source_dir()

build_CLHT arch="aarch64":
  #!/usr/bin/env bash
  mkdir -p {{structs_basedir}}/lib {{structs_basedir}}/include
  cd {{structs_basedir}}/CLHT
  make ARCH={{arch}} clht_lf
  cp libclht.a ../lib/libclht_lf_{{arch}}.a
  cp include/clht.h ../include 

clean_CLHT:
  #!/usr/bin/env bash
  rm -f {{structs_basedir}}/lib/libclht_lf*.a
  cd {{structs_basedir}}/CLHT
  make clean

build_ART:
  #!/usr/bin/env bash
  cp -r {{structs_basedir}}/adaptive-radix-tree/include/* {{structs_basedir}}/include

clean_ART:
  #!/usr/bin/env bash
  rm -rf {{structs_basedir}}/include/art {{structs_basedir}}/include/art.hpp

build_skiplist:
  #!/usr/bin/env bash
  cp {{structs_basedir}}/skiplist/arena.h {{structs_basedir}}/skiplist/skiplist.h {{structs_basedir}}/skiplist/random.h {{structs_basedir}}/include
  
clean_skiplist:
  #!/usr/bin/env bash
  rm -f {{structs_basedir}}/include/skiplist.h {{structs_basedir}}/include/arena.h {{structs_basedir}}/include/random.h

build_btree:
  #!/usr/bin/env bash
  cp {{structs_basedir}}/btree/btree.hpp {{structs_basedir}}/include

clean_btree:
  #!/usr/bin/env bash
  rm -f {{structs_basedir}}/include/btree.hpp

build_all_structs arch="aarch64": (build_CLHT arch) build_ART build_skiplist build_btree

clean_all_structs: clean_CLHT clean_ART clean_skiplist clean_btree

build_ycsb arch="aarch64": clean_all_structs (build_all_structs arch)
  #!/usr/bin/env bash
  cd {{structs_basedir}}/YCSB
  git submodule update --init --recursive
  make ARCH={{arch}} -j

clean_ycsb:
  #!/usr/bin/env bash
  cd {{structs_basedir}}/YCSB
  make clean

build_queue_bench arch="aarch64":
  #!/usr/bin/env bash
  cd {{structs_basedir}}/queue_bench
  make ARCH={{arch}} -j

clean_queue_bench:
  #!/usr/bin/env bash
  cd {{structs_basedir}}/queue_bench
  make clean

full_build arch="aarch64": clean_ycsb clean_queue_bench (build_ycsb arch) (build_queue_bench arch)

full_clean: clean_all_structs clean_ycsb clean_queue_bench

run_ycsb db="" workload="YCSB/workloads/workloada" threads="1" rec_count="1000000" op_count="1000000" req_distrib="zipfian" extra_args='':
  #!/usr/bin/env bash  
  GLIBC_TUNABLES="glibc.mem.tagging=3" {{structs_basedir}}/YCSB/ycsb -load -run -s -db {{db}} -P {{workload}} -p threadcount={{threads}} -p recordcount={{rec_count}} -p operationcount={{op_count}} -p requestdistribution={{req_distrib}} {{extra_args}}

run_queue_bench nb_ops="100000" nb_threads="2":
  #!/usr/bin/env bash
  GLIBC_TUNABLES="glibc.mem.tagging=3" {{structs_basedir}}/queue_bench/queue_bench {{nb_ops}} {{nb_threads}}

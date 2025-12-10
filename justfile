proot := source_dir()
user := `whoami`
host := `hostname`
# bin_dir assumes that the directory is not shared among the two hosts
bin_dir := "/scratch/"+user+"/memsafedb_bin/" # if modified, replicate this in execute_bench.py

mod structs 'datastructures/structs.just'
mod dbms 'dbms/dbms.just'


build_structs arch="aarch64":
  #!/usr/bin/env bash
  just structs::build_all_benchmarks {{arch}}
  mkdir -p {{bin_dir}}
  cp {{proot}}/datastructures/YCSB/ycsb {{bin_dir}}/ycsb_{{arch}}
  cp {{proot}}/datastructures/queue_bench/queue_bench {{bin_dir}}/queue_bench_{{arch}} 

#!/usr/bin/env bash

CORES_FROM=12
CORES_TO=15
PINNED_CORES="$CORES_FROM-$CORES_TO"

declare -A governors

mkdir -p results/mte

for i in $(seq $CORES_FROM $CORES_TO); do
  governors[$i]=$(cat /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor)
  echo performance | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
done

taskset -c $CORES_FROM ./insts/target/release/arch-tests -m mte -o results/mte/insts_mte.json

SIZES=8192,32768,262144,2097152
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/ptr_chase_normal --sizes $SIZES --iterations 100000 --min-iterations 500 > results/mte/ptr_chase_no_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/ptr_chase_normal --enable-mte sync --sizes $SIZES --iterations 100000 --min-iterations 500 > results/mte/ptr_chase_sync_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/ptr_chase_normal --enable-mte async --sizes $SIZES --iterations 100000 --min-iterations 500 > results/mte/ptr_chase_async_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/ptr_chase_normal --enable-mte no_tagging --sizes $SIZES --iterations 100000 --min-iterations 500 > results/mte/ptr_chase_no_tagging_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/ptr_chase_normal --enable-mte prctl_only --sizes $SIZES --iterations 100000 --min-iterations 500 > results/mte/ptr_chase_prctl_only_mte.csv

SIZES=65536,2097152,33554432,268435456
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memcpy_normal --sizes $SIZES --iterations 30000 --min-iterations 100 > results/mte/memcpy_no_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memcpy_normal --enable-mte sync --sizes $SIZES --iterations 30000 --min-iterations 100 > results/mte/memcpy_sync_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memcpy_normal --enable-mte async --sizes $SIZES --iterations 30000 --min-iterations 100 > results/mte/memcpy_async_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memcpy_normal --enable-mte no_tagging --sizes $SIZES --iterations 30000 --min-iterations 100 > results/mte/memcpy_no_tagging_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memcpy_normal --enable-mte prctl_only --sizes $SIZES --iterations 30000 --min-iterations 100 > results/mte/memcpy_prctl_only_mte.csv

echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memset_normal --sizes $SIZES --iterations 50000 --min-iterations 100 > results/mte/memset_no_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memset_normal --enable-mte sync --sizes $SIZES --iterations 50000 --min-iterations 100 > results/mte/memset_sync_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memset_normal --enable-mte async --sizes $SIZES --iterations 50000 --min-iterations 100 > results/mte/memset_async_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memset_normal --enable-mte no_tagging --sizes $SIZES --iterations 50000 --min-iterations 100 > results/mte/memset_no_tagging_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memset_normal --enable-mte prctl_only --sizes $SIZES --iterations 50000 --min-iterations 100 > results/mte/memset_prctl_only_mte.csv

echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memread_normal --sizes $SIZES --iterations 10000 --min-iterations 100 > results/mte/memread_no_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memread_normal --enable-mte sync --sizes $SIZES --iterations 10000 --min-iterations 100 > results/mte/memread_sync_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memread_normal --enable-mte async --sizes $SIZES --iterations 10000 --min-iterations 100 > results/mte/memread_async_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memread_normal --enable-mte no_tagging --sizes $SIZES --iterations 10000 --min-iterations 100 > results/mte/memread_no_tagging_mte.csv
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
taskset -c $PINNED_CORES ./c_benches/build/memread_normal --enable-mte prctl_only --sizes $SIZES --iterations 10000 --min-iterations 100 > results/mte/memread_prctl_only_mte.csv

taskset -c $PINNED_CORES ./c_benches/build/mte_caches 0 > results/mte/mte_caches.txt
taskset -c $PINNED_CORES ./c_benches/build/mte_caches 1 >> results/mte/mte_caches.txt
taskset -c $PINNED_CORES ./c_benches/build/mte_caches 2 >> results/mte/mte_caches.txt

taskset -c $PINNED_CORES ./c_benches/build/mte_alloc --sizes 16,32,64,128,256,512,1024,2048,4096,8192,16384,32768,65536,131072,262144,524288 --num-allocs 10000 --iterations 200 --label default > results/mte/mte_alloc_default.csv
GLIBC_TUNABLES="glibc.mem.tagging=3" taskset -c $PINNED_CORES ./c_benches/build/mte_alloc --sizes 16,32,64,128,256,512,1024,2048,4096,8192,16384,32768,65536,131072,262144,524288 --num-allocs 10000 --iterations 200 --label MTE > results/mte/mte_alloc_tagging.csv

run_perf() {
    local output="$1"
    local name="$2"
    local op="$3"

    echo "Running: $name"
    echo "[$name]" >> "$output"

    taskset -c $PINNED_CORES perf stat -e cycles,instructions,cache-references,cache-misses,\
L1-dcache-loads,L1-dcache-load-misses,\
L1-dcache-stores,branches,branch-misses \
        ./c_benches/build/stzg_vs_memset "$op" 2>> "$output"

    echo "" >> "$output"
}

echo "" > results/mte/perf_ctrs.txt
run_perf results/mte/perf_ctrs.txt "memset" 1
run_perf results/mte/perf_ctrs.txt "stzg" 2
run_perf results/mte/perf_ctrs.txt "stgp" 3
run_perf results/mte/perf_ctrs.txt "stnp" 4
run_perf results/mte/perf_ctrs.txt "stp" 5

run_perf_test() {
    local bench=$1
    local mode=$2
    local size=$3
    local output_file="results/mte/perf-${bench}_${mode}.txt"

    # 2MB (beyond L2 cache)
    taskset -c $PINNED_CORES perf stat -e cycles,instructions,cache-misses,L1-dcache-load-misses,stalled-cycles-frontend,stalled-cycles-backend \
        ./c_benches/build/${bench} --enable-mte $mode --sizes $size --iterations 100 \
        2> "$output_file"

    echo ""
}

run_perf_test "ptr_chase_normal" "off" 2097152
run_perf_test "ptr_chase_normal" "sync" 2097152
run_perf_test "ptr_chase_normal" "async" 2097152
run_perf_test "ptr_chase_normal" "no_tagging" 2097152
run_perf_test "ptr_chase_normal" "prctl_only" 2097152
run_perf_test "memcpy_normal" "off" 268435456
run_perf_test "memcpy_normal" "sync" 268435456
run_perf_test "memcpy_normal" "async" 268435456
run_perf_test "memcpy_normal" "no_tagging" 268435456
run_perf_test "memcpy_normal" "prctl_only" 268435456
run_perf_test "memset_normal" "off" 268435456
run_perf_test "memset_normal" "sync" 268435456
run_perf_test "memset_normal" "async" 268435456
run_perf_test "memset_normal" "no_tagging" 268435456
run_perf_test "memset_normal" "prctl_only" 268435456
run_perf_test "memread_normal" "off" 268435456
run_perf_test "memread_normal" "sync" 268435456
run_perf_test "memread_normal" "async" 268435456
run_perf_test "memread_normal" "no_tagging" 268435456
run_perf_test "memread_normal" "prctl_only" 268435456


for i in $(seq $CORES_FROM $CORES_TO); do
  echo "${governors[$i]}" | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
done


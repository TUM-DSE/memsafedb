#!/usr/bin/env bash

mkdir -p results

./arch-tests -m cheri -o results/insts_morello.json

SIZES=4096,32768,262144,1048576,2097152
./build/ptr_chase_normal --sizes $SIZES --iterations 5000 > results/ptr_chase_normal.csv
./build/ptr_chase_purecap --sizes $SIZES --iterations 5000 > results/ptr_chase_purecap.csv
./build/atomic_ptr_table_normal --sizes $SIZES --iterations 10 > results/atomic_ptr_table_normal.csv
./build/atomic_ptr_table_purecap --sizes $SIZES --iterations 10 > results/atomic_ptr_table_purecap.csv

SIZES=65536,1048576,8388608,33554432 #,268435456
./build/memcpy_normal --sizes $SIZES --iterations 50000 > results/memcpy_normal.csv
./build/memcpy_purecap --sizes $SIZES --iterations 50000 > results/memcpy_purecap.csv

./build/memset_normal --sizes $SIZES --iterations 50000 > results/memset_normal.csv
./build/memset_purecap --sizes $SIZES --iterations 50000 > results/memset_purecap.csv

./build/memread_normal --sizes $SIZES --iterations 10000 > results/memread_normal.csv
./build/memread_purecap --sizes $SIZES --iterations 10000 > results/memread_purecap.csv

./build/cheri_caches > results/cheri_caches.txt

./build/cheri_narrow_bounds --objects 256,1024,16384,32768 --iterations 1000000000 > results/narrow_base.csv
./build/cheri_narrow_bounds --objects 256,1024,16384,32768 --iterations 1000000000 > results/narrow_cheri.csv

./build/cheri_ldxr_stxr --iterations 200 --inner 200000 > results/cheri_ldxr_stxr.csv

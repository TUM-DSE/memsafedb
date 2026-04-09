#!/usr/bin/env bash

mkdir -p results

./arch-tests -m clock-test -o results/insts_gravitron.json


SIZES=4096,32768,262144,2097152
./build/ptr_chase_normal --sizes $SIZES --iterations 5000 > results/ptr_chase_normal.csv
#./build/atomic_ptr_table_normal --sizes $SIZES --iterations 10 > results/atomic_ptr_table_normal.csv

SIZES=65536,1048576,8388608,33554432 #,268435456
./build/memcpy_normal --sizes $SIZES --iterations 50000 > results/memcpy_normal.csv

./build/memset_normal --sizes $SIZES --iterations 50000 > results/memset_normal.csv

./build/memread_normal --sizes $SIZES --iterations 50000 > results/memread_normal.csv

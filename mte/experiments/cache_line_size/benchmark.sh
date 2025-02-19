#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

CORE=0

# 256MB - 2GB; div 4 is because we use 4 byte integer for the array
ARRAY_SIZES=()
for ((i = 28; i <= 31; i++)); do
  ARRAY_SIZES+=($(( (2**i) / 4 )))
done

STRIDES=(1 2 4 8 16 32 64 128 256 512)

rm -f result_load.csv
touch result_load.csv

echo "len;stride;duration" >> result_load.csv
for size in "${ARRAY_SIZES[@]}"; do
    for stride in "${STRIDES[@]}"; do
        taskset -c $CORE  ./cache_line_size_load 10 $size $stride  | tee -a result_load.csv
    done
done

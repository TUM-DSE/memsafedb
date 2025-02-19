#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

CORE=0

ARRAY_SIZES=()
for ((i = 1; i < 20; i++)); do
  ARRAY_SIZES+=($((1024 * 2**i)))
done

rm -f result.csv
touch result.csv

echo "len;steps;duration" >> result.csv
for size in "${ARRAY_SIZES[@]}"; do
    taskset -c $CORE  ./cache_size_load 10 $size 2500000000 | tee -a result.csv
done

rm -f result_write.csv
touch result_write.csv

echo "len;steps;duration" >> result_write.csv
for size in "${ARRAY_SIZES[@]}"; do
    taskset -c $CORE  ./cache_size_write 10 $size 2500000000 | tee -a result_write.csv
done

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

run_experiment() {
    local executable=$1
    local output_file=$2

    rm -f "$output_file"
    touch "$output_file"
    echo "len;stride;duration" >> "$output_file"

    for size in "${ARRAY_SIZES[@]}"; do
        for stride in "${STRIDES[@]}"; do
            taskset -c "$CORE" "$executable" 10 "$size" "$stride" | tee -a "$output_file"
        done
    done
}


run_experiment "./cache_line_size_load" "result_load.csv"


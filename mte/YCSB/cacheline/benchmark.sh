#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "cacheline_load_untagged" 
  "cacheline_load_tagged"
)
missing=false

for file in "${files[@]}"; do
  if [[ ! -e "$file" ]]; then
    echo "Error: File '$file' is missing." >&2
    missing=true
  fi
done

if $missing; then
  exit 1
fi

ARRAY_SIZES=()
for ((i = 0; i < 20; i++)); do
  ARRAY_SIZES+=($((512 * 2**i)))
done


rm -f result_untagged.csv
touch result_untagged.csv

echo "len;steps;duration" >> result_untagged.csv
for size in "${ARRAY_SIZES[@]}"; do
  for i in {1..10}; do
    taskset -c 0 ./cacheline_load_untagged $size 30000000 | tee -a result_untagged.csv
  done
done


rm -f result_tagged.csv
touch result_tagged.csv
echo "len;steps;duration" >> result_tagged.csv
for size in "${ARRAY_SIZES[@]}"; do
  for i in {1..10}; do
    taskset -c 0 ./cacheline_load_tagged $size 30000000 | tee -a result_tagged.csv
  done
done

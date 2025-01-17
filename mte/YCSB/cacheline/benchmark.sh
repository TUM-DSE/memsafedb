#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "cacheline_untagged"
  "cacheline_tagged"
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

STEP=1
SEED=1337
STEPS=(1)

ARRAY_SIZES=()
for size in $(seq 32768 32768 1073741824); do # 16KB 16KB 1GB -> 32768 entries
  ARRAY_SIZES+=($size)
done

rm -f result_untagged.csv
touch result_untagged.csv
echo "size;seed;steps;sum;nano" >> result_untagged.csv

for size in "${ARRAY_SIZES[@]}"; do
  for i in {1..20}; do
    ./cacheline_untagged "$size" "$SEED" "$STEP" | tee -a result_untagged.csv
  done
done


rm -f result_tagged.csv
touch result_tagged.csv
echo "size;seed;steps;sum;nano" >> result_tagged.csv
for size in "${ARRAY_SIZES[@]}"; do
  for i in {1..20}; do
    ./cacheline_tagged "$size" "$SEED" "$STEP" | tee -a result_tagged.csv
  done
done


#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "cacheline_untagged"
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

SEED=1337
STEPS=(1 2 4 8 16 32)

ARRAY_SIZES=()
for size in $(seq 32768 32768 16777216); do
  ARRAY_SIZES+=($size)
done

touch result.csv
echo "size;seed;steps;sum;nano" >> result.csv

for size in "${ARRAY_SIZES[@]}"; do
  for step in "${STEPS[@]}"; do
    for i in {1..10}; do
      ./cacheline_untagged "$size" "$SEED" "$step" | tee -a result.csv
    done
  done
done


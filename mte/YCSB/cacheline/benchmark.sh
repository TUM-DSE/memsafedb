#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "simple"
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
for ((i = 0; i < 20; i++)); do
  ARRAY_SIZES+=($((512 * 2**i)))
done


rm -f data.csv
touch data.csv

echo "len;steps;duration" >> data.csv
for size in "${ARRAY_SIZES[@]}"; do
  ./storeonly $size 30000000
  ./storeonly $size 30000000
  for i in {1..10}; do
    ./storeonly $size 30000000 | tee -a data.csv
  done
done


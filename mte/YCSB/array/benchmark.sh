#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "sparse"
  "dense"
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
for size in $(seq 1048576 104857600 104857600); do 
  ARRAY_SIZES+=($size)
done

SEED=1337

rm -f result_sparse.csv
touch result_sparse.csv
for size in "${ARRAY_SIZES[@]}"; do
  for i in {1..20}; do
    ./sparse "$size" "$SEED" | tee -a result_sparse.csv
  done
done


rm -f result_dense.csv
touch result_dense.csv
for size in "${ARRAY_SIZES[@]}"; do
  for i in {1..20}; do
    ./sparse "$size" "$SEED" | tee -a result_dense.csv
  done
done




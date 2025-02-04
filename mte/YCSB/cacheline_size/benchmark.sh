#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "linesize" 
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

ARRAY_STRIDES=(1 2 4 8 16 32 64 128 256)
ARRAY_LEN=()
for ((i=10000; i<=700000; i+=10000)); do
    ARRAY_LEN+=($i)
done

rm -f result.csv
touch result.csv

echo "len;stride;duration" >> result.csv
for stride in ${ARRAY_STRIDES[@]}; do 
  for len in ${ARRAY_LEN[@]}; do 
    for i in {1..10}; do
      ./linesize $len $stride | tee -a result.csv
    done
  done
done

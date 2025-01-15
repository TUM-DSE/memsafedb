#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "COMPACT_TAGGED_NODES"
  "COMPACT_UNTAGGED_NODES"
  "LOOSE_TAGGED_NODES"
  "LOOSE_UNTAGGED_NODES"
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


touch result.txt
echo "--- COMPACT_TAGGED_NODES ---" >> result.txt
./COMPACT_TAGGED_NODES 10000 1337 | tee -a result.txt 

echo "--- COMPACT_UNTAGGED_NODES ---" >> result.txt
./COMPACT_UNTAGGED_NODES 10000 1337 | tee -a result.txt 

echo "--- LOOSE_TAGGED_NODES ---" >> result.txt
./LOOSE_TAGGED_NODES 10000 1337 | tee -a result.txt 

echo "--- LOOSE_UNTAGGED_NODES ---" >> result.txt
time ./LOOSE_UNTAGGED_NODES 10000 1337 | tee -a result.txt 


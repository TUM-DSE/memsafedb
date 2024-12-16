#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=("O2_TAGGED" "O2_UNTAGGED")
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
echo "---> O2_TAGGED" >> result.txt
./ycsb_O2_TAGGED -P "../workloads/workloada" -run -load -db exampledb | tee -a result.txt 
echo "---> O2_UNTAGGED" >> result.txt
./ycsb_O2_UNTAGGED -P "../workloads/workloada" -run -load -db exampledb | tee -a result.txt 

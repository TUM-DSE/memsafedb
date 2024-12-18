#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "O2_TAGGED" 
  "O2_TAGGED_GPROF" 
  "O2_UNTAGGED" 
  "O2_UNTAGGED_GPROF" 
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

echo "Cleaning up"
rm -f result.txt
rm -f result_gprof.txt

touch result.txt
echo "---> O2_TAGGED" >> result.txt
./O2_TAGGED -P "../workloads/workloada" -run -load -db chashtabledb | tee -a result.txt 
echo "---> O2_UNTAGGED" >> result.txt
./O2_UNTAGGED -P "../workloads/workloada" -run -load -db chashtabledb | tee -a result.txt 

rm -f gnom.out

touch result_gprof.txt

echo "---> O2_TAGGED_GPROF" >> result.txt
./O2_TAGGED_GPROF -P "../workloads/workloada" -run -load -db chashtabledb | tee -a result_gprof.txt 
gprof O2_TAGGED_GPROF gnom.out > O2_TAGGED_RESULT.txt

rm -f gnom.out
echo "---> O2_UNTAGGED_GPROF" >> result.txt
./O2_UNTAGGED_GPROF -P "../workloads/workloada" -run -load -db chashtabledb | tee -a result_gprof.txt 
gprof O2_UNTAGGED_GPROF gnom.out > O2_UNTAGGED_RESULT.txt

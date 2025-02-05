#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "cacheline_size_load_untagged" 
  "cacheline_size_load_tagged"
  "cacheline_size_load_untagged_complex_addr"
  "cacheline_size_load_tagged_complex_addr"
  "cacheline_size_load_tagged_ldg"
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

rm -f result_untagged.csv
touch result_untagged.csv
echo "len;stride;duration" >> result_untagged.csv
for stride in ${ARRAY_STRIDES[@]}; do 
  for len in ${ARRAY_LEN[@]}; do 
    for i in {1..10}; do
      taskset -c 0 ./cacheline_size_load_untagged $len $stride | tee -a result_untagged.csv
    done
  done
done


rm -f result_tagged.csv
touch result_tagged.csv
echo "len;stride;duration" >> result_tagged.csv
for stride in ${ARRAY_STRIDES[@]}; do 
  for len in ${ARRAY_LEN[@]}; do 
    for i in {1..10}; do
      taskset -c 0 ./cacheline_size_load_tagged $len $stride | tee -a result_tagged.csv
    done
  done
done


# Complex addressing

rm -f result_untagged_complex_addr.csv
touch result_untagged_complex_addr.csv
echo "len;stride;duration" >> result_untagged_complex_addr.csv
for stride in ${ARRAY_STRIDES[@]}; do 
  for len in ${ARRAY_LEN[@]}; do 
    for i in {1..10}; do
      taskset -c 0 ./cacheline_size_load_untagged_complex_addr $len $stride | tee -a result_untagged_complex_addr.csv
    done
  done
done


rm -f result_tagged_complex_addr.csv
touch result_tagged_complex_addr.csv
echo "len;stride;duration" >> result_tagged_complex_addr.csv
for stride in ${ARRAY_STRIDES[@]}; do 
  for len in ${ARRAY_LEN[@]}; do 
    for i in {1..10}; do
      taskset -c 0 ./cacheline_size_load_tagged_complex_addr $len $stride | tee -a result_tagged_complex_addr.csv
    done
  done
done




rm -f result_tagged_ldg.csv
touch result_tagged_ldg.csv
echo "len;stride;duration" >> result_tagged_ldg.csv
for stride in ${ARRAY_STRIDES[@]}; do 
  for len in ${ARRAY_LEN[@]}; do 
    for i in {1..10}; do
      taskset -c 0 ./cacheline_size_load_tagged_ldg $len $stride | tee -a result_tagged_ldg.csv
    done
  done
done

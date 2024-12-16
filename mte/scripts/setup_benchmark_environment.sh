#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <workloads_folder> <binaries_folder> <benchmark_script>"
  exit 1
fi

WORKLOADS_FOLDER=$1
BINARIES_FOLDER=$2
BENCHMARK_SCRIPT=$3

if [ ! -d "$WORKLOADS_FOLDER" ]; then
  echo "Error: Workloads folder '$WORKLOADS_FOLDER' does not exist."
  exit 1
fi

if [ ! -d "$BINARIES_FOLDER" ]; then
  echo "Error: Binaries folder '$BINARIES_FOLDER' does not exist."
  exit 1
fi

if [ ! -f "$BENCHMARK_SCRIPT" ]; then
  echo "Error: Benchmark script '$BENCHMARK_SCRIPT' does not exist."
  exit 1
fi

TEMP_DIR=$(mktemp -d)
echo "Setup benchmark environment $TEMP_DIR"

WORKLOADS_TEMP="$TEMP_DIR/workloads"
DB_TEMP="$TEMP_DIR/db"

mkdir -p "$WORKLOADS_TEMP"
mkdir -p "$DB_TEMP"

echo "--- Moved YCSB workloads."
rsync -av "$WORKLOADS_FOLDER"/* "$WORKLOADS_TEMP"/

echo "--- Moved binary files."
rsync -av --exclude='CMakeFiles' \
  --exclude='CMakeCache.txt' \
  --exclude='Makefile' \
  --exclude='cmake_install.cmake' \
  "$BINARIES_FOLDER"/* "$DB_TEMP"/

echo "--- Moved benchmark script."
rsync -av "$BENCHMARK_SCRIPT" "$DB_TEMP"/

echo "--- Run benchmark."
pushd "$DB_TEMP" > /dev/null
chmod +x "$(basename "$BENCHMARK_SCRIPT")"
./"$(basename "$BENCHMARK_SCRIPT")"
popd > /dev/null
echo "--- Finished benchmark."

rsync -av "$DB_TEMP"/result.txt "$BINARIES_FOLDER"/

rm -rf "$TEMP_DIR"

echo "--- Benchmark completed and temporary files removed."
echo "--- Transfer benchmark results back."

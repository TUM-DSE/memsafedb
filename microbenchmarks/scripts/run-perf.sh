#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <binary> [args...]" >&2
    exit 1
fi

BIN="$1"
shift

perf stat \
  -j \
  -r 5 \
  -e task-clock,context-switches,cpu-migrations,page-faults \
  -e cycles,instructions,branches,branch-misses \
  -e cache-references,cache-misses \
  -e L1-dcache-loads,L1-dcache-load-misses \
  -e LLC-loads,LLC-load-misses \
  -e dTLB-loads,dTLB-load-misses \
  -e iTLB-loads,iTLB-load-misses \
  -- "$BIN" "$@" \



#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

files=(
  "TAGGED_MALLOC"
  "UNTAGGED_MALLOC"
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

echo "--- [TAGGED_MALLOC] Verify mmap is not used ---"
strace ./TAGGED_MALLOC 1000 2>&1 | grep mmap | wc -l | { \
  read count; \
  if [ "$$count" -eq 7 ]; then \
    echo "PASSED"; \
  else \
    echo "FAILED"; \
  fi; \
}

echo "--- [UNTAGGED_MALLOC] Verify mmap is not used ---"
strace ./UNTAGGED_MALLOC 1000 2>&1 | grep mmap | wc -l | { \
  read count; \
  if [ "$$count" -eq 7 ]; then \
    echo "PASSED"; \
  else \
    echo "FAILED"; \
  fi; \
}

echo "--- [TAGGED_MALLOC] Run normal ---"
./TAGGED_MALLOC 1000

echo "--- [UNTAGGED_MALLOC] Run normal ---"
./UNTAGGED_MALLOC 1000
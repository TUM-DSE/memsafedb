bc_dir := source_dir()
results_dir := bc_dir + "/../results/bug_classes"
CHERI_HOST := "ace"
runs := "200"

# MTE: synchronous tag checks with glibc heap tagging (same as the DBMS runs).
mte_tunables := "glibc.mem.tagging=3"

help:
  just -l bugclasses

# List the bug cases of the suite
list:
  {{bc_dir}}/build/runner_baseline -l

# Build the baseline and MTE runners (eliza devshell, on the MTE host)
build_host:
  make -C {{bc_dir}} baseline mte

# Cross-compile the CHERI purecap runner (cross-compiler devshell)
build_cheri:
  make -C {{bc_dir}} cheri

# Run one configuration on this machine: baseline, mte, cheri
run config n=runs:
  #!/usr/bin/env bash
  set -euo pipefail
  mkdir -p {{results_dir}}
  case "{{config}}" in
    baseline|cheri) envs=() ;;
    mte) envs=("GLIBC_TUNABLES={{mte_tunables}}") ;;
    *) echo "unknown config {{config}}" >&2; exit 1 ;;
  esac
  env "${envs[@]+"${envs[@]}"}" {{bc_dir}}/build/runner_{{config}} -c {{config}} -n {{n}} \
    -o {{results_dir}}/{{config}}.csv

# Run the CHERI configuration on the Morello host (shared file system)
run_cheri n=runs:
  ssh {{CHERI_HOST}} "cd {{bc_dir}} && just bugclasses::run cheri {{n}}"

# Run every configuration (call from the MTE host)
run_all n=runs:
  just bugclasses::run baseline {{n}}
  just bugclasses::run mte {{n}}
  just bugclasses::run_cheri {{n}}

# Generate the LaTeX table from the CSVs
table:
  python3 {{bc_dir}}/../plots/bug_classes_table.py

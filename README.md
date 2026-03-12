# MemSafeDB — Artifact Evaluation

> This repository contains the artifact for the paper: *Should Your Database Systems Use Hardware-Assisted Memory Safety Extensions in Production?*

## Abstract

We present the first comprehensive, cross-layer evaluation of hardware-assisted
memory-safety extensions—Arm MTE and CHERI—applied to database systems.
Our study spans the full software stack: from microarchitecture and compiler/runtime/OS
layers, through core data structures (ART, B+Tree, CLHT, skiplist, linked list, queue),
to full-scale database systems (Redis, LevelDB, SQLite, MySQL, DuckDB, LadyBugDB).
We also conduct an extensive bug and CVE study of prominent database systems to
characterise the prevalence and impact of memory-safety vulnerabilities in production.

---

## Repository Structure

```
memsafedb/
├── bug_study/          # Bug & CVE scraping, LLM classification, export  →  Details: bug_study/README.md
├── microbenchmarks/    # Microarchitecture benchmarks (MTE, CHERI, MPK)  →  Details: microbenchmarks/README.md
├── datastructures/     # Data-structure benchmarks (YCSB, queue_bench)
├── dbms/               # Full DBMS source trees + benchmark harness
├── plots/              # Python plotting scripts
├── results/            # Output directory for all CSVs and PDFs
├── utils/              # Cross-compilation toolchain files
├── flake.nix           # Nix development environments (MTE + CHERI)
└── justfile            # Top-level task runner
```

### Prerequisites

All build environments are managed with [Nix](https://nixos.org/) flakes. Two physical
machines are assumed:

| Machine    | Alias  | Architecture          | Extension |
|------------|--------|-----------------------|-----------|
| MTE host   | `eliza`| ARMv8.6 (Ampere 1a)   | MTE       |
| CHERI host | `ace`  | ARMv8.2 (Morello)     | CHERI     |

Tasks are orchestrated with [`just`](https://github.com/casey/just):

```bash
just --list          # list all top-level recipes
just structs --list  # data-structure recipes
just dbms --list     # DBMS recipes
just bugs --list     # bug-study recipes
```

---

## Experiments

### 1 — Bug Study

We scrape bug reports and CVEs from upstream issue trackers (GitHub, Jira, MySQL bug
tracker, CVEProject) for 2015–2025, then classify them with an LLM (3× majority vote) to
identify memory-safety issues and their operational implications.
> **Full instructions:** [`bug_study/README.md`](bug_study/README.md)

### 2 — Microarchitecture Benchmarks

Instruction-level and memory-system microbenchmarks covering MTE, CHERI, PAC, and MPK,
run on the Morello board, Ampere server, and an x86 machine (MPK).
> **Full instructions:** [`microbenchmarks/README.md`](microbenchmarks/README.md)

### 3 — Data Structure Benchmarks

Six data structures (ART, B+Tree, CLHT, skiplist, linked list, queue) evaluated under
YCSB workloads and a concurrent queue benchmark.

```bash
# Build (run on each host):
just build_structs mte    # on eliza (MTE host)
just build_structs cheri  # on ace  (CHERI host)

# Run (orchestrated over SSH from the host with MTE):
cd datastructures
python3 execute_bench.py --extensions mte,cheri --repetitions 5
```

Results → `results/datastructures_<extension>.csv`

### 4 — Database System Benchmarks

Redis, LevelDB, SQLite, MySQL, DuckDB, and LadyBugDB under YCSB, TPC-C, TPC-H, and
LDBC SNB. Each DBMS is compiled in four variants: **dynamic** (MTE baseline), **mte**,
**static** (CHERI baseline), **cheri**.

```bash
just dbms prepare_local_data      # sync datasets to both hosts
just dbms build_<db>              # e.g. build_redis, build_duckdb, …
just dbms benchmark db=all repetitions=3
just dbms run_all_rss             # collect peak RSS for memory-overhead plot
```

Results → `results/` (per-DBMS CSVs) and `results/dbms_rss/` (memory footprint CSVs)

---

## Plotting

All figures are generated from `results/` CSVs by the scripts in `plots/`:

```bash
cd plots
python3 bug_analysis.py
python3 datastructures.py
python3 dbms.py
python3 memory_overhead.py
python3 compiler_instructions.py
python3 compiler_instruction_breakdown_table.py
python3 conclusion.py
```

Dependencies (`matplotlib`, `seaborn`, `pandas`, `numpy`, `scipy`, `natsort`) are
available in the Nix plotting shell:

```bash
nix develop .#plotter
```

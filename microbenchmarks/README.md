# Microarchitectural Benchmarks for CHERI-DB

This repository contains the microarchitectural benchmarks and plotting pipeline used to evaluate Arm MTE, CHERI (Morello), and Intel MPK.

## Repository structure

- `c_benches/`: C microbenchmarks for memory-access patterns and allocation behavior.
- `insts/`: instruction benchmarks for MTE, CHERI, PAC, and MPK.
- `scripts/`: evaluation scripts for the different machines used in the study.
- `plot_scripts/`: scripts that generate the paper figures and tables from `results/`.
- `results/`: collected benchmark outputs.
- `output/`: generated PDFs and LaTeX snippets.

## Benchmarks

### Instruction-level benchmarks

The Rust harness in `insts/` measures per-instruction throughput and, where relevant, latency.

- `MTE`: `irg`, `addg`, `subg`, `subp`, `stg`, `stzg`, `stgp`, `ldg`, and related instructions.
- `CHERI`: capability loads/stores, conversions, bounds manipulation, getters/setters, checks, sealing, and capability atomics.
- `PAC`: pointer authentication instructions such as `pacda`, `autda`, and `xpacd`.
- `MPK`: `rdpkru`, `wrpkru`, PKRU round trips, plus `pkey_alloc`, `pkey_free`, and `pkey_mprotect` costs.

The default instruction benchmark iteration count is very high (`1_600_000_000`) to make steady-state throughput measurements robust.

### Memory-system microbenchmarks

The C benchmarks model the kinds of access patterns that show up in database internals.

- `ptr_chase`: randomized linked-list traversal for pointer-heavy, latency-sensitive access.
- `memcpy`, `memset`, `memread`: linear streaming access over different working-set sizes.
- `atomic_ptr_table`: mixed reader/writer access to a pointer table using atomic loads/stores.
- `mte_alloc`: allocator overhead with and without MTE-enabled glibc tagging.
- `mte_caches`: initialization and cache-contention experiments for MTE tag stores.
- `cheri_caches`: cache/coherency effects when reading capabilities while another thread clears tags.
- `cheri_narrow_bounds`: cost of CHERI subobject bounds narrowing.
- `cheri_ldxr_stxr`: cost of exclusive load/store on plain values versus capabilities.

## Reproducing the benchmarks

We use `nix` to manage our dependencies.

```bash
nix develop
```

This shell provides the Morello toolchain, Rust toolchains/targets, plotting dependencies, `just`, and environment variables.

```bash
just build          # build C benchmarks and the Rust harness
just run_on_mte     # run the MTE experiments locally
just run_on_morello # sync to the Morello board, run remotely, fetch results
just run_on_x86     # run MPK experiments remotely
just run_on_gravitron
just plot           # regenerate PDFs and LaTeX tables in output/
```

Notes:

- The MTE scripts must be run from a machine that supports MTE.
- `run_on_morello`, `run_on_x86`, and `run_on_gravitron` use hostnames hardcoded in `Justfile`. You will need to adapt them to your own machines.

## Methodology

- Benchmarks warm up before timing to reduce cold-start noise.
- For the C benchmarks, iterations are scaled by working-set size so that larger inputs do not receive disproportionately little work.
- Small working sets receive extra samples to reduce variance.
- Several scripts pin execution to specific cores with `taskset` or thread affinity.
- The MTE evaluation script temporarily switches CPUs to the `performance` governor and drops page cache between runs.
- Cache-focused tests calibrate iteration counts to target a roughly fixed wall-clock duration per sample.
- Results are recorded as CSV or JSON and normalized later by the plotting scripts for the paper figures.

The experimental platforms are:

- **Morello**: 4-core Arm Morello evaluation board, used for CHERI measurements.
- **Ampere 1a**: 192-core server, used for MTE measurements.
- **x86_64**: Intel MPK platform for the appendix-style MPK measurements.
- **Gravitron**: Amazon Gravitron, used as a baseline for Morello.

## Results and plots

The repository already includes collected results in `results/` and generated artifacts in `output/`.

```bash
just plot # generate all plots from results
```


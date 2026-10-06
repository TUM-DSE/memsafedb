# Bug-Class Detection Suite

Small, self-contained reproductions of the memory-safety bug classes of the bug
study (`bug_study/`, paper App. B), used to check which classes MTE and CHERI
detect (paper Sec. 6.4). Each case is one function in `bugs.c`, tagged with
the class (table row) it belongs to; `runner.c` runs every case in a forked
child, repeatedly, and records how the run ended.

## Cases

`build/runner_baseline -l` lists them:

| Class                          | Cases                                                                 |
|--------------------------------|-----------------------------------------------------------------------|
| Heap buffer overflow           | `heap_overflow`, `heap_overflow_granule`, `heap_overflow_large`, `libc_memcpy_overflow` |
| Stack/global buffer overflow   | `stack_overflow`, `global_overflow`                                    |
| Out-of-bounds read/write       | `oob_read`, `oob_underflow`, `oob_nonadjacent`                         |
| Integer overflow to corruption | `int_overflow_alloc`                                                   |
| Use-after-free                 | `uaf_read`, `uaf_write`, `uaf_reuse`, `realloc_stale`                  |
| Double/invalid free            | `double_free`, `invalid_free`                                          |
| Null pointer dereference       | `null_deref`                                                           |
| Uninitialized memory access    | `uninit_read`                                                          |

## Configurations

| Config     | Build                                 | Run environment                             |
|------------|---------------------------------------|---------------------------------------------|
| `baseline` | plain clang                           | —                                           |
| `mte`      | `-march=armv8.5-a+memtag`, MTE glibc  | `GLIBC_TUNABLES=glibc.mem.tagging=3` (sync) |
| `cheri`    | purecap, musl                         | Morello Linux                               |

All builds use `-O1 -fno-builtin -fno-stack-protector` and disable
`_FORTIFY_SOURCE`, so the bugs stay in the binary and detections are
attributed to the mechanism under test.

## Outcomes

Each run is classified as one of:

| Outcome         | Meaning                                                              |
|-----------------|----------------------------------------------------------------------|
| `hw_trap`       | MTE tag fault (`mte_sync`/`mte_async`) or CHERI capability fault (`cheri_tag`, `cheri_bounds`, ...) |
| `runtime_abort` | allocator / libc check (glibc message, musl trap)                    |
| `crash`         | other fault (e.g., `segv_maperr`), same as without protection        |
| `hang`          | child timed out                                                      |
| `silent`        | completed: `corruption`, `leak`, or `no_effect`                      |

`timing` tells whether the event happened at the faulty `access`, `after` it,
or at `cleanup` (e.g., in `free`).

`plots/bug_classes_table.py` reduces each (configuration, class) to one
colored cell: detected at the access, partially detected (with an in-cell
note, e.g., the detection rate), caught by an allocator check, crash,
undetected, or "OS" (CHERI use-after-free detection needs capability
revocation, which Morello Linux lacks). For CHERI, `heap_overflow_large` is not
counted: the overflow stays within the padding of the rounded-up bounds and
cannot reach another object.

## Running

```bash
# On the MTE host, in the eliza devshell:
just bugclasses::build_host
# Cross-compile the CHERI runner (cross-compiler devshell):
just bugclasses::build_cheri
# Run everything (the CHERI config runs on the Morello host over ssh):
just bugclasses::run_all 200
# Table:
just bugclasses::table
```

Results: `results/bug_classes/<config>.csv`, `bug_classes_table.tex`,
`bug_classes_macros.tex`.

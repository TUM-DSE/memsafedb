# RangeSanitizer (RSan) build for the LevelDB motivation plot

Adds a `release-rsan` LevelDB `db_bench` variant — a software memory-safety
sanitizer to compare against ASan / MTE / CHERI. AArch64 only (eliza), using
RSan's explicit-tagging (Arm TBI) path.

## Derivations
- `nix/rsan/toolchain.nix` (`packages.rsan-toolchain`) — forked LLVM-16
  clang/lld + `tcmalloc-explicit`, pinned to vusec/rangesanitizer master.
  `CPATH`/`LIBRARY_PATH` point the freshly-built clang at glibc so its
  compiler-rt bootstrap finds libc headers on NixOS.
- `nix/rsan/leveldb.nix` (`packages.leveldb-rsan`) — the TUM-DSE leveldb fork
  (`leveldb-memsafedb`, pinned to the `dbms/leveldb` submodule commit) so the
  RSan `db_bench` is the *same* code as the release-asan/mte/cheri/dynamic
  points and its slowdown is comparable to the `release-dynamic` baseline.
  Built with the RSan clang and the flags from `examples/test-explicit.sh`:
  - `-flto=full -fsanitize=safe-stack` (RSan lives in the forked SafeStack pass;
    the pass runs at LTO time, so linking must use RSan's own `ld.lld` — we
    can't swap in a stock nixpkgs bintools wrapper).
  - link `-ltcmalloc_minimal` from the explicit-tagging tcmalloc.
  - the unwrapped RSan clang has no default paths on NixOS, so `leveldb.nix`
    supplies them by hand: `-isystem glibc` + `--gcc-toolchain=gcc` (headers,
    crtbegin, libgcc.a, libstdc++ headers), `-B glibc/lib` (CRT: Scrt1/crti/
    crtn), `-L gcc-lib` (libgcc_s, libstdc++.so), and for the binary to run
    `-Wl,-dynamic-linker,glibc/ld-linux-aarch64.so.1` + rpaths to glibc/gcc-lib.
  - flags with spaces go through `cmakeFlagsArray` (a plain `cmakeFlags` entry
    gets word-split, dropping `-ltcmalloc_minimal`).
  - configure probes link trivial no-unsafe-stack programs, which fail against
    the safestack runtime (undefined `__sizedstack_sizeclasses`); build them as
    static libs (`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`, no link), and
    force google/benchmark's run-based `HAVE_STD_REGEX`/`HAVE_STEADY_CLOCK`
    (`STATIC_LIBRARY` can't run them) — same as the fork's own build recipe.
  - `LEVELDB_BUILD_TESTS=OFF` (the fork's `db_bench` links google/benchmark, not
    gtest); `ninjaFlags = [ "db_bench" ]` builds only that target.

## Build
```bash
nix build .#rsan-toolchain   # heavy: full LLVM-16 build (~1-2h, lots of RAM)
nix build .#leveldb-rsan     # -> result/bin/db_bench
```

## Status
Source hashes are pinned; both derivations evaluate and the `leveldb-rsan`
source fetches correctly. The LLVM-16 clang/lld build compiles fully. Two
glibc-2.4x compat fixes were needed (upstream LLVM-16 assumes older glibc):
- tests disabled (`LLVM_INCLUDE_TESTS=OFF`, `COMPILER_RT_INCLUDE_TESTS=OFF`,
  `COMPILER_RT_BUILD_GWP_ASAN=OFF`) so the compiler-rt runtimes configure
  doesn't trip over the `check-gwp_asan -> scudo_standalone` test dependency;
- compiler-rt restricted to just what RSan links —
  `COMPILER_RT_SANITIZERS_TO_BUILD=safestack` plus XRAY/LIBFUZZER/MEMPROF/ORC/
  PROFILE off — so the unused C++-heavy components (asan/cfi/xray/fuzzer/orc,
  which need libc++ headers the unwrapped clang can't see) never build;
- `crypt.h` (moved to libxcrypt) added to `CPATH`, and a `postPatch` adds
  `throw()` to `safestack.cpp`'s `DECLARE_WRAPPER` alias of `pthread_create`
  (RSan's fork pulls `<pthread.h>`, whose noexcept decl clashes with the
  interceptor). Scoped to that one TU / one interceptor.

`COMPILER_RT_HAS_FNO_LTO_FLAG=ON` is forced: RSan repurposes compiler-rt's
`NO_LTO_FLAGS` to `-flto=full` (gated on that var) so the safestack *runtime*
is emitted as LLVM bitcode and joins the LTO module at link time — that's how
`finalize()` rewrites the runtime's `extern __sizedstack_ptrs/count/sizeclasses`
to the instrumented program's private arrays. The gating probe *links* a
trivial program, which fails on the unwrapped NixOS clang, so without the force
it defaults off and the runtime builds native → undefined `__sizedstack_*` at
the final db_bench link.

A second `postPatch` guards two unchecked null-derefs in RSan's SafeStack pass
(`SafeStack.cpp` `finalize()` / `createStackPtrCount()`): they look up the
runtime globals `kUnsafeStackPtrVar` / `kUnsafeStackPtrCountVar`, which only
exist once a module has unsafe-stack objects. A module without any (a trivial
`int main(){}`, which CMake's compiler/feature probes compile) segfaults the
linker under LTO. The guard makes such modules no-ops, so probes link normally
and no `CMAKE_TRY_COMPILE_TARGET_TYPE` workaround is needed.

Packaging uses `ninja install` (with `CMAKE_INSTALL_PREFIX=$out`,
`LLVM_INSTALL_TOOLCHAIN_ONLY=ON`) rather than copying the build tree, so the
output has relocatable binaries with sane RPATHs and no build-tree `.o` files
(hand-copying tripped nix's `/build` RPATH audit); the clang resource dir is
also copied explicitly to guarantee `libclang_rt.safestack*.a` is present.

`nix build .#rsan-toolchain` succeeds. `nix build .#leveldb-rsan` is a fast
build; the NixOS sysroot/runtime flags are pinned as above. Once
`result/bin/db_bench` runs, do the benchmark wiring below.

## Wiring into the benchmark (later)
Once `result/bin/db_bench` works, add a `release-rsan` arm to
`run_leveldb_bench` in `dbms/dbms.just`, the `rsan -> release-rsan` mapping in
`parse_leveldb_bench_output`, and a series in `plot_leveldb_motivation_slowdown`
(`plots/dbms.py`).

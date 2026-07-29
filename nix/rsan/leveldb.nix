# LevelDB db_bench built with RangeSanitizer, for the memory-safety motivation
# plot (a software-sanitizer point alongside ASan / MTE / CHERI).
# Uses the TUM-DSE fork (same db_bench as the release-asan/mte/cheri/dynamic
# points), pinned to the submodule commit so the RSan slowdown is comparable to
# the release-dynamic baseline. leveldbSrc (not `src`): callPackage would
# otherwise fill `src` from pkgs.src.
{ lib, stdenv, cmake, ninja, fetchFromGitHub, rsan-toolchain, glibc
, leveldbSrc ? fetchFromGitHub {
    owner = "TUM-DSE";
    repo = "leveldb-memsafedb";
    rev = "799c9f439461104f0c3b519b95ce212e0f73d669";  # branch memsafedb, matches submodule
    fetchSubmodules = true;  # third_party/{benchmark,googletest}
    hash = "sha256-2xTpEIhky4MmQLXei2uTucWfMcPr+LnQl1cFFycZd8g=";
  }
}:

let
  gccOut = stdenv.cc.cc;                 # gcc install: crtbegin*.o, libgcc.a, C++ headers
  gccLib = lib.getLib stdenv.cc.cc;      # split-off lib output: libgcc_s, libstdc++.so
  glibcDev = lib.getDev glibc;
  glibcLib = lib.getLib glibc;
  # The unwrapped RSan clang has no default paths on NixOS; supply glibc headers,
  # gcc (for crtbegin/libgcc/libstdc++ headers), and -B for glibc CRT objects.
  # glibc via -idirafter (not -isystem) so it lands *after* the gcc-toolchain
  # C++ headers: libstdc++'s <cstdlib> etc. do `#include_next <stdlib.h>`, which
  # only finds glibc if glibc is later in the search path.
  sysroot = "-idirafter ${glibcDev}/include --gcc-toolchain=${gccOut} -B${glibcLib}/lib";
  # AArch64 explicit-tagging flags, verbatim from examples/test-explicit.sh.
  cflags = "-O2 -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc "
    + "-fno-builtin-free -g -flto=full -fsanitize=safe-stack ${sysroot}";
  # Link: RSan's own lld (LTO runs the RSan pass), + glibc CRT/libc (-B,-L),
  # gcc's split-off libgcc_s/libstdc++ (-L), NixOS dynamic linker, and rpaths
  # so the binary actually runs (no /lib/ld-linux, no /lib/libc.so.6 on NixOS).
  ldflags = "-fuse-ld=lld -fsanitize=safe-stack --gcc-toolchain=${gccOut} "
    + "-B${glibcLib}/lib -L${glibcLib}/lib -L${gccLib}/lib "
    + "-Wl,-dynamic-linker,${glibcLib}/lib/ld-linux-aarch64.so.1 "
    + "-Wl,-rpath,${glibcLib}/lib -Wl,-rpath,${gccLib}/lib";
  tcmalloc = "-L${rsan-toolchain}/tcmalloc/lib -Wl,-rpath -Wl,${rsan-toolchain}/tcmalloc/lib -ltcmalloc_minimal";
in
stdenv.mkDerivation {
  pname = "leveldb-rsan";
  version = "memsafedb-rsan";
  src = leveldbSrc;

  nativeBuildInputs = [ cmake ninja ];

  # Build only db_bench (fork's db_bench links leveldb + google/benchmark, not
  # gtest), skipping test exes and the sqlite/kyoto benchmarks.
  ninjaFlags = [ "db_bench" ];

  cmakeFlags = [
    "-DCMAKE_C_COMPILER=${rsan-toolchain}/bin/clang"
    "-DCMAKE_CXX_COMPILER=${rsan-toolchain}/bin/clang++"
    "-DCMAKE_AR=${rsan-toolchain}/bin/llvm-ar"
    "-DCMAKE_RANLIB=${rsan-toolchain}/bin/llvm-ranlib"
    "-DCMAKE_BUILD_TYPE=Release"
    # Probes link trivial no-unsafe-stack programs against the safestack runtime
    # (undefined __sizedstack_sizeclasses) / as C (undefined __gxx_personality_v0);
    # build them as static libs (no link) so configure passes. The real db_bench
    # target still links + instruments normally.
    "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY"
    # google/benchmark probes regex via try_run, which STATIC_LIBRARY can't run;
    # force the results (same as the fork's own build recipe).
    "-DHAVE_STD_REGEX=1"
    "-DHAVE_STEADY_CLOCK=1"
    "-DBENCHMARK_ENABLE_WERROR=OFF"
    "-DLEVELDB_BUILD_BENCHMARKS=ON"
    "-DLEVELDB_BUILD_TESTS=OFF"   # fork's db_bench links google/benchmark, not gtest
    "-DLEVELDB_INSTALL=OFF"
    "-DBUILD_SHARED_LIBS=OFF"
    "-DHAVE_TCMALLOC=OFF"         # we link RSan's tcmalloc-explicit ourselves
    "-DHAVE_SNAPPY=OFF"
    "-DHAVE_CRC32C=OFF"
    "-DHAVE_ZSTD=OFF"
  ];

  # Flags contain spaces; cmakeFlagsArray preserves them (a plain cmakeFlags
  # list entry gets word-split, dropping -ltcmalloc_minimal etc).
  preConfigure = ''
    cmakeFlagsArray+=(
      "-DCMAKE_C_FLAGS=${cflags}"
      "-DCMAKE_CXX_FLAGS=${cflags}"
      "-DCMAKE_EXE_LINKER_FLAGS=${ldflags} ${tcmalloc}"
    )
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p $out/bin $out/lib
    cp "$(find . -maxdepth 2 -name db_bench -type f | head -1)" $out/bin/db_bench
    if [ -f libleveldb.a ]; then cp libleveldb.a $out/lib/; fi
    runHook postInstall
  '';

  meta = with lib; {
    description = "LevelDB db_bench (TUM-DSE fork) instrumented with RangeSanitizer (RSan)";
    platforms = [ "aarch64-linux" ];
  };
}

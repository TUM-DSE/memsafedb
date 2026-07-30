# RangeSanitizer (RSan) toolchain: forked LLVM-16 clang/lld + explicit-tagging
# tcmalloc. AArch64 only (eliza). Mirrors upstream install-all.sh.
{ lib, stdenv, fetchFromGitHub, cmake, ninja, python3, git
, autoconf, automake, libtool, which, glibc, libxcrypt }:

stdenv.mkDerivation {
  pname = "rsan-toolchain";
  version = "unstable-2025-11-04";

  src = fetchFromGitHub {
    owner = "vusec";
    repo = "rangesanitizer";
    rev = "8e9444b2f1efb155905e5004dd38834b8a4887cd";
    fetchSubmodules = false;  # only 'infra' (SPEC runner) is a submodule; unused here
    hash = "sha256-x+W5yvuLJ4KJjsR8PPw2+7lIZincARqQyduuXSFhnP4=";
  };

  nativeBuildInputs = [ cmake ninja python3 git autoconf automake libtool which ];

  dontConfigure = true;

  # LLVM-16 compiler-rt vs glibc 2.4x: RSan's safestack.cpp pulls <pthread.h>,
  # so the DECLARE_WRAPPER alias of pthread_create clashes with glibc's noexcept
  # decl. Add throw() to that alias (this TU only intercepts pthread_create).
  postPatch = ''
    sed -i '\|#include "interception/interception.h"| r /dev/stdin' \
      llvm-project-16/compiler-rt/lib/safestack/safestack.cpp <<'RSAN_EOF'
    #undef DECLARE_WRAPPER
    #define DECLARE_WRAPPER(ret_type, func, ...) \
        extern "C" ret_type func(__VA_ARGS__) throw() \
        __attribute__((weak, alias("__interceptor_" #func), visibility("default")));
    RSAN_EOF

    # RSan's SafeStack pass null-derefs in finalize()/createStackPtrCount when a
    # module has no unsafe-stack objects (e.g. a trivial `int main(){}`, which
    # CMake compiler/feature probes use). Guard the runtime-global lookups so
    # such modules become no-ops instead of segfaulting the linker under LTO.
    substituteInPlace llvm-project-16/llvm/lib/CodeGen/SafeStack.cpp \
      --replace 'assert(stackPointerArrayStatic);' 'if (stackPointerArrayStatic) {' \
      --replace 'stackPointerArrayStatic->eraseFromParent();' 'stackPointerArrayStatic->eraseFromParent(); }' \
      --replace 'GlobalVariable *gv = cast<GlobalVariable>(M.getNamedValue(varName));' 'GlobalVariable *gv = dyn_cast_or_null<GlobalVariable>(M.getNamedValue(varName)); if (!gv) return nullptr;'
  '';

  buildPhase = ''
    runHook preBuild

    # The freshly-built unwrapped clang builds compiler-rt but can't find libc
    # headers on NixOS; point it at glibc (+ libxcrypt for crypt.h) explicitly.
    export CPATH="${lib.getDev glibc}/include:${lib.getDev libxcrypt}/include"
    export LIBRARY_PATH="${lib.getLib glibc}/lib"

    cmake -S llvm-project-16/llvm -B llvm-build -GNinja \
      -DLLVM_ENABLE_PROJECTS="clang;lld" \
      -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX="$out" \
      -DLLVM_INSTALL_TOOLCHAIN_ONLY=ON \
      -DLLVM_PARALLEL_LINK_JOBS=1 \
      -DLLVM_TARGETS_TO_BUILD=AArch64 \
      -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON \
      -DLLVM_INCLUDE_TESTS=OFF \
      -DCOMPILER_RT_INCLUDE_TESTS=OFF \
      -DCOMPILER_RT_BUILD_GWP_ASAN=OFF \
      -DCOMPILER_RT_SANITIZERS_TO_BUILD=safestack \
      -DCOMPILER_RT_HAS_FNO_LTO_FLAG=ON \
      -DCOMPILER_RT_BUILD_XRAY=OFF \
      -DCOMPILER_RT_BUILD_LIBFUZZER=OFF \
      -DCOMPILER_RT_BUILD_MEMPROF=OFF \
      -DCOMPILER_RT_BUILD_ORC=OFF \
      -DCOMPILER_RT_BUILD_PROFILE=OFF \
      -DCLANG_ENABLE_STATIC_ANALYZER=OFF \
      -DCLANG_ENABLE_ARCMT=OFF
    ninja -C llvm-build

    ( cd tcmalloc-explicit && autoreconf -i && (./autogen.sh || true) )
    mkdir -p tcmalloc-expl-build
    ( cd tcmalloc-expl-build \
      && ../tcmalloc-explicit/configure --prefix="$PWD" \
      && make -j"$NIX_BUILD_CORES" && make install )

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    # Proper install: relocatable binaries, sane RPATHs, no build-tree .o files.
    ninja -C llvm-build install

    # Guarantee the compiler-rt resource dir (libclang_rt.safestack*.a) is
    # present even if the toolchain-only install skips the runtimes target.
    mkdir -p $out/lib/clang
    cp -r llvm-build/lib/clang/. $out/lib/clang/

    mkdir -p $out/tcmalloc
    cp -r tcmalloc-expl-build/lib $out/tcmalloc/lib
    if [ -d tcmalloc-expl-build/include ]; then
      cp -r tcmalloc-expl-build/include $out/tcmalloc/include
    fi
    runHook postInstall
  '';

  meta = with lib; {
    description = "RangeSanitizer toolchain: forked LLVM-16 clang/lld + explicit-tagging tcmalloc (AArch64)";
    homepage = "https://github.com/vusec/rangesanitizer";
    platforms = [ "aarch64-linux" ];
  };
}

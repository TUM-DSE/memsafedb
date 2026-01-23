cmake_minimum_required(VERSION 3.0)

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

if(NOT DEFINED ENV{MORELLO_CLANG_DIR} OR NOT DEFINED ENV{MORELLO_LLVM_DIR} OR NOT DEFINED ENV{MORELLO_SYSROOT})
    message(FATAL_ERROR "Environment variables MORELLO_CLANG_DIR (Phase 1), MORELLO_LLVM_DIR (Phase 2), and MORELLO_SYSROOT must be defined.")
endif()

set(COMPILER_DIR $ENV{MORELLO_CLANG_DIR})
set(RUNTIMES_DIR $ENV{MORELLO_LLVM_DIR})
set(SYSROOT_DIR         $ENV{MORELLO_SYSROOT})
set(GTEST_DIR $ENV{GTEST_DIR})

set(CMAKE_C_COMPILER   "${COMPILER_DIR}/bin/clang")
set(CMAKE_CXX_COMPILER "${COMPILER_DIR}/bin/clang++")
set(CMAKE_AR           "${COMPILER_DIR}/bin/ar")
set(CMAKE_RANLIB       "${COMPILER_DIR}/bin/ranlib")

set(CHERI_FLAGS "-march=morello -mabi=purecap --target=aarch64-linux-musl_purecap --sysroot=${SYSROOT_DIR} -stdlib=libc++ -nostdlib++ -unwindlib=libunwind --rtlib=compiler-rt")
set(CHERI_FLAGS "${CHERI_FLAGS} -isystem ${RUNTIMES_DIR}/include/c++/v1 -I${RUNTIMES_DIR}/include")
set(CHERI_FLAGS "${CHERI_FLAGS} -fno-omit-frame-pointer -funwind-tables -g")

if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/cheri-shim.h")
    set(CHERI_FLAGS "${CHERI_FLAGS} -include ${CMAKE_CURRENT_LIST_DIR}/cheri-shim.h")
endif()

set(CHERI_FLAGS "${CHERI_FLAGS} -fno-lto -DCHERI -D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE")
set(CHERI_WARNINGS "-Wno-cheri-inefficient -Wno-unused-command-line-argument -Wno-stack-protector-purecap-ignored")

set(CMAKE_C_FLAGS_INIT   "${CHERI_FLAGS} ${CHERI_WARNINGS}")
set(CMAKE_CXX_FLAGS_INIT "${CHERI_FLAGS} ${CHERI_WARNINGS}")

set(CRT_START "${SYSROOT_DIR}/lib/crt1.o ${SYSROOT_DIR}/lib/crti.o")
set(CRT_END   "${SYSROOT_DIR}/lib/crtn.o")
set(LIB_PATHS "-L${RUNTIMES_DIR}/lib -L${RUNTIMES_DIR}/lib/c++ -L${RUNTIMES_DIR}/lib/linux")
set(STD_LIBS "-Wl,--start-group -lc++ -lc++abi -lunwind -lc -lclang_rt.builtins-aarch64 -Wl,--end-group")
set(CHERI_LINK_FLAGS "${LINKER_SEARCH_PATH} -static -fuse-ld=lld -Wl,--allow-multiple-definition")

set(CMAKE_C_LINK_EXECUTABLE
    "<CMAKE_C_COMPILER> <FLAGS> <CMAKE_C_LINK_FLAGS> <LINK_FLAGS> -nostartfiles -nodefaultlibs ${CRT_START} <OBJECTS> -o <TARGET> ${LIB_PATHS} <LINK_LIBRARIES> ${STD_LIBS} ${CRT_END}")
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> -nostartfiles -nodefaultlibs ${CRT_START} <OBJECTS> -o <TARGET> ${LIB_PATHS} <LINK_LIBRARIES> ${STD_LIBS} ${CRT_END}")


set(CMAKE_EXE_LINKER_FLAGS_INIT    "${CHERI_LINK_FLAGS}")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "${CHERI_LINK_FLAGS} -Wl,--allow-shlib-undefined")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "${CHERI_LINK_FLAGS}")

set(CMAKE_FIND_ROOT_PATH ${SYSROOT_DIR} ${RUNTIMES_DIR})
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

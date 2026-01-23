cmake_minimum_required(VERSION 3.0)

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

if(NOT DEFINED ENV{BASE_CLANG_DIR} OR NOT DEFINED ENV{BASE_SYSROOT} OR NOT DEFINED ENV{BASE_HDRS} OR NOT DEFINED ENV{BASE_LIBCXX_DIR} OR NOT DEFINED ENV{BASE_LIBCXX_HDR} OR NOT DEFINED ENV{BASE_UNWIND_DIR})
    message(FATAL_ERROR "Environment variables BASE_CLANG_DIR, BASE_LIBCXX_DIR, BASE_LIBCXX_HDR, BASE_UNWIND_DIR, BASE_SYSROOT, and BASE_HDRS must be defined.")
endif()

set(COMPILER_DIR $ENV{BASE_CLANG_DIR})
set(RUNTIMES_DIR $ENV{BASE_LIBCXX_DIR})
set(RUNTIMES_HDR $ENV{BASE_LIBCXX_HDR})
set(MUSL_LIB_DIR $ENV{BASE_SYSROOT})
set(MUSL_INC_DIR $ENV{BASE_HDRS})
set(MUSL_UNWIND_DIR $ENV{BASE_UNWIND_DIR})

set(CMAKE_C_COMPILER   "${COMPILER_DIR}/bin/clang")
set(CMAKE_CXX_COMPILER "${COMPILER_DIR}/bin/clang++")
set(CMAKE_AR           "${COMPILER_DIR}/bin/ar")
set(CMAKE_RANLIB       "${COMPILER_DIR}/bin/ranlib")

set(ARCH_FLAGS "--target=aarch64-unknown-linux-musl --unwindlib=libunwind")

# C Flags
set(CMAKE_C_FLAGS_INIT "${ARCH_FLAGS} -I${MUSL_INC_DIR}/include -Wno-unused-command-line-argument")

# C++ Flags
# Note: we assume libc++ is available to clang
set(CMAKE_CXX_FLAGS_INIT "${ARCH_FLAGS} -I${RUNTIMES_HDR}/include/c++/v1 -I${MUSL_INC_DIR}/include -stdlib=libc++ -nostdlib++ -Wno-unused-command-line-argument -Wno-c99-extensions -Wno-bitwise-op-parentheses -Wno-shift-op-parentheses")

# Manual Construction of Linker Line for Static Build
# This ensures we pick up the musl crt files and libraries correctly
set(CRT_START "${MUSL_LIB_DIR}/crt1.o ${MUSL_LIB_DIR}/crti.o ${COMPILER_DIR}/resource-root/lib/linux/clang_rt.crtbegin-aarch64.o")
set(CRT_END   "${COMPILER_DIR}/resource-root/lib/linux/clang_rt.crtend-aarch64.o ${MUSL_LIB_DIR}/crtn.o")

# Lib search paths
set(LIB_PATHS "-L${MUSL_LIB_DIR} -L${RUNTIMES_DIR}/lib -L${MUSL_UNWIND_DIR}/lib -L${COMPILER_DIR}/resource-root/lib/linux")

# Standard Libraries to link
# We explicitly list them to control the order and static nature
set(STD_LIBS "-Wl,--start-group -lc++ -lc++abi -lunwind -lc -lclang_rt.builtins-aarch64 -Wl,--end-group")

# Base Linker Flags
set(LINK_FLAGS "${ARCH_FLAGS} -static")

set(CMAKE_C_LINK_EXECUTABLE
    "<CMAKE_C_COMPILER> <FLAGS> <CMAKE_C_LINK_FLAGS> <LINK_FLAGS> -nostartfiles -nodefaultlibs ${CRT_START} <OBJECTS> -o <TARGET> ${LIB_PATHS} <LINK_LIBRARIES> ${STD_LIBS} ${CRT_END}")

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> -nostartfiles -nodefaultlibs ${CRT_START} <OBJECTS> -o <TARGET> ${LIB_PATHS} <LINK_LIBRARIES> ${STD_LIBS} ${CRT_END}")

set(CMAKE_EXE_LINKER_FLAGS_INIT    "${LINK_FLAGS}")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "${LINK_FLAGS}")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "${LINK_FLAGS}")

set(CMAKE_FIND_ROOT_PATH ${MUSL_LIB_DIR} ${MUSL_INC_DIR} ${RUNTIMES_DIR} ${MUSL_UNWIND_DIR})
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

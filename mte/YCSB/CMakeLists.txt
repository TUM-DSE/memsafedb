cmake_minimum_required(VERSION 3.10)
project(ycsb-cpp LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "-pthread")

set(CMAKE_BUILD_TYPE Release)
set(CompilerFlags
        CMAKE_CXX_FLAGS
        CMAKE_CXX_FLAGS_DEBUG
        CMAKE_CXX_FLAGS_RELEASE
        CMAKE_C_FLAGS
        CMAKE_C_FLAGS_DEBUG
        CMAKE_C_FLAGS_RELEASE
        )

option(EXAMPLEDB "Include the example files in the build" OFF)


file(GLOB_RECURSE YCSB_CORE_SRC "core/*.cc")

if(EXAMPLEDB)
    file(GLOB_RECURSE YCSB_EXAMPLEDB_SRC "example/*.cc")
    list(APPEND YCSB_CORE_SRC ${YCSB_EXAMPLEDB_SRC})
endif()

include(FindThreads)

add_executable(ycsb ${YCSB_CORE_SRC})
target_include_directories(ycsb PRIVATE ${PROJECT_SOURCE_DIR})
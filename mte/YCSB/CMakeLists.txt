cmake_minimum_required(VERSION 3.10)
project(ycsb-cpp LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "-pthread")
#set(CMAKE_CXX_FLAGS "-pthread -march=armv8.5-a+memtag -fsanitize=memtag-heap")


option(EXAMPLEDB "Include the example files in the build" OFF)

file(GLOB_RECURSE YCSB_CORE_SRC "core/*.cc")
include(FindThreads)

if(EXAMPLEDB)
    set(EXAMPLEDB_VARIATIONS 
        "exampledb_O0" 
        "exampledb_O3"
    )

    foreach(variant IN LISTS EXAMPLEDB_VARIATIONS)
        file(GLOB_RECURSE YCSB_EXAMPLEDB_SRC "example/*.cc")
        set(SOURCES ${YCSB_CORE_SRC} ${YCSB_EXAMPLEDB_SRC})

        add_executable(ycsb_${variant} ${SOURCES})
        target_include_directories(ycsb_${variant} PRIVATE ${PROJECT_SOURCE_DIR})

        if(variant STREQUAL "exampledb_O0")
            target_compile_options(ycsb_${variant} PRIVATE -O0 -g)
        elseif(variant STREQUAL "exampledb_O3")
            target_compile_options(ycsb_${variant} PRIVATE -O3 -funroll-loops)
        endif()

    endforeach()
endif()

# include(FindThreads)

# add_executable(ycsb ${YCSB_CORE_SRC})
# target_include_directories(ycsb PRIVATE ${PROJECT_SOURCE_DIR})

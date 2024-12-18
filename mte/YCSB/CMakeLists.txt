cmake_minimum_required(VERSION 3.10)
project(ycsb-cpp LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "-pthread")
#set(CMAKE_CXX_FLAGS "-pthread -march=armv8.5-a+memtag -fsanitize=memtag-heap")


option(EXAMPLEDB "Include the example files in the build" OFF)
option(CHASHTABLE "Include the example files in the build" OFF)

file(GLOB_RECURSE YCSB_CORE_SRC "core/*.cc")
include(FindThreads)

if(EXAMPLEDB)
    set(EXAMPLEDB_VARIATIONS 
      "O2_TAGGED" 
      "O2_UNTAGGED"
    )

    foreach(variant IN LISTS EXAMPLEDB_VARIATIONS)
        file(GLOB_RECURSE YCSB_EXAMPLEDB_SRC "example/*.cc")
        set(SOURCES ${YCSB_CORE_SRC} ${YCSB_EXAMPLEDB_SRC})

        add_executable(ycsb_${variant} ${SOURCES})
        target_include_directories(ycsb_${variant} PRIVATE ${PROJECT_SOURCE_DIR})

        if(variant STREQUAL "O2_TAGGED")
          target_compile_options(ycsb_${variant} PRIVATE 
            -O2 -march=armv8.5-a+memtag -fsanitize=memtag-heap)
        elseif(variant STREQUAL "O2_UNTAGGED")
          target_compile_options(ycsb_${variant} PRIVATE
            -O2 -march=armv8.5-a+memtag)
        endif()

    endforeach()
endif()


if(CHASHTABLE)
    set(EXAMPLEDB_VARIATIONS 
      "O2_TAGGED" 
    )

    foreach(variant IN LISTS EXAMPLEDB_VARIATIONS)
        file(GLOB_RECURSE YCSB_EXAMPLEDB_SRC 
          "chashtable/*.cc" "chashtable/*.c")
        set(SOURCES ${YCSB_CORE_SRC} ${YCSB_EXAMPLEDB_SRC})

        add_executable(ycsb_${variant} ${SOURCES})
        target_include_directories(ycsb_${variant} PRIVATE ${PROJECT_SOURCE_DIR})

        if(variant STREQUAL "O2_TAGGED")
          target_compile_options(${variant} PRIVATE 
            -O2) #-march=armv8.5-a+memtag -fsanitize=memtag-heap)
        endif()

    endforeach()
endif()

# include(FindThreads)

# add_executable(ycsb ${YCSB_CORE_SRC})
# target_include_directories(ycsb PRIVATE ${PROJECT_SOURCE_DIR})

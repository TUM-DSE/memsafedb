// memcpy_bench.c
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "ptr_chase.h"


/*
 * Layout:
 * buffer is used as two equal size regions
 * [src][dst]
 * nodes is the total count of bytes in the buffer
 * we copy fixed size chunks from src to dst in a loop
 */
size_t required_mem_size(size_t n) {
    return n * 2;
}

void *benchmark_init(void *buffer, size_t mem_size)
{
    (void)mem_size;
    // we touch the full buffer once
    memset(buffer, 0, mem_size);
    return buffer;
}

__attribute__((noinline))
uintptr_t benchmark_run(void *start, size_t mem_size, size_t iterations)
{
    (void)iterations;

    uint8_t *base = (uint8_t *)start;
    size_t chunk = mem_size / 2;

    // For safety make total_bytes a multiple of 2 * chunk in main
    // volatile to prevent the compiler from replacing the loop with a memcpy
    volatile uint8_t *src = base;
    volatile uint8_t *dst = base + chunk;

    for (size_t i = 0; i < chunk; i++) {
        dst[i] = src[i];
    }

    return (uintptr_t)dst;
}

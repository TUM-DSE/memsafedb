// memread_bench.c
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "ptr_chase.h"


size_t required_mem_size(size_t n) {
    return n;
}

void *benchmark_init(void *buffer, size_t mem_size)
{
    (void)mem_size;
    // we touch the full buffer once and populate it
    memset(buffer, 0x42, mem_size);
    return buffer;
}

__attribute__((noinline))
uintptr_t benchmark_run(void *start, size_t mem_size, size_t iterations)
{
    (void)iterations;

    volatile uint8_t *base = (volatile uint8_t *)start;
    volatile uint64_t sum = 0;

    // Read through the entire buffer byte-by-byte
    for (size_t i = 0; i < mem_size; i++) {
        sum += base[i];
    }

    return (uintptr_t)sum;
}

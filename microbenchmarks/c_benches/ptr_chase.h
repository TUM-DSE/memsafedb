#pragma once

#include <stddef.h>
#include <stdint.h>

size_t required_mem_size(size_t n);
void *benchmark_init(void *buffer, size_t mem_size);
uintptr_t benchmark_run(void *start, size_t mem_size, size_t iterations);

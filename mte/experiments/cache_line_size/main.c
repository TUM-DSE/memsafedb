#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <time.h>
#include "../allocator/allocator.h"


extern void benchmark(uint32_t *arr, size_t len, size_t steps);

int main(int argc, char *args[]) {
    if (argc != 4) {
        printf("Usage: %s <iterations> <len> <stride>\n", args[0]);
        exit(EXIT_FAILURE);
    }

    size_t iterations = atoll(args[1]);
    size_t len = atoll(args[2]);
    size_t stride = atoll(args[3]);
    
    // we only test with lengths of power of 2 - this is done to simplify the benchmark
    assert((len & (len - 1)) == 0);
    
    // we only test with strides of power of 2 - 
    assert((stride & (stride - 1)) == 0);

    for (size_t i = 0; i < iterations; ++i) {
        size_t num_bytes = len * sizeof(uint32_t);
        void *p = alloc(num_bytes);

        struct timespec s, e;
        clock_gettime(CLOCK_MONOTONIC_RAW, &s);
        benchmark(p, len, stride);
        clock_gettime(CLOCK_MONOTONIC_RAW, &e);

        uint64_t duration = 1e9 * (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec);
        printf("%ld;%ld;%ld\n", len, stride, duration);

        alloc_free(p, num_bytes);
    }
}

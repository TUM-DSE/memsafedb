#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <cheriintrin.h>

int main() {
    uint64_t *buf = (uint64_t *)aligned_alloc(64, 128);
    if (!buf) { perror("alloc"); return 1; }

    for (size_t i = 0; i < (128 / 8); i++) buf[i] = (uint64_t)i;

    const uint64_t *p = buf;
    const uint64_t *q = p;
    // Force the compiler to treat p/q as potentially equal only at runtime.
    // also, clear the tag bit
    p = cheri_tag_clear(p);
    __asm__ volatile("" : "+C"(p), "+C"(q) : : "memory");

    uint64_t result = 0;
    if (p == q) {
        result = q[0];
    }

    // p == q should be true (same address). On CHERI, not interchangeable due to bounds.
    printf("out=%llu\n", (unsigned long long)result);

    free(buf);
    return 0;
}

// ptr_chase.c
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>

typedef struct Node {
    struct Node *next;
} Node;

static uint64_t rng_state = 0x123456789abcdefULL;

static inline uint64_t xorshift64(void) {
    uint64_t x = rng_state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    rng_state = x;
    return x;
}

size_t required_mem_size(size_t n) {
    return n * sizeof(Node);
}

/**
 * Initialize a single cyclic pointer chase inside the given buffer.
 *
 * buffer_size is in bytes, it will be truncated to a multiple of sizeof(Node).
 *
 * Returns start node pointer for the chase, or NULL if too small.
 */
void *benchmark_init(void *buffer, size_t mem_size) {
    size_t count = mem_size / sizeof(Node);
    if (!buffer || count < 2) {
        return NULL;
    }

    Node *nodes = (Node *)buffer;

    // index permutation
    size_t *perm = malloc(count * sizeof(size_t));
    if (!perm) {
        return NULL;
    }

    for (size_t i = 0; i < count; ++i) {
        perm[i] = i;
    }

    // Fisher Yates shuffle
    for (size_t i = count - 1; i > 0; --i) {
        size_t j = (size_t)xorshift64() % (i + 1);
        size_t tmp = perm[i];
        perm[i] = perm[j];
        perm[j] = tmp;
    }

    // Build one cycle over all nodes
    for (size_t i = 0; i < count; ++i) {
        size_t cur = perm[i];
        size_t nxt = perm[(i + 1) % count];
        nodes[cur].next = &nodes[nxt];
    }

    void *start = &nodes[perm[0]];
    free(perm);
    return start;
}

/**
 * Perform pointer chase for the given number of iterations.
 *
 * Returns a value derived from the final pointer to keep the compiler
 * from optimizing the loop away.
 */
__attribute__((noinline))
uintptr_t benchmark_run(void *start, size_t mem_size, size_t iterations) {
    Node *cursor = (Node *)start;
    if (!cursor) {
        return 0;
    }

    size_t count = mem_size / sizeof(Node);
    for (size_t i = 0; i < iterations; ++i) {
        // we walk the entire cycle once
        for (size_t j = 0; j < count; ++j) {
            cursor = cursor->next;
        }
    }

    return (uintptr_t)cursor;
}

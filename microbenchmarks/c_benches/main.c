#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <time.h>
#include <math.h>

#include "ptr_chase.h"

// -----------------------------------------------------------------------------
// Configuration & Helpers
// -----------------------------------------------------------------------------

#define WARMUP_RATIO 0.1
// For small working sets, run extra samples to reduce variance.
#define SMALL_SIZE_BYTES (256 * 1024)

enum mte_mode {
    MTE_OFF = 0,
    MTE_SYNC,
    MTE_ASYNC,
    MTE_SYNC_NO_TAGGING,
    MTE_SYNC_PRCTL_ONLY,
};

typedef struct {
    double mean;
    double stddev;
    double min;
    double max;
} stats_t;

static inline uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static stats_t compute_stats(double *data, size_t n) {
    if (n == 0) return (stats_t){0};
    
    double sum = 0, min = data[0], max = data[0];
    for (size_t i = 0; i < n; i++) {
        sum += data[i];
        if (data[i] < min) min = data[i];
        if (data[i] > max) max = data[i];
    }
    double mean = sum / n;
    
    double sum_sq = 0;
    for (size_t i = 0; i < n; i++) {
        sum_sq += (data[i] - mean) * (data[i] - mean);
    }
    double stddev = (n > 1) ? sqrt(sum_sq / (n - 1)) : 0.0;
    
    return (stats_t){mean, stddev, min, max};
}

static enum mte_mode parse_mte_mode(const char *s) {
    if (!s || strcmp(s, "off") == 0) return MTE_OFF;
    if (strcmp(s, "sync") == 0) return MTE_SYNC;
    if (strcmp(s, "async") == 0) return MTE_ASYNC;
    if (strcmp(s, "no_tagging") == 0) return MTE_SYNC_NO_TAGGING;
    if (strcmp(s, "prctl_only") == 0) return MTE_SYNC_PRCTL_ONLY;
    fprintf(stderr, "Unknown MTE mode \"%s\", using off\n", s);
    return MTE_OFF;
}

static int configure_mte(enum mte_mode mode) {
    if (mode == MTE_OFF) return 0;

#if defined(PR_SET_TAGGED_ADDR_CTRL) && defined(PR_TAGGED_ADDR_ENABLE) && defined(PR_MTE_TCF_SHIFT)
    unsigned long ctrl = PR_TAGGED_ADDR_ENABLE;
    switch (mode) {
    case MTE_SYNC:
    case MTE_SYNC_PRCTL_ONLY:
    case MTE_SYNC_NO_TAGGING:
        ctrl |= PR_MTE_TCF_SYNC;
        break;
    case MTE_ASYNC:
        ctrl |= PR_MTE_TCF_ASYNC;
        break;
    default: return 0;
    }
    ctrl |= (0xfffeUL << PR_MTE_TAG_SHIFT);
    if (prctl(PR_SET_TAGGED_ADDR_CTRL, ctrl, 0, 0, 0) != 0) {
        perror("prctl failed");
        return -1;
    }
    return 0;
#else
    (void)mode;
    fprintf(stderr, "MTE prctl not available on this build\n");
    return 1;
#endif
}

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s [--sizes N,M,...] [--iterations N] [--min-iterations N] [--enable-mte mode]\n"
            "  --min-iterations N   lower-bound on per-size iteration count after scaling (default 1)\n",
            prog);
}

// -----------------------------------------------------------------------------
// Core Benchmark Logic
// -----------------------------------------------------------------------------

int run_benchmark_for_size(size_t size, size_t iterations, enum mte_mode mode) {
    long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) page_size = 4096;
    
    size_t requested_mem_size = required_mem_size(size);
    size_t alloc_size = (requested_mem_size + page_size - 1) / page_size * page_size;

    int prot = PROT_READ | PROT_WRITE;
#if defined(PROT_MTE)
    if (mode == MTE_SYNC || mode == MTE_ASYNC || mode == MTE_SYNC_NO_TAGGING) {
        prot |= PROT_MTE;
    }
#endif

    void *buffer = mmap(NULL, alloc_size, prot, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (buffer == MAP_FAILED) {
        perror("mmap failed");
        return 1;
    }

#if defined(PROT_MTE)
    if (mode != MTE_OFF && mode != MTE_SYNC_NO_TAGGING && mode != MTE_SYNC_PRCTL_ONLY) {
        uintptr_t p = (uintptr_t)buffer;
        p = (p & ~(0xFULL << 56)) | (1ULL << 56);
        uintptr_t end = p + alloc_size;
        buffer = (void *) p;
        while (p < end) {
            __asm volatile("stg %0, [%0], #16" : "+r"(p) :: "memory");
        }
    }
#endif

    void *start = benchmark_init(buffer, requested_mem_size);
    if (!start) {
        munmap(buffer, alloc_size);
        return 1;
    }

    // Warmup
    size_t warmup_iters = (size_t)(iterations * WARMUP_RATIO);
    if (warmup_iters < 10) warmup_iters = 10;
    
    volatile uintptr_t dummy = 0;
    for (size_t i = 0; i < warmup_iters; i++) {
        dummy = benchmark_run(start, requested_mem_size, 1);
    }
    (void)dummy;

    // Measurement
    double *samples_time_ns = malloc(iterations * sizeof(double));
    if (!samples_time_ns) {
        munmap(buffer, alloc_size);
        return 1;
    }

    for (size_t r = 0; r < iterations; r++) {
        uint64_t t_start = get_time_ns();
        dummy = benchmark_run(start, requested_mem_size, 1);
        uint64_t t_end = get_time_ns();

        double duration_ns = (double)(t_end - t_start);
        if (duration_ns < 1.0) duration_ns = 1.0;
        samples_time_ns[r] = duration_ns;
    }

    stats_t s_time = compute_stats(samples_time_ns, iterations);
    
    // OUTPUT: Comma separated values
    printf("%d,%zu,%zu,%.4f,%.4f\n", 
           mode, size, iterations, s_time.mean, s_time.stddev);

    free(samples_time_ns);
    munmap(buffer, alloc_size);
    return 0;
}

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

int main(int argc, char **argv) {
    size_t iterations = 1000;
    size_t min_iterations = 1;
    enum mte_mode mode = MTE_OFF;
    char *sizes_str = NULL;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--sizes") == 0 && i + 1 < argc) {
            sizes_str = argv[++i];
        } else if (strcmp(argv[i], "--iterations") == 0 && i + 1 < argc) {
            iterations = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--min-iterations") == 0 && i + 1 < argc) {
            min_iterations = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--enable-mte") == 0 && i + 1 < argc) {
            mode = parse_mte_mode(argv[++i]);
        } else if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        }
    }

    if (!sizes_str) {
        usage(argv[0]);
        return 1;
    }

    if (iterations == 0) iterations = 1;
    if (configure_mte(mode) != 0) return 1;

    // Print CSV Header once
    printf("mode,size,iterations,mean_time_ns,stddev_time_ns\n");

    // Parse sizes list (comma separated) and compute smallest size as baseline.
    size_t *sizes = NULL;
    size_t sizes_count = 0, sizes_cap = 0;
    size_t min_size = SIZE_MAX;

    char *sizes_copy = strdup(sizes_str);
    if (!sizes_copy) {
        perror("strdup failed");
        return 1;
    }

    char *saveptr;
    for (char *token = strtok_r(sizes_copy, ",", &saveptr);
         token != NULL;
         token = strtok_r(NULL, ",", &saveptr)) {
        size_t s = strtoull(token, NULL, 0);
        if (s > 0) {
            if (sizes_count == sizes_cap) {
                size_t new_cap = sizes_cap ? sizes_cap * 2 : 8;
                size_t *tmp = realloc(sizes, new_cap * sizeof(size_t));
                if (!tmp) {
                    perror("realloc failed");
                    free(sizes);
                    free(sizes_copy);
                    return 1;
                }
                sizes = tmp;
                sizes_cap = new_cap;
            }
            sizes[sizes_count++] = s;
            if (s < min_size) min_size = s;
        }
    }
    free(sizes_copy);

    if (sizes_count == 0) {
        usage(argv[0]);
        free(sizes);
        return 1;
    }

    for (size_t i = 0; i < sizes_count; i++) {
        size_t s = sizes[i];
        // Scale iterations so each size performs roughly constant total work,
        // but boost small sizes to get more samples.
        size_t s_mem = required_mem_size(s);
        size_t min_mem = required_mem_size(min_size);
        size_t scale_mem = min_mem;
        if (s_mem <= SMALL_SIZE_BYTES && SMALL_SIZE_BYTES > min_mem) {
            scale_mem = SMALL_SIZE_BYTES;
        }
        size_t adjusted_iterations = (size_t)((double)iterations * (double)scale_mem / (double)s_mem);
        if (adjusted_iterations < min_iterations) adjusted_iterations = min_iterations;

        if (run_benchmark_for_size(s, adjusted_iterations, mode) != 0) {
            fprintf(stderr, "Failed running size %zu\n", s);
        }
    }

    free(sizes);
    return 0;
}

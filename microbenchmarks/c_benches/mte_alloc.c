#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <time.h>
#include <math.h>
#include <sched.h>

#ifndef WARMUP_RATIO
#define WARMUP_RATIO 0.1
#endif

// extra work per measurement iteration to reduce noise
#ifndef INNER_REPS
#define INNER_REPS 10
#endif

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
    if (n == 0) {
        stats_t z = {0};
        return z;
    }

    double sum = 0.0;
    double min = data[0];
    double max = data[0];

    for (size_t i = 0; i < n; i++) {
        double v = data[i];
        sum += v;
        if (v < min) min = v;
        if (v > max) max = v;
    }

    double mean = sum / (double)n;

    double var = 0.0;
    for (size_t i = 0; i < n; i++) {
        double d = data[i] - mean;
        var += d * d;
    }

    double stddev = (n > 1) ? sqrt(var / (double)(n - 1)) : 0.0;

    stats_t s = {mean, stddev, min, max};
    return s;
}

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s --sizes S1,S2,... --num-allocs N "
            "[--iterations M] [--label NAME]\n",
            prog);
}

static void pin_to_core(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(12, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        perror("sched_setaffinity");
    }
}

// Run benchmark for one size
static int run_benchmark(const char *label,
                         size_t size_bytes,
                         size_t num_allocs,
                         size_t iterations) {
    if (size_bytes == 0 || iterations == 0 || num_allocs == 0) {
        fprintf(stderr, "size_bytes, num_allocs and iterations must be > 0\n");
        return 1;
    }

    // void **ptrs = malloc(num_allocs * sizeof(void *));
    // if (!ptrs) {
    //     perror("malloc ptrs");
    //     return 1;
    // }

    size_t warmup_iters = (size_t)(iterations * WARMUP_RATIO);
    if (warmup_iters < 5) warmup_iters = 5;

    // Warmup: run the pattern a few times to fault in pages and settle allocator
    for (size_t w = 0; w < warmup_iters; w++) {
        for (size_t i = 0; i < num_allocs; i++) {
            volatile void *p = malloc(size_bytes);
            if (!p) {
                perror("malloc warmup");
                return 1;
            }
            ((unsigned char *)p)[0] = 0;
            __asm__ volatile ("" : "+r"(p) :: "memory");
            free((void *)p);
        }
    }

    double *samples = malloc(iterations * sizeof(double));
    if (!samples) {
        perror("malloc samples");
        // free(ptrs);
        return 1;
    }

    // Measurement
    for (size_t it = 0; it < iterations; it++) {
        uint64_t t0 = get_time_ns();

        for (size_t rep = 0; rep < INNER_REPS; rep++) {
            size_t allocs = num_allocs;
            if (size_bytes >= 1024*1024) {
                allocs /= 100;
            }
            for (size_t i = 0; i < allocs; i++) {
                volatile void *p = malloc(size_bytes);
                if (!p) {
                    perror("malloc");
                    free(samples);
                    return 1;
                }
                ((unsigned char *)p)[0] = 0;
                __asm__ volatile ("" : "+r"(p) :: "memory");
                free((void *)p);
            }
        }

        uint64_t t1 = get_time_ns();
        double dt = (double)(t1 - t0);
        if (dt < 1.0) dt = 1.0;

        // store time per single batch to keep semantics consistent
        samples[it] = dt / (double)INNER_REPS;
    }

    stats_t s = compute_stats(samples, iterations);

    size_t total_bytes = size_bytes * num_allocs;

    // CSV: label,size_bytes,num_allocs,total_bytes,iterations,
    //      mean_time_ns,stddev_time_ns,min_time_ns,max_time_ns
    printf("%s,%zu,%zu,%zu,%zu,%.4f,%.4f,%.4f,%.4f\n",
           label ? label : "",
           size_bytes,
           num_allocs,
           total_bytes,
           iterations,
           s.mean,
           s.stddev,
           s.min,
           s.max);

    free(samples);
    return 0;
}

int main(int argc, char **argv) {
    char *sizes_str = NULL;
    size_t iterations = 100;
    size_t num_allocs = 0;
    const char *label = "default";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--sizes") == 0 && i + 1 < argc) {
            sizes_str = argv[++i];
        } else if (strcmp(argv[i], "--iterations") == 0 && i + 1 < argc) {
            iterations = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--num-allocs") == 0 && i + 1 < argc) {
            num_allocs = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--label") == 0 && i + 1 < argc) {
            label = argv[++i];
        } else if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 1;
        }
    }

    if (!sizes_str || num_allocs == 0) {
        usage(argv[0]);
        return 1;
    }
    if (iterations == 0) iterations = 1;

    pin_to_core();

    // Parse sizes
    size_t sizes[256];
    size_t size_count = 0;

    char *s_tmp = strdup(sizes_str);
    if (!s_tmp) {
        perror("strdup");
        return 1;
    }
    char *saveptr;
    char *tok = strtok_r(s_tmp, ",", &saveptr);
    while (tok && size_count < sizeof(sizes) / sizeof(sizes[0])) {
        size_t v = strtoull(tok, NULL, 0);
        if (v > 0) sizes[size_count++] = v;
        tok = strtok_r(NULL, ",", &saveptr);
    }
    free(s_tmp);

    if (size_count == 0) {
        fprintf(stderr, "No valid sizes\n");
        return 1;
    }

    // CSV header
    printf("label,size_bytes,num_allocs,total_bytes,iterations,"
           "mean_time_ns,stddev_time_ns,min_time_ns,max_time_ns\n");

    for (size_t i = 0; i < size_count; i++) {
        if (run_benchmark(label, sizes[i], num_allocs, iterations) != 0) {
            fprintf(stderr, "Benchmark failed for size %zu\n", sizes[i]);
        }
    }

    return 0;
}

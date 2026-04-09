#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <time.h>
#include <math.h>
#include <cheriintrin.h>

#define NARROW_SIZE 128
typedef struct {
    uint8_t payload[NARROW_SIZE];
} item_t;

#ifdef NARROW_BOUNDS
#define NARROW_BOUNDS_ENABLED 1
#else
#define NARROW_BOUNDS_ENABLED 0
#endif

// -----------------------------------------------------------------------------
// Stats helpers
// -----------------------------------------------------------------------------

typedef struct {
    double mean;
    double stddev;
    double min;
    double max;
} stats_t;

static inline uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1e9 + ts.tv_nsec;
}

static stats_t compute_stats(double *d, size_t n) {
    stats_t s = {0};
    if (n == 0) return s;

    double sum = 0, min = d[0], max = d[0];
    for (size_t i = 0; i < n; i++) {
        sum += d[i];
        if (d[i] < min) min = d[i];
        if (d[i] > max) max = d[i];
    }
    double mean = sum / n;

    double var = 0;
    for (size_t i = 0; i < n; i++) {
        double z = d[i] - mean;
        var += z * z;
    }

    s.mean = mean;
    s.stddev = (n > 1) ? sqrt(var / (n - 1)) : 0;
    s.min = min;
    s.max = max;
    return s;
}

static void usage(const char *p) {
    fprintf(stderr,
        "Usage: %s --objects K --iterations M\n"
        "  NARROW_BOUNDS=%d (compile time)\n",
        p, NARROW_BOUNDS_ENABLED);
}

// -----------------------------------------------------------------------------
// Benchmark
// -----------------------------------------------------------------------------

static int run_benchmark(size_t num_objects, size_t iterations) {
    size_t required = sizeof(item_t) * num_objects;
    size_t runs = iterations / num_objects;

    void *region = aligned_alloc(64, required);
    if (!region) {
        perror("aligned_alloc");
        return 1;
    }
    memset(region, 0, required);

    void **objects = (void**) malloc(num_objects * sizeof(void *));
    if (!objects) {
        perror("malloc objects");
        free(region);
        return 1;
    }

    double *samples = (double*) malloc(runs * sizeof(double));
    if (!samples) {
        perror("malloc samples");
        free(objects);
        free(region);
        return 1;
    }

    uint8_t *base = (uint8_t*) region;

    // Warmup
    for (size_t i = 0; i < num_objects; i++) {
        item_t *arr = (item_t *)region;
        item_t *elem = &arr[i];
        objects[i] = &elem->payload[0];
    }

    // Measurement
    for (size_t it = 0; it < runs; it++) {
        uint64_t t0 = get_time_ns();

        for (size_t i = 0; i < num_objects; i++) {
            item_t *arr = (item_t *)region;
            item_t *elem = &arr[i];
            objects[i] = &elem->payload[0];
        }

        uint64_t t1 = get_time_ns();
        samples[it] = fmax((double)(t1 - t0), 1.0);
    }

    // Prevent dead-code elimination
    volatile uint8_t sink = 0;
    for (size_t i = 0; i < num_objects; i++) {
        sink ^= ((uint8_t *)objects[i])[0];
    }
    (void)sink;

    stats_t s = compute_stats(samples, runs);

    printf("%d,%zu,%zu,%zu,%zu,%.4f,%.4f,%.4f,%.4f\n",
           NARROW_BOUNDS_ENABLED,
           required,
           sizeof(item_t),
           num_objects,
           iterations,
           s.mean, s.stddev, s.min, s.max);

    free(samples);
    free(objects);
    free(region);
    return 0;
}

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

int main(int argc, char **argv) {
    char *num_objects_str = NULL;
    size_t iterations   = 1000;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--objects") == 0 && i + 1 < argc) {
            num_objects_str = argv[++i];
        } else if (strcmp(argv[i], "--iterations") == 0 && i + 1 < argc) {
            iterations = strtoull(argv[++i], NULL, 0);
        } else {
            usage(argv[0]);
            return 1;
        }
    }

    size_t num_objects[256];
    size_t num_object_count = 0;

    char *saveptr;
    char *tok = strtok_r(num_objects_str, ",", &saveptr);
    while (tok && num_object_count < 256) {
        size_t num = strtoull(tok, NULL, 0);
        if (num > 0) {
            num_objects[num_object_count++] = num;
        } else {
            fprintf(stderr, "Invalid number of objects: %s\n", tok);
            return 1;
        }
        tok = strtok_r(NULL, ",", &saveptr);
    }

    printf("narrow_bounds,allocated_bytes,object_bytes,num_objects,iterations,"
           "mean_time_ns,stddev_time_ns,min_time_ns,max_time_ns\n");

    for (size_t i = 0; i < num_object_count; i++){
        if (iterations < num_objects[i]) {
            fprintf(stderr, "iterations (%zu) < num_objects (%zu)\n", iterations, num_objects[i]);
            return 1;
        }
        if (run_benchmark(num_objects[i], iterations) != 0) {
            return 1;
        }
    }

    return 0;
}

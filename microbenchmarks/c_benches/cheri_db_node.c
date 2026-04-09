#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <math.h>

#define MAX_FANOUT 64
#define DEFAULT_FANOUT 16
#define DEFAULT_NODES 512
#define DEFAULT_ITERATIONS 1000

#ifdef SUBOBJECT_BOUNDS
#define SUBOBJECT_BOUNDS_ENABLED 1
#else
#define SUBOBJECT_BOUNDS_ENABLED 0
#endif

typedef struct db_node {
    uint64_t keys[MAX_FANOUT];
    uint64_t payloads[MAX_FANOUT];
    struct db_node *children[MAX_FANOUT + 1];
} db_node_t;

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

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [--fanout N] [--nodes N] [--iterations N]\n"
        "  subobject bounds: %d (compile time)\n",
        prog, SUBOBJECT_BOUNDS_ENABLED);
}

static void init_nodes(db_node_t *nodes, size_t node_count, size_t fanout) {
    for (size_t n = 0; n < node_count; n++) {
        for (size_t i = 0; i < fanout; i++) {
            nodes[n].keys[i] = (uint64_t)(n * fanout + i);
            nodes[n].payloads[i] = nodes[n].keys[i] ^ 0x5a5a5a5a5a5a5a5aULL;
            nodes[n].children[i] = &nodes[(n + i + 1) % node_count];
        }
        nodes[n].children[fanout] = &nodes[(n + fanout + 1) % node_count];
    }
}

static int run_benchmark(size_t node_count, size_t fanout, size_t iterations) {
    if (fanout == 0 || fanout > MAX_FANOUT) {
        fprintf(stderr, "fanout must be between 1 and %d\n", MAX_FANOUT);
        return 1;
    }

    db_node_t *nodes = aligned_alloc(64, node_count * sizeof(db_node_t));
    if (!nodes) {
        perror("aligned_alloc");
        return 1;
    }
    memset(nodes, 0, node_count * sizeof(db_node_t));
    init_nodes(nodes, node_count, fanout);

    double *samples = malloc(iterations * sizeof(double));
    if (!samples) {
        perror("malloc samples");
        free(nodes);
        return 1;
    }

    // Warm up to ensure caches are populated before measurement
    volatile uint64_t warm_sink = 0;
    for (size_t n = 0; n < node_count; n++) {
        size_t idx = n % fanout;
        warm_sink ^= nodes[n].keys[idx];
        warm_sink ^= nodes[n].payloads[idx];
        warm_sink ^= (uintptr_t)nodes[n].children[idx];
    }

    for (size_t it = 0; it < iterations; it++) {
        uint64_t start = get_time_ns();

        uint64_t acc_keys = 0;
        uint64_t acc_payloads = 0;
        uintptr_t acc_child = 0;

        for (size_t n = 0; n < node_count; n++) {
            size_t slot = (n + it) % fanout;
            db_node_t *node = &nodes[n];

            uint64_t *key_ref = &node->keys[slot];
            uint64_t *payload_ref = &node->payloads[slot];
            db_node_t **child_ref = &node->children[slot];

            acc_keys += *key_ref;
            acc_payloads += *payload_ref;
            acc_child ^= (uintptr_t)*child_ref;
        }

        uint64_t end = get_time_ns();
        (void)acc_keys;
        (void)acc_payloads;
        (void)acc_child;

        double duration_ns = (double)(end - start);
        if (duration_ns < 1.0) duration_ns = 1.0;
        samples[it] = duration_ns;
    }

    stats_t s = compute_stats(samples, iterations);
    printf("%d,%zu,%zu,%zu,%zu,%.4f,%.4f,%.4f,%.4f\n",
           SUBOBJECT_BOUNDS_ENABLED,
           fanout,
           node_count,
           iterations,
           sizeof(db_node_t),
           s.mean,
           s.stddev,
           s.min,
           s.max);

    free(samples);
    free(nodes);
    return 0;
}

int main(int argc, char **argv) {
    size_t fanout = DEFAULT_FANOUT;
    size_t node_count = DEFAULT_NODES;
    size_t iterations = DEFAULT_ITERATIONS;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--fanout") == 0 && i + 1 < argc) {
            fanout = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--nodes") == 0 && i + 1 < argc) {
            node_count = strtoull(argv[++i], NULL, 0);
        } else if (strcmp(argv[i], "--iterations") == 0 && i + 1 < argc) {
            iterations = strtoull(argv[++i], NULL, 0);
        } else {
            usage(argv[0]);
            return 1;
        }
    }

    if (node_count == 0 || iterations == 0) {
        usage(argv[0]);
        return 1;
    }

    printf("subobject_bounds,fanout,node_count,iterations,node_bytes,mean_time_ns,stddev_time_ns,min_time_ns,max_time_ns\n");
    return run_benchmark(node_count, fanout, iterations);
}

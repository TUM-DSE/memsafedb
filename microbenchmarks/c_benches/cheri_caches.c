#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <math.h>

#ifndef __CHERI_PURE_CAPABILITY__
#error "Compile with purecap Morello LLVM"
#endif

// ---------------------------------------------------------
// Configuration
// ---------------------------------------------------------

#define L1_SIZE   (64UL * 1024UL)
#define L2_SIZE   (1UL * 1024UL * 1024UL)
#define L3_SIZE   (2UL * 1024UL * 1024UL)
#define L4_SIZE   (8UL * 1024UL * 1024UL)
#define MAX_SIZE  (L4_SIZE * 4)

// Timing
#define TARGET_RUN_NS (100ULL * 1000ULL * 1000ULL) 
#define CALIBRATION_ITERS 50 
#define REPEAT_COUNT 10 

// ---------------------------------------------------------
// Helpers
// ---------------------------------------------------------

typedef struct {
    double mean;
    double stddev;
} stats_t;

static stats_t compute_stats(double *samples, int n) {
    if (n <= 0) return (stats_t){0,0};
    double sum = 0.0;
    for(int i=0; i<n; i++) sum += samples[i];
    double mean = sum / n;
    
    double sum_sq_diff = 0.0;
    for(int i=0; i<n; i++) {
        sum_sq_diff += (samples[i] - mean) * (samples[i] - mean);
    }
    double stddev = (n > 1) ? sqrt(sum_sq_diff / (n - 1)) : 0.0;
    return (stats_t){mean, stddev};
}

static inline uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static void pin_current_thread(int cpu) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (pthread_setaffinity_np(pthread_self(), sizeof(set), &set) != 0) {
        perror("pthread_setaffinity_np");
        exit(1);
    }
}

static void *alloc_cap_array(size_t bytes) {
    void *ptr = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (ptr == MAP_FAILED) {
        perror("mmap");
        exit(1);
    }
    return ptr;
}

static void init_cap_array(void **base, size_t count) {
    char *region = (char*)base;
    for (size_t i = 0; i < count; i++) {
        base[i] = region + (i * sizeof(void*));
    }
}

// ---------------------------------------------------------
// Operations
// ---------------------------------------------------------

// Unrolled reader to saturate L1/L2 bandwidth
static inline void load_caps_once(void **base, size_t count) {
    uintptr_t accum = 0;
    size_t i = 0;
    
    // We step by 4 caps (4 * 16 = 64 bytes = 1 cache line)
    const size_t step = 4; 
    
    // Unroll 4x (Process 4 cache lines per loop iteration)
    size_t unroll_limit = 0;
    if (count > (step * 4)) {
        unroll_limit = count - (step * 4);
    }

    // Main unrolled loop
    for (; i < unroll_limit; i += (step * 4)) {
        accum ^= (uintptr_t)base[i];
        accum ^= (uintptr_t)base[i + step];
        accum ^= (uintptr_t)base[i + step*2];
        accum ^= (uintptr_t)base[i + step*3];
    }

    // Handle remainder
    for (; i < count; i += step) {
        accum ^= (uintptr_t)base[i];
    }
    
    // Sink the accumulator so the compiler doesn't optimize it away
    __asm volatile("" :: "r"(accum));
}

static inline void clear_tags_once(void **base, size_t count) {
    const size_t step = 4;
    void * volatile * vbase = (void * volatile *)base;
    for (size_t i = 0; i < count; i += step) {
        void *c = vbase[i];
        c = __builtin_cheri_tag_clear(c);
        vbase[i] = c; 
    }
}

// ---------------------------------------------------------
// Benchmark Logic
// ---------------------------------------------------------

struct writer_ctx {
    void **base;
    size_t count;
    volatile int stop;
};

static void *writer_thread(void *arg) {
    pin_current_thread(1); 
    struct writer_ctx *ctx = (struct writer_ctx*)arg;
    while (!ctx->stop) {
        clear_tags_once(ctx->base, ctx->count);
    }
    return NULL;
}

static void run_contention_test(void **base, size_t max_bytes, int with_writer) {
    // Generate powers of 2 from 32KB up to MAX
    size_t sizes[64];
    int nsizes = 0;
    
    for (size_t s = 32UL * 1024UL; s <= max_bytes; s <<= 1) {
        sizes[nsizes++] = s;
    }

    printf("#mode=2,with_writer,size,iters,mean_ns_per_pass,stddev_ns\n");

    for (int i = 0; i < nsizes; i++) {
        size_t bytes = sizes[i];
        size_t count = bytes / sizeof(void*);
        if (count == 0) continue;

        // 1. Calibration Phase
        uint64_t t1 = get_time_ns();
        for (int k = 0; k < CALIBRATION_ITERS; k++) {
            load_caps_once(base, count);
        }
        uint64_t t2 = get_time_ns();
        double ns_per_calib = (double)(t2 - t1) / CALIBRATION_ITERS;
        
        unsigned long iters = (unsigned long)((double)TARGET_RUN_NS / ns_per_calib);
        if (iters < 5) iters = 5;
        // Cap max iterations to prevent 10s hangs on huge arrays
        if (iters > 20000000) iters = 20000000; 

        // 2. Setup Contention
        struct writer_ctx ctx = { base, count, 0 };
        pthread_t t;

        if (with_writer) {
            pthread_create(&t, NULL, writer_thread, &ctx);
            // Longer warmup for contention to stabilize
            usleep(20000); 
        }

        // 3. Measurement Repeats
        double samples[REPEAT_COUNT];
        for (int r = 0; r < REPEAT_COUNT; r++) {
            uint64_t start = get_time_ns();
            for (unsigned long it = 0; it < iters; it++) {
                load_caps_once(base, count);
            }
            uint64_t end = get_time_ns();
            samples[r] = (double)(end - start) / (double)iters;
        }

        if (with_writer) {
            ctx.stop = 1;
            pthread_join(t, NULL);
        }

        stats_t s = compute_stats(samples, REPEAT_COUNT);

        printf("2,%d,%zu,%lu,%.2f,%.2f\n",
               with_writer, bytes, iters, s.mean, s.stddev);
    }
}

int main() {
    pin_current_thread(0);

    // Initialize full buffer
    void **base = alloc_cap_array(MAX_SIZE);
    init_cap_array(base, MAX_SIZE / sizeof(void*));
    load_caps_once(base, MAX_SIZE / sizeof(void*)); 

    printf("# CHERI Cache Coherency Benchmark (optimized)\n");
    
    run_contention_test(base, MAX_SIZE, 0); // Baseline
    run_contention_test(base, MAX_SIZE, 1); // Contention

    return 0;
}
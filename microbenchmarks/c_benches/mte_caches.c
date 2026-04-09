#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <time.h>
#include <unistd.h>
#include <math.h>

// Granule size for MTE
#define TAG_GRANULE 16UL

// Cache sizes
#define L1_SIZE   (64UL * 1024UL)
#define L2_SIZE   (2UL * 1024UL * 1024UL)
#define L3_SIZE   (16UL * 1024UL * 1024UL)
#define MAX_SIZE  (L3_SIZE * 2) 

// Benchmarking Target Time per Repeat
#define TARGET_RUN_NS (100ULL * 1000ULL * 1000ULL) // 100ms per repeat
#define CALIBRATION_ITERS 20
#define REPEAT_COUNT 10 // Number of stats samples

// ---------------------------------------------------------
// Helpers
// ---------------------------------------------------------

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

static void enable_mte(void) {
    unsigned long ctrl = PR_TAGGED_ADDR_ENABLE;
    ctrl |= PR_MTE_TCF_SYNC; 
    ctrl |= (0xfffeUL << PR_MTE_TAG_SHIFT);
    if (prctl(PR_SET_TAGGED_ADDR_CTRL, ctrl, 0, 0, 0) != 0) {
        perror("prctl MTE");
        exit(1);
    }
}

static void *alloc_mte_buffer(size_t size) {
    void *p = mmap(NULL, size, PROT_READ | PROT_WRITE | PROT_MTE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        perror("mmap");
        exit(1);
    }
    return p;
}

// ---------------------------------------------------------
// Operations
// ---------------------------------------------------------

static inline void op_memset(void *base, size_t size) {
    memset(base, 0, size);
}

static inline void op_stzg(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("stzg %0, [%0], #16" : "+r"(p) : : "memory");
    }
}

static inline void op_stz2g(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("stz2g %0, [%0], #32" : "+r"(p) : : "memory");
    }
}

static inline void op_stgp(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("stgp xzr, xzr, [%0], #16" : "+r"(p) : : "memory");
    }
}

static inline void op_stp(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("stp xzr, xzr, [%0], #16" : "+r"(p) : : "memory");
    }
}

static inline void op_stg(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("stg %0, [%0], #16" : "+r"(p) : : "memory");
    }
}

static inline void op_st2g(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("st2g %0, [%0], #32" : "+r"(p) : : "memory");
    }
}

static inline void op_stnp(void *base, size_t size) {
    unsigned char *p = (unsigned char *)base;
    unsigned char *end = p + size;
    while (p < end) {
        __asm volatile("stnp xzr, xzr, [%0]" : "+r"(p) : : "memory");
        p += 16;
    }
}

static inline void touch_region_readonly(unsigned char *base, size_t size) {
    volatile unsigned char sink = 0;
    const size_t step = 64; 
    for (size_t i = 0; i < size; i += step) {
        sink ^= base[i];
    }
    __asm volatile("" :: "r"(sink) : "memory");
}

// ---------------------------------------------------------
// Stats Helper
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
    // Sample standard deviation
    double stddev = (n > 1) ? sqrt(sum_sq_diff / (n - 1)) : 0.0;
    
    return (stats_t){mean, stddev};
}

// ---------------------------------------------------------
// MODE 1: Initialization
// ---------------------------------------------------------

static void run_mode1_sub(int submode, void *buf, size_t sz) {
    // Calibration
    uint64_t t_start = get_time_ns();
    for(int i=0; i<CALIBRATION_ITERS; i++) {
        switch (submode) {
            case 0: op_memset(buf, sz); break;
            case 1: op_memset(buf, sz); break;
            case 2: op_stg(buf, sz); break;
            case 3: op_stzg(buf, sz); break;
            case 4: op_stz2g(buf, sz); break;
            case 5: op_stgp(buf, sz); break;
            case 6: op_memset(buf, sz); op_stg(buf, sz); break;
            case 7: op_memset(buf, sz); op_st2g(buf, sz); break;
            case 8: op_stp(buf, sz); break;
            case 9: op_stnp(buf, sz); break;
        }
    }
    uint64_t t_end = get_time_ns();
    
    double ns_per_calib = (double)(t_end - t_start) / (double)CALIBRATION_ITERS;
    unsigned long iters = (unsigned long)((double)TARGET_RUN_NS / ns_per_calib);
    if (iters < 5) iters = 5;

    // Measurement Repeats
    double samples[REPEAT_COUNT];

    for (int r = 0; r < REPEAT_COUNT; r++) {
        t_start = get_time_ns();
        for (unsigned long i = 0; i < iters; i++) {
            switch (submode) {
                case 0: op_memset(buf, sz); break;
                case 1: op_memset(buf, sz); break;
                case 2: op_stg(buf, sz); break;
                case 3: op_stzg(buf, sz); break;
                case 4: op_stz2g(buf, sz); break;
                case 5: op_stgp(buf, sz); break;
                case 6: op_memset(buf, sz); op_stg(buf, sz); break;
                case 7: op_memset(buf, sz); op_st2g(buf, sz); break;
                case 8: op_stp(buf, sz); break;
                case 9: op_stnp(buf, sz); break;
            }
        }
        t_end = get_time_ns();
        samples[r] = (double)(t_end - t_start) / (double)iters;
    }

    stats_t s = compute_stats(samples, REPEAT_COUNT);
    printf("1,%d,%zu,%lu,%.2f,%.2f\n", submode, sz, iters, s.mean, s.stddev);
}

static void run_mode1(void *buf, size_t max_size) {
    size_t sizes[] = {
        2 << 13, 2 << 14, 2 << 15, 2 << 16, 2 << 17, 2 << 18, 
        2 << 19, 2 << 20, 2 << 21, 2 << 22, 2 << 23, 2 << 24, 2 << 25,
    };
    size_t nsizes = sizeof(sizes) / sizeof(sizes[0]);

    printf("#mode=1,submode,size,iters,mean_ns,stddev_ns\n");
    for (int sub = 1; sub <= 9; sub++) {
        for (size_t i = 0; i < nsizes; i++) {
            if (sizes[i] > max_size) continue;
            run_mode1_sub(sub, buf, sizes[i]);
        }
    }
}

static void run_mode1_mte_disabled(void *buf, size_t max_size) {
    size_t sizes[] = {
        2 << 13, 2 << 14, 2 << 15, 2 << 16, 2 << 17, 2 << 18, 
        2 << 19, 2 << 20, 2 << 21, 2 << 22, 2 << 23, 2 << 24, 2 << 25,
    };
    size_t nsizes = sizeof(sizes) / sizeof(sizes[0]);

    for (size_t i = 0; i < nsizes; i++) {
        if (sizes[i] > max_size) continue;
        run_mode1_sub(0, buf, sizes[i]);
    }
}

// ---------------------------------------------------------
// MODE 2: Contention (Optimized)
// ---------------------------------------------------------

struct tagger_ctx {
    unsigned char *buf;
    size_t size;
    volatile int stop;
};

static void *tagger_thread(void *arg) {
    pin_current_thread(14);
    struct tagger_ctx *ctx = (struct tagger_ctx *)arg;
    while (!ctx->stop) {
        op_stg(ctx->buf, ctx->size);
    }
    return NULL;
}

static void run_mode2(void *buf, size_t max_size, int with_tagger) {
    size_t sizes[] = {
        2 << 13, 2 << 14, 2 << 15, 2 << 16, 2 << 17, 2 << 18, 
        2 << 19, 2 << 20, 2 << 21, 2 << 22, 2 << 23, 2 << 24, 2 << 25,
    };
    size_t nsizes = sizeof(sizes) / sizeof(sizes[0]);

    printf("#mode=2,with_tagger,size,iters,mean_ns,stddev_ns\n");

    for (size_t i = 0; i < nsizes; i++) {
        size_t sz = sizes[i];
        if (sz > max_size) continue;

        struct tagger_ctx ctx = {0};
        pthread_t t;

        if (with_tagger) {
            ctx.buf = (unsigned char *)buf;
            ctx.size = sz;
            ctx.stop = 0;
            pthread_create(&t, NULL, tagger_thread, &ctx);
            usleep(10000); 
        }

        // Calibration
        uint64_t t1 = get_time_ns();
        for (int k = 0; k < CALIBRATION_ITERS; k++) {
            touch_region_readonly((unsigned char *)buf, sz);
        }
        uint64_t t2 = get_time_ns();

        double ns_per_calib = (double)(t2 - t1) / (double)CALIBRATION_ITERS;
        unsigned long iters = (unsigned long)((double)TARGET_RUN_NS / ns_per_calib);
        
        if (iters < 5) iters = 5;
        if (iters > 50000000) iters = 50000000;

        // Measurement Repeats
        double samples[REPEAT_COUNT];
        for (int r = 0; r < REPEAT_COUNT; r++) {
            uint64_t start = get_time_ns();
            for (unsigned long it = 0; it < iters; it++) {
                touch_region_readonly((unsigned char *)buf, sz);
            }
            uint64_t end = get_time_ns();
            samples[r] = (double)(end - start) / (double)iters;
        }

        if (with_tagger) {
            ctx.stop = 1;
            pthread_join(t, NULL);
        }

        stats_t s = compute_stats(samples, REPEAT_COUNT);
        printf("2,%d,%zu,%lu,%.2f,%.2f\n", with_tagger, sz, iters, s.mean, s.stddev);
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s [1|2]\n", argv[0]);
        return 1;
    }

    pin_current_thread(12);

    int mode = atoi(argv[1]);

    void *buf;
    if (mode != 0) {
        enable_mte();
        buf = alloc_mte_buffer(MAX_SIZE);
    } else {
        buf = mmap(NULL, MAX_SIZE, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (buf == MAP_FAILED) {
            perror("mmap");
            exit(1);
        }
    }
    memset(buf, 0, MAX_SIZE); 

    if (mode == 1) {
        run_mode1(buf, MAX_SIZE);
    } else if (mode == 2) {
        run_mode2(buf, MAX_SIZE, 0); 
        run_mode2(buf, MAX_SIZE, 1); 
    } else if (mode == 0) {
        run_mode1_mte_disabled(buf, MAX_SIZE);
    } else {
        fprintf(stderr, "Unknown mode: %d\n", mode);
        return 1;
    }



    return 0;
}
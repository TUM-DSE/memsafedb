#define _GNU_SOURCE
#include <cheriintrin.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef WARMUP_RATIO
#define WARMUP_RATIO 0.1
#endif

typedef struct {
  double mean;
  double stddev;
} stats_t;

static inline uint64_t get_time_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static stats_t compute_stats(double *data, size_t n) {
  if (n == 0)
    return (stats_t){0};

  double sum = 0.0;
  for (size_t i = 0; i < n; i++)
    sum += data[i];
  double mean = sum / (double)n;

  double sum_sq = 0.0;
  for (size_t i = 0; i < n; i++) {
    double d = data[i] - mean;
    sum_sq += d * d;
  }
  double stddev = (n > 1) ? sqrt(sum_sq / (double)(n - 1)) : 0.0;
  return (stats_t){mean, stddev};
}

static inline uint64_t ldxr_stxr_u64(uint64_t *addr, uint64_t value) {
  uint64_t out = 0;
  unsigned int status = 1;
  do {
    __asm__ volatile("ldxr %0, [%2]\n"
                     "stxr %w1, %3, [%2]\n"
                     : "=&r"(out), "=&r"(status)
                     : "r"(addr), "r"(value)
                     : "memory");
  } while (status);
  return out;
}

typedef void *__capability cap_void_t;
typedef cap_void_t *__capability cap_void_ptr_t;

static inline cap_void_t cap_from_ptr(void *ptr, size_t len) {
  cap_void_t base = __builtin_cheri_global_data_get();
  cap_void_t cap = __builtin_cheri_cap_from_pointer(base, ptr);
  return __builtin_cheri_bounds_set(cap, len);
}

static inline cap_void_t ldxr_stxr_cap(void *addr, cap_void_t value) {
  cap_void_t out = NULL;
  unsigned int status = 1;
  do {
    __asm__ volatile("ldxr %0, [%2]\n"
                     "stxr %w1, %3, [%2]\n"
                     : "=&r"(out), "=&r"(status)
                     : "r"(addr), "C"(value)
                     : "memory");
  } while (status);
  return out;
}

static void usage(const char *prog) {
  fprintf(stderr, "Usage: %s [--iterations N] [--inner N]\n", prog);
}

static int run_normal(size_t iterations, size_t inner, uint64_t *slot) {
  size_t warmup = (size_t)(iterations * WARMUP_RATIO);
  if (warmup < 5)
    warmup = 5;

  uint64_t value = 0x12345678ULL;
  for (size_t i = 0; i < warmup; i++) {
    for (size_t j = 0; j < inner; j++) {
      value ^= ldxr_stxr_u64(slot, value + j);
    }
  }

  double *samples = malloc(iterations * sizeof(double));
  if (!samples)
    return 1;

  for (size_t i = 0; i < iterations; i++) {
    uint64_t start = get_time_ns();
    for (size_t j = 0; j < inner; j++) {
      value ^= ldxr_stxr_u64(slot, value + j);
    }
    uint64_t end = get_time_ns();
    double dt = (double)(end - start);
    if (dt < 1.0)
      dt = 1.0;
    samples[i] = dt / (double)inner;
  }

  __asm__ volatile("" : "+r"(value));

  stats_t s = compute_stats(samples, iterations);
  printf("normal,%zu,%zu,%.4f,%.4f\n", iterations, inner, s.mean, s.stddev);
  free(samples);
  return 0;
}

static int run_cap(size_t iterations, size_t inner, void *slot,
                   cap_void_t value) {
  size_t warmup = (size_t)(iterations * WARMUP_RATIO);
  if (warmup < 5)
    warmup = 5;

  for (size_t i = 0; i < warmup; i++) {
    for (size_t j = 0; j < inner; j++) {
      value = ldxr_stxr_cap(slot, value);
    }
  }

  double *samples = malloc(iterations * sizeof(double));
  if (!samples)
    return 1;

  for (size_t i = 0; i < iterations; i++) {
    uint64_t start = get_time_ns();
    for (size_t j = 0; j < inner; j++) {
      value = ldxr_stxr_cap(slot, value);
    }
    uint64_t end = get_time_ns();
    double dt = (double)(end - start);
    if (dt < 1.0)
      dt = 1.0;
    samples[i] = dt / (double)inner;
  }

  __asm__ volatile("" : "+C"(value));

  stats_t s = compute_stats(samples, iterations);
  printf("capability,%zu,%zu,%.4f,%.4f\n", iterations, inner, s.mean, s.stddev);
  free(samples);
  return 0;
}

int main(int argc, char **argv) {
  size_t iterations = 100;
  size_t inner = 100000;

  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "--iterations") == 0 && i + 1 < argc) {
      iterations = strtoull(argv[++i], NULL, 0);
    } else if (strcmp(argv[i], "--inner") == 0 && i + 1 < argc) {
      inner = strtoull(argv[++i], NULL, 0);
    } else if (strcmp(argv[i], "--help") == 0) {
      usage(argv[0]);
      return 0;
    } else {
      usage(argv[0]);
      return 1;
    }
  }

  if (iterations == 0)
    iterations = 1;
  if (inner == 0)
    inner = 1;

  uint64_t *normal_slot = aligned_alloc(64, 64);
  void *cap_slot_mem = aligned_alloc(64, 64);
  void *cap_value_mem = aligned_alloc(64, 64);
  if (!normal_slot || !cap_slot_mem || !cap_value_mem) {
    perror("aligned_alloc");
    return 1;
  }

  *normal_slot = 0;
  cap_void_t cap_value = cap_from_ptr(cap_value_mem, 64);
  cap_value = __builtin_cheri_bounds_set(cap_value, 64);

  printf("kind,iterations,inner,mean_ns_per_op,stddev_ns_per_op\n");
  if (run_normal(iterations, inner, normal_slot) != 0)
    return 1;
  if (run_cap(iterations, inner, normal_slot, cap_value) != 0)
    return 1;

  free(normal_slot);
  free(cap_slot_mem);
  free(cap_value_mem);
  return 0;
}

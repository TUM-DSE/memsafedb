#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "ptr_chase.h"

#ifndef DEFAULT_READERS
#define DEFAULT_READERS 3
#endif

#ifndef DEFAULT_WRITER
#define DEFAULT_WRITER 1
#endif

#ifndef PAYLOAD_STRIDE
#define PAYLOAD_STRIDE 64
#endif

#ifndef INNER_REPS
#define INNER_REPS 50
#endif

typedef struct {
  void **table;
  unsigned char *payload;
  size_t entries;
  size_t payload_stride;
  size_t readers;
  size_t writer;
} bench_ctx_t;

typedef struct {
  bench_ctx_t *ctx;
  size_t iters;
  size_t start_idx;
  size_t step;
  uint64_t accum;
  uint64_t rng_state;
} thread_ctx_t;

static inline uint64_t xorshift64(uint64_t *state) {
  uint64_t x = *state;
  x ^= x << 13;
  x ^= x >> 7;
  x ^= x << 17;
  *state = x;
  return x;
}

static inline size_t wrap_index(size_t idx, size_t entries) {
  if (entries == 0)
    return 0;
  if (idx >= entries) {
    idx %= entries;
  }
  return idx;
}

static inline void *load_ptr(void *volatile *addr) {
#if defined(__CHERI_PURE_CAPABILITY__)
  void *out = NULL;
  __asm__ volatile("ldxr %0, [%1]\n" : "=&C"(out) : "C"(addr) : "memory");
  return out;
#else
  void *out = NULL;
  __asm__ volatile("ldxr %0, [%1]\n" : "=&r"(out) : "r"(addr) : "memory");
  return out;
#endif
}

static inline void store_ptr(void *volatile *addr, void *value) {
#if defined(__CHERI_PURE_CAPABILITY__)
  unsigned int status = 1;
  void *tmp = NULL;
  do {
    __asm__ volatile("ldxr %1, [%2]\n"
                     "stxr %w0, %3, [%2]\n"
                     : "=&r"(status), "=&C"(tmp)
                     : "C"(addr), "C"(value)
                     : "memory");
  } while (status);
#else
  unsigned int status = 1;
  void *tmp = NULL;
  do {
    __asm__ volatile("ldxr %1, [%2]\n"
                     "stxr %w0, %3, [%2]\n"
                     : "=&r"(status), "=&r"(tmp)
                     : "r"(addr), "r"(value)
                     : "memory");
  } while (status);
#endif
}

static void *reader_thread(void *arg) {
  thread_ctx_t *tctx = (thread_ctx_t *)arg;
  bench_ctx_t *ctx = tctx->ctx;
  size_t idx = tctx->start_idx;
  uint64_t accum = 0;

  for (size_t it = 0; it < tctx->iters; it++) {
    for (size_t j = 0; j < ctx->entries; j++) {
      void *ptr = load_ptr(&ctx->table[idx]);
      accum ^= (uintptr_t)ptr;
      idx += tctx->step;
      idx = wrap_index(idx, ctx->entries);
    }
  }

  tctx->accum = accum;
  return NULL;
}

static void *writer_thread(void *arg) {
  thread_ctx_t *tctx = (thread_ctx_t *)arg;
  bench_ctx_t *ctx = tctx->ctx;
  size_t idx = tctx->start_idx;
  uint64_t rng = tctx->rng_state;

  for (size_t it = 0; it < tctx->iters; it++) {
    for (size_t j = 0; j < ctx->entries; j++) {
      idx = (size_t)(xorshift64(&rng) % ctx->entries);
      size_t new_idx = (size_t)(xorshift64(&rng) % ctx->entries);
      void *ptr = ctx->payload + (new_idx * ctx->payload_stride);
      store_ptr(&ctx->table[idx], ptr);
    }
  }
  tctx->rng_state = rng;
  return NULL;
}

size_t required_mem_size(size_t n) {
  return n * (sizeof(void *) + PAYLOAD_STRIDE);
}

void *benchmark_init(void *buffer, size_t mem_size) {
  if (!buffer || mem_size < 256)
    return NULL;

  unsigned char *base = (unsigned char *)buffer;
  size_t entries = mem_size / (sizeof(void *) + PAYLOAD_STRIDE);
  if (entries < 4)
    return NULL;

  size_t table_bytes = entries * sizeof(void *);
  unsigned char *payload = base + table_bytes;
  uintptr_t p = (uintptr_t)payload;
  p = (p + (PAYLOAD_STRIDE - 1)) & ~(uintptr_t)(PAYLOAD_STRIDE - 1);
  payload = (unsigned char *)p;

  size_t payload_bytes = mem_size - (size_t)(payload - base);
  size_t payload_entries = payload_bytes / PAYLOAD_STRIDE;
  if (payload_entries < entries) {
    entries = payload_entries;
    if (entries < 4)
      return NULL;
    table_bytes = entries * sizeof(void *);
  }

  void **table = (void **)base;
  for (size_t i = 0; i < entries; i++) {
    void *ptr = payload + (i * PAYLOAD_STRIDE);
    table[i] = ptr;
  }

  bench_ctx_t *ctx = malloc(sizeof(*ctx));
  if (!ctx)
    return NULL;
  ctx->table = table;
  ctx->payload = payload;
  ctx->entries = entries;
  ctx->payload_stride = PAYLOAD_STRIDE;
  ctx->readers = DEFAULT_READERS;
  ctx->writer = DEFAULT_WRITER;
  return ctx;
}

__attribute__((noinline)) uintptr_t benchmark_run(void *start, size_t mem_size,
                                                  size_t iterations) {
  (void)mem_size;
  bench_ctx_t *ctx = (bench_ctx_t *)start;
  if (!ctx || ctx->entries == 0)
    return 0;

  size_t readers = ctx->readers;
  size_t writer = ctx->writer ? 1 : 0;
  size_t total_threads = readers + writer;
  if (total_threads == 0)
    return 0;

  size_t work_iters = iterations * INNER_REPS;
  if (work_iters == 0)
    work_iters = 1;

  pthread_t *threads = calloc(total_threads, sizeof(*threads));
  thread_ctx_t *tctx = calloc(total_threads, sizeof(*tctx));
  if (!threads || !tctx) {
    free(threads);
    free(tctx);
    return 0;
  }

  for (size_t i = 0; i < readers; i++) {
    size_t step = (2 * i) + 1;
    step = wrap_index(step, ctx->entries);
    if (step == 0)
      step = 1;
    tctx[i].ctx = ctx;
    tctx[i].iters = work_iters;
    tctx[i].start_idx = wrap_index(i * 97, ctx->entries);
    tctx[i].step = step;
    if (pthread_create(&threads[i], NULL, reader_thread, &tctx[i]) != 0) {
      total_threads = i;
      readers = i;
      writer = 0;
      break;
    }
  }

  if (writer) {
    size_t idx = readers;
    tctx[idx].ctx = ctx;
    tctx[idx].iters = work_iters;
    tctx[idx].start_idx = 3;
    tctx[idx].step = 7;
    if (tctx[idx].step >= ctx->entries)
      tctx[idx].step = 1;
    tctx[idx].rng_state = 0x9e3779b97f4a7c15ULL ^ (uint64_t)ctx->entries;
    if (pthread_create(&threads[idx], NULL, writer_thread, &tctx[idx]) != 0) {
      writer = 0;
      total_threads = readers;
    }
  }

  for (size_t i = 0; i < total_threads; i++) {
    pthread_join(threads[i], NULL);
  }

  uint64_t accum = 0;
  for (size_t i = 0; i < readers; i++) {
    accum ^= tctx[i].accum;
  }

  free(threads);
  free(tctx);
  return (uintptr_t)accum;
}
